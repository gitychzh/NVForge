#!/usr/bin/env python3
"""HTTP handler for NV proxy (nv_gw) — 三 agent 通用.

R38.12 / unify-nv: ALL models use NVCF pexec direct path (SOCKS5 → ACTIVE functions).
Single-model: dsv4p_nv (no fallback). Per-tier 5-key sequential RR with persistent
counters (全局共享, N+1 跨 agent 连续).
MSG-FIX: messages ending with assistant → append user "Continue."
"""
import http.server
import json
import os
import time
import datetime
import uuid
import http.client
import socket
import urllib.parse

from .config import (
    NVU_NUM_KEYS,
    NV_MODEL_IDS, NV_MODEL_TIERS, DEFAULT_NV_MODEL, MODEL_MAP,
    detect_nv_model, get_tier_index,
    NVCF_PEXEC_MODELS,
    PROXY_ROLE, LISTEN_PORT,
    MODEL_INPUT_TOKEN_SAFETY, DEFAULT_CONTEXT_FALLBACK,
    NVU_GATEWAY_API_KEY,
    NVU_FORCE_STREAM_UPGRADE,
    NVU_FORCE_STREAM_UPGRADE_TIMEOUT,
    NVU_FORCE_STREAM_EXCLUDE_MODELS,
    NVU_PEER_FALLBACK_ENABLED,
    NVU_PEER_FALLBACK_URL,
    NVU_PEER_FALLBACK_TIMEOUT,
    NVU_STREAM_TOTAL_DEADLINE_S,
    NVU_STREAM_FIRST_BYTE_DEADLINE_S,
    NVU_ZOMBIE_EMPTY_CONTENT_CHARS,
    NVU_ZOMBIE_MIN_INPUT_CHARS,
    NVU_STREAM_NO_CONTENT_GAP_S,
    NVU_STREAM_POLL_S,
    NVU_STREAM_FULL_BUFFER,
    NVU_KEYS, NV_INTEGRATE_HOST,
    is_key_cooling, mark_key_cooling, reset_key429_count,
)
from .logger import _log, _log_metrics, _log_error_detail
from .upstream import execute_request, UpstreamResult
from .error_mapping import format_nv_all_keys_exhausted, format_nv_error_upstream
# R1648b: /v1/messages anthropic endpoint — format conversion (self-contained pkg).
from .format.anth_to_oai import anth_to_openai, _estimate_text_chars, CHARS_PER_TOKEN_ESTIMATE
from .format.oai_to_anth import (
    OaiSseToAnthropicConverter, oai_nonstream_to_anth, convert_error_to_anth,
    THINKING_SIGNATURE as OAI_TO_ANTH_THINKING_SIG,
)


# R1-2026-07-01: identify which local agent sent the request, for per-agent
# full-chain analysis. Preference: explicit X-Caller header (set by openclaw's
# provider config). Fallback: User-Agent — "OpenAI/Python" = openclaw alt path;
# "python-httpx"/"python-requests" = hermes/opencode standalone. NB: the
# "opencode/" UA is intentionally NOT mapped to openclaw, because standalone
# opencode uses the same UA — rely on X-Caller instead.
def _detect_caller(user_agent: str, x_caller: str = "") -> str:
    xc = (x_caller or "").strip().lower()
    if xc:
        return xc
    ua = (user_agent or "").strip()
    if ua.startswith("OpenAI/Python"):
        return "openclaw"
    if ua.startswith("python-httpx"):
        return "httpx"
    if ua.startswith("python-requests"):
        return "requests"
    if ua.startswith("opencode/"):
        return "opencode-standalone"
    if ua:
        return "other"
    return "unknown"


class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ("/health", "/"):
            self._send_json(200, {
                "status": "ok",
                "proxy_role": PROXY_ROLE,
                "nv_num_keys": NVU_NUM_KEYS,
                "nvcf_pexec_models": list(NVCF_PEXEC_MODELS.keys()),
                "nv_model_tiers": NV_MODEL_TIERS,
                "nv_default_model": DEFAULT_NV_MODEL,
                "port": LISTEN_PORT,
            })
        elif parsed.path in ("/v1/models", "/models"):
            self._proxy_models()
        else:
            self._send_json(404, {"error": {"message": "not found", "type": "invalid_request_error", "code": "404"}})

    def do_HEAD(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ("/health", "/", "/v1/models", "/models", "/v1/chat/completions", "/chat/completions", "/v1/embeddings", "/embeddings", "/v1/messages"):
            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ("/v1/chat/completions", "/chat/completions"):
            self._handle_openai_nv()
        elif parsed.path in ("/v1/embeddings", "/embeddings"):
            self._handle_embeddings()
        elif parsed.path in ("/v1/messages", "/messages"):
            # R1648b: anthropic Messages endpoint (for cc4101/CC after R1648e pure-passthrough).
            # Converts anth→oai, reuses execute_request NVCF 5key chain, converts oai SSE→anth SSE.
            # No fallback in R1648b (R1648c adds nv→ms). Isolated from openai path by routing.
            self._handle_messages_anthropic()
        else:
            self._send_json(404, {"error": {"message": f"Hermes proxy only serves /v1/chat/completions and /v1/embeddings. Role={PROXY_ROLE}",
                                             "type": "invalid_request_error", "code": "404"}})

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    # ─── /v1/embeddings — forward to NVIDIA integrate (R581: openclaw memorySearch) ───
    def _handle_embeddings(self):
        """Forward OpenAI-format /v1/embeddings to NVIDIA integrate API.

        R581: openclaw 2026.6.11 memorySearch defaults to openai provider and
        needs /v1/embeddings. HM2 has no openai key, but the 5 NVU_KEYS (nvapi-)
        can call integrate.api.nvidia.com/v1/embeddings directly (实测可用,
        model=nvidia/nv-embed-v1). This route exposes that via the local gateway
        so openclaw points its openai provider at localhost:40006 — keys stay in
        the gateway, symmetric with the chat path. Reuses cooldown.py per-key
        429 state machine under a virtual tier "embeddings_integrate" (isolated
        from chat tiers). Non-streaming; embeddings are returned in one shot.
        """
        if not self._check_auth():
            return
        t_start = time.time()
        request_id = str(uuid.uuid4())[:8]
        # Virtual tier name isolates embeddings cooldown from chat integrate tiers.
        EMB_TIER = "embeddings_integrate"
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            body_obj = json.loads(raw) if raw else {}
        except Exception as e:
            self._send_json(400, {"error": {"message": f"bad request: {e}",
                                            "type": "invalid_request_error", "code": "400"}})
            return
        emb_model = body_obj.get("model", "nvidia/nv-embed-v1")
        # rr starting index per-request (round-robin across NVU_KEYS)
        start_idx = (int(time.time() * 1000) // 1000) % max(NVU_NUM_KEYS, 1)
        tried_keys = []
        last_error = None
        for attempt in range(NVU_NUM_KEYS):
            key_idx = (start_idx + attempt) % NVU_NUM_KEYS
            if is_key_cooling(EMB_TIER, key_idx):
                continue
            tried_keys.append(key_idx)
            key = NVU_KEYS[key_idx]
            conn = None
            try:
                conn = http.client.HTTPSConnection(NV_INTEGRATE_HOST, timeout=60)
                fwd_headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {key}",
                    "Accept": "application/json",
                }
                conn.request("POST", "/v1/embeddings", body=raw, headers=fwd_headers)
                resp = conn.getresponse()
                resp_body = resp.read()
                status = resp.status
                # 429 → mark this key cooling, try next key
                if status == 429:
                    mark_key_cooling(EMB_TIER, key_idx)
                    last_error = f"429 key{key_idx}"
                    _log("NV-EMB", f"429 from integrate key{key_idx} model={emb_model}, cooling, trying next")
                    try: conn.close()
                    except Exception: pass
                    continue
                # success or non-429 error → relay to client as-is
                reset_key429_count(EMB_TIER, key_idx)
                # pass through upstream content-type
                ct = resp.getheader("Content-Type") or "application/json"
                self.send_response(status)
                self.send_header("Content-Type", ct)
                self.send_header("Content-Length", str(len(resp_body)))
                self.end_headers()
                self.wfile.write(resp_body)
                elapsed_ms = int((time.time() - t_start) * 1000)
                _log("NV-EMB", f"ok model={emb_model} key{key_idx} status={status} {elapsed_ms}ms req={request_id}")
                _log_metrics({
                    "request_id": request_id, "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "path": "/v1/embeddings", "proxy_role": PROXY_ROLE, "request_model": emb_model,
                    "mapped_model": emb_model, "agent_type": "embeddings",
                    "stream": False, "total_input_chars": len(raw),
                    "ttfb_ms": None, "duration_ms": elapsed_ms, "status": status,
                    "error_type": None if status < 400 else f"http_{status}",
                    "error_message": None if status < 400 else last_error,
                    "upstream": "nv_integrate", "key_idx": key_idx,
                })
                try: conn.close()
                except Exception: pass
                return
            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"
                _log("NV-EMB", f"key{key_idx} exception: {last_error}, trying next")
                if conn:
                    try: conn.close()
                    except Exception: pass
                continue
        # all keys exhausted or cooling
        elapsed_ms = int((time.time() - t_start) * 1000)
        _log("NV-EMB", f"all keys exhausted model={emb_model} tried={tried_keys} last={last_error} {elapsed_ms}ms req={request_id}")
        self._send_json(502, {"error": {
            "message": f"all embeddings keys exhausted (tried={tried_keys}, last={last_error})",
            "type": "invalid_request_error", "code": "502"}})

    # ─── /v1/chat/completions — OpenAI format (three agents / _nv) ───
    def _handle_openai_nv(self):
        """Handle OpenAI-format requests from Hermes agent.

        R38.12: ALL models use NVCF pexec (no LiteLLM routing).
        MSG-FIX: if messages ends with assistant role, append user "Continue."
        """
        if not self._check_auth():
            return
        t_start = time.time()
        request_id = str(uuid.uuid4())[:8]
        metrics = {
            "request_id": request_id,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "path": "/v1/chat/completions",
            "proxy_role": PROXY_ROLE,
            "request_model": "?",
            "mapped_model": "?",
            "agent_type": "_nv",
            "caller": _detect_caller(self.headers.get("User-Agent", ""), self.headers.get("X-Caller", "")),
            "stream": False,
            "total_input_chars": 0,
            "ttfb_ms": None,
            "duration_ms": 0,
            "status": 0,
            "error_type": None,
            "error_message": None,
            "upstream": "nv",
        }

        try:
            body_len = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(body_len) if body_len > 0 else b""
            body = json.loads(raw) if raw else {}
        except Exception as e:
            self._send_json(400, {"error": {"message": f"bad request: {e}", "type": "invalid_request_error", "code": "400"}})
            metrics["status"] = 400
            metrics["error_type"] = "BadRequest"
            _log_metrics(metrics)
            return

        request_model = body.get("model", DEFAULT_NV_MODEL)
        is_stream = body.get("stream", False)
        # mapped_model 先算, 供 per-model force-stream 排除判断 (R576)
        mapped_model = detect_nv_model(request_model)
        metrics["mapped_model"] = mapped_model
        metrics["start_tier_idx"] = get_tier_index(mapped_model)
        # R502: Force stream upgrade - non-stream requests upgraded to stream internally
        # to avoid NVCF pexec_timeout. kimi-k2.6 thinking needs full inference time in
        # non-stream mode; stream mode establishes TTFB earlier. SSE is accumulated and
        # returned as non-stream JSON to the caller.
        # R576 (2026-07-03): per-model 排除. dsv4p_nv 流式+thinking 实测 content 丢失 90%
        # (思考消耗 max_tokens, content 在末尾 chunk 且 finish=length 时不产生), 而走
        # integrate 非流原生 26-35s 正常返回 content, 故对 dsv4p_nv 关闭 force-stream.
        force_stream_upgrade = (NVU_FORCE_STREAM_UPGRADE == "1"
                                and not is_stream
                                and mapped_model not in NVU_FORCE_STREAM_EXCLUDE_MODELS)
        if force_stream_upgrade:
            body["stream"] = True
            is_stream_upstream = True
            _log("NV-FORCE-STREAM", "upgrading non-stream->stream for upstream (caller sees non-stream)")
        else:
            is_stream_upstream = is_stream
        metrics["request_model"] = request_model
        metrics["stream"] = is_stream  # record original caller intent
        metrics["force_stream_upgrade"] = force_stream_upgrade
        # OC-R3 (2026-07-01): 记录 reasoning_effort / thinking 以便按思考级别分桶回溯.
        # cc2 指出: 不记 effort 则 effort 类实验改前/改后无法分桶, bursty NVCF 下不可信.
        metrics["reasoning_effort"] = body.get("reasoning_effort")
        thinking_field = body.get("thinking")
        metrics["thinking_type"] = thinking_field.get("type") if isinstance(thinking_field, dict) else thinking_field

        json_chars = len(json.dumps(body))
        
        metrics["total_input_chars"] = json_chars

        # ─── MSG-FIX (R35.10) ───
        messages = body.get("messages", [])
        original_msg_count = len(messages)
        if messages and isinstance(messages[-1], dict) and messages[-1].get("role") == "assistant":
            body["messages"].append({"role": "user", "content": "Continue."})
            _log("MSG-FIX", f"appended user 'Continue.' (original msgs={original_msg_count}, "
                           f"now {len(body['messages'])})")

        # Add stream_options.include_usage for streaming metrics
        if is_stream_upstream and "stream_options" not in body:
            body["stream_options"] = {"include_usage": True}

        # ─── Execute request via NVCF pexec with three-tier fallback ───
        # thinking-timeout (2026-07-01, cc2 核对驱动): 思考型请求无论流式与否都用扩展 timeout.
        # 抓包实测: glm5_2 思考 16-63s, deepseek sglang 思考 5-30s; 默认 UPSTREAM_TIMEOUT=25s
        # 对 glm5_2 长思考太短, 流式请求被 25s 砍掉后多 key 重试累积 502 (cc2 复现 3/4 流式 502).
        # 判定: 该 model 的 inject 配置非空(网关会注入思考触发参数) OR 客户端自带思考参数.
        nvcf_cfg = NVCF_PEXEC_MODELS.get(mapped_model, {})
        is_thinking_req = bool(nvcf_cfg.get("inject")) or bool(body.get("reasoning_effort")) or bool(body.get("chat_template_kwargs")) or bool(body.get("thinking"))
        if force_stream_upgrade:
            result = execute_request(self, body, mapped_model, request_id, metrics, t_start, upstream_timeout_override=NVU_FORCE_STREAM_UPGRADE_TIMEOUT)
        elif is_thinking_req:
            result = execute_request(self, body, mapped_model, request_id, metrics, t_start, upstream_timeout_override=NVU_FORCE_STREAM_UPGRADE_TIMEOUT)
            _log("NV-THINKING-TIMEOUT", f"({mapped_model}) thinking request stream={is_stream} → extended timeout {NVU_FORCE_STREAM_UPGRADE_TIMEOUT}s")
        else:
            result = execute_request(self, body, mapped_model, request_id, metrics, t_start)

        if not result.success:
            if result.all_keys_exhausted:
                metrics["status"] = 429 if result.all_429 else 502
                metrics["error_type"] = "all_tiers_exhausted"
                metrics["duration_ms"] = result.elapsed_ms
                metrics["total_cycle_attempts"] = len(result.key_cycle_attempts)
                metrics["fallback_tiers_used"] = result.fallback_tiers_used
                metrics["tier_model"] = mapped_model
                metrics["error_subcategory"] = "all_tiers_failed_in_mapped_tier"
                metrics["tier_summaries"] = result.tier_attempts

                # ─── 跨机 peer fallback (2026-07-01) ───────────────────────
                # 本机单 tier 5 key 全失败(all_tiers_exhausted) 时, 转发到对端 nv_gw 同模型.
                # 循环防护: 请求头 X-Fallback-Hop ≥1 表示"我是被转发来的", 不再转发.
                # 安全: 只在 tier 耗尽时转发, 不在单 key SSL error 转发 (cc2 仲裁).
                # 429 (all_429) 是 key 级限流, 跨机不增加 key 池, 不转发 (直接返回让客户端退避).
                hop = self.headers.get("X-Fallback-Hop", "0")
                try:
                    hop_n = int(hop)
                except (ValueError, TypeError):
                    hop_n = 0
                is_429 = bool(result.all_429)
                # R797: per-model peer-fb skip. NVCF ai-glm-5_2 (3b9748d8) DEGRADING 全 key 坏,
                # peer (HM1 nv_gw) 同 function 同坏 → peer-fb 只会再烧 ~180s 才 502, 把
                # cc4101/cx4102/opclaw4103 卡死 ~360s. 跳过 peer-fb 让 agent 直接落 ms_gw.
                # env NVU_PEER_FB_SKIP_MODELS 逗号分隔, 默认含 glm5_2_nv. NVCF 恢复后清 env.
                _peer_skip = {m.strip() for m in os.environ.get(
                    "NVU_PEER_FB_SKIP_MODELS", "glm5_2_nv").split(",") if m.strip()}
                if (NVU_PEER_FALLBACK_ENABLED and NVU_PEER_FALLBACK_URL
                        and hop_n < 1 and not is_429
                        and mapped_model not in _peer_skip):
                    _log("NV-PEER-FB", f"local all_tiers_exhausted (model={mapped_model}), "
                                       f"attempting peer fallback to {NVU_PEER_FALLBACK_URL}")
                    ok = self._peer_fallback(body, mapped_model, is_stream, metrics)
                    if ok:
                        metrics["peer_fallback_used"] = True
                        _log_metrics(metrics)
                        return
                    _log("NV-PEER-FB", f"peer fallback FAILED for model={mapped_model}, "
                                       f"returning local 502")
                elif mapped_model in _peer_skip and hop_n < 1 and not is_429:
                    _log("NV-PEER-FB", f"model={mapped_model} in peer-fb skip list "
                                       f"(NVCF DEGRADING, peer same function also bad), "
                                       f"returning local 502 for agent ms_gw fallback")
                elif hop_n >= 1:
                    _log("NV-PEER-FB", f"peer-originated request (hop={hop_n}) also "
                                       f"all_tiers_exhausted, no further fallback, returning 502")

                _log_metrics(metrics)

                error_payload, client_status = format_nv_all_keys_exhausted(result, mapped_model, request_model)
                extra_hdrs = None
                if client_status == 429:
                    extra_hdrs = {"retry-after": "5"}
                self._send_json(client_status, error_payload, extra_headers=extra_hdrs)
                return
            else:
                error_json = result.final_error_json
                resp_status = result.final_resp_status
                error_payload, client_status = format_nv_error_upstream(error_json, request_model, resp_status)
                extra_hdrs = None
                if client_status == 429:
                    extra_hdrs = {"retry-after": "5"}
                metrics["status"] = client_status
                metrics["error_type"] = "nv_upstream_error"
                metrics["error_message"] = str(error_json)[:200]
                metrics["duration_ms"] = int((time.time() - t_start) * 1000)
                metrics["tier_model"] = mapped_model
                metrics["error_subcategory"] = "nv_upstream_error"
                _log_metrics(metrics)
                self._send_json(client_status, error_payload, extra_headers=extra_hdrs)
                return

        # ─── Success: pass through NVCF pexec response ───
        resp = result.resp
        conn = result.conn
        metrics["nv_key_idx"] = result.nv_key_idx
        # R784: per-key egress info for DB long-term IP-diversity analysis
        metrics["egress_route"] = result.egress_route
        metrics["egress_ip"] = result.egress_ip
        metrics["litellm_model"] = result.nv_model_label
        metrics["tier_model"] = result.tier_model
        metrics["fallback_tiers_used"] = result.fallback_tiers_used
        if result.key_cycle_attempts:
            metrics["key_cycle_429s_before_success"] = len(result.key_cycle_attempts)
            metrics["key_cycle_details"] = result.key_cycle_attempts
        if result.fallback_tiers_used and len(result.fallback_tiers_used) > 1:
            metrics["fallback_occurred"] = True

        cached_body = getattr(resp, '_hm_cached_body', None)

        if is_stream and not force_stream_upgrade:
            self._stream_openai_passthrough(resp, conn, metrics, t_start, request_model)
        elif force_stream_upgrade:
            # R502: Accumulate SSE stream -> reconstruct non-stream JSON for caller
            self._accumulate_stream_to_nonstream(resp, conn, metrics, t_start, request_model)
        else:
            ttfb_start = time.time()
            if cached_body is not None:
                resp_body = cached_body
            else:
                resp_body = resp.read()
            metrics["status"] = 200
            metrics["duration_ms"] = int((time.time() - t_start) * 1000)
            metrics["ttfb_ms"] = int((ttfb_start - t_start) * 1000)

            try:
                oai_response = json.loads(resp_body)
                usage = oai_response.get("usage", {})
                metrics["input_tokens"] = usage.get("prompt_tokens", 0)
                metrics["output_tokens"] = usage.get("completion_tokens", 0)
                choices = oai_response.get("choices", [])
                if choices:
                    metrics["finish_reason"] = choices[0].get("finish_reason")
            except Exception:
                pass

            # R844 F9: 非流式 success 路径 zombie 保护 (与 F8 互补).
            # fr in (stop,tool_calls) + content/reasoning<50 + input>=5000 + 无真 tool_calls → 空僵尸.
            # 改写 finish_reason=content_filter, 让 cc4101 (F4) 触发 api_error 重试, 不透传空响应.
            try:
                _oai = oai_response if ('oai_response' in dir() and isinstance(oai_response, dict)) else json.loads(resp_body)
                _choices = _oai.get("choices", []) if isinstance(_oai, dict) else []
                if _choices and isinstance(_choices[0], dict):
                    _fr = _choices[0].get("finish_reason")
                    _msg = _choices[0].get("message") or {}
                    _cont = _msg.get("content") or ""
                    _rcont = _msg.get("reasoning_content") or ""
                    _real_tc = any(
                        (tc.get("function", {}).get("arguments") if isinstance(tc, dict) else "")
                        for tc in (_msg.get("tool_calls") or [])
                    )
                    _cont_len = len(_cont) if isinstance(_cont, str) else 0
                    _rcont_len = len(_rcont) if isinstance(_rcont, str) else 0
                    if (_fr in ("stop", "tool_calls")
                            and not _real_tc
                            and (_cont_len + _rcont_len) < NVU_ZOMBIE_EMPTY_CONTENT_CHARS
                            and metrics.get("total_input_chars", 0) >= NVU_ZOMBIE_MIN_INPUT_CHARS):
                        _log("NV-ZOMBIE-NONSTREAM", f"({request_model}) non-stream zombie: fr={_fr} "
                            f"content={_cont_len}c reasoning={_rcont_len}c input="
                            f"{metrics.get('total_input_chars',0)}c no real tool_calls — rewriting to content_filter")
                        metrics["error_type"] = "zombie_empty_completion"
                        metrics["finish_reason"] = "content_filter"
                        # 改写 body: finish_reason → content_filter, 清空 content
                        _choices[0]["finish_reason"] = "content_filter"
                        if isinstance(_msg, dict):
                            _msg["content"] = ""
                        resp_body = json.dumps(_oai).encode("utf-8")
            except Exception as _e:
                _log("ERR", f"NV-ZOMBIE-NONSTREAM check failed: {_e}")

            _log_metrics(metrics)

            self.send_response(resp.status)
            for h in ["Content-Type"]:
                v = resp.getheader(h)
                if v:
                    self.send_header(h, v)
            self.send_header("Content-Length", str(len(resp_body)))
            self.end_headers()
            self.wfile.write(resp_body)
            conn.close()

    def _accumulate_stream_to_nonstream(self, resp, conn, metrics, t_start, request_model):
        """R502: Read SSE stream from upstream, accumulate chunks, return as non-stream JSON.

        The upstream was sent stream=True (because of FORCE_STREAM_UPGRADE), but the
        caller expects a non-stream JSON response. We accumulate all SSE data chunks,
        reconstruct the OpenAI non-stream format, and return it to the caller.
        """
        sse_buffer = ""
        all_content_parts = []
        reasoning_content_parts = []
        finish_reason = None
        model_id = None
        usage = {}
        ttfb_recorded = False
        chunk_id = None

        try:
            while True:
                try:
                    chunk = resp.read(8192)
                except socket.timeout:
                    # R1408: per-read 短轮询 (POLL_S=15s) 超时, 非致命. continue 回循环顶,
                    # 让 60s/90s/20s deadline 检查判定是否真 stall. 命中真 stall 时上面已设
                    # metrics["error_type"] 并 break; 这里只是唤醒.
                    continue
                except OSError as _re:
                    # per-read 短轮询超时后下次 read 抛裸 OSError("cannot read from timed out object")
                    # (socket.py:717), 非 socket.timeout 子类. 当非致命 continue (同 cc4101 R846 修3).
                    if "timed out object" in str(_re) or "timeout" in str(_re).lower():
                        continue
                    raise
                if not chunk:
                    break

                if not ttfb_recorded:
                    metrics["ttfb_ms"] = int((time.time() - t_start) * 1000)
                    ttfb_recorded = True

                sse_buffer += chunk.decode("utf-8", errors="replace")

                while "\n" in sse_buffer:
                    line, sse_buffer = sse_buffer.split("\n", 1)
                    line = line.strip()
                    if not line or line.startswith(":"):
                        continue
                    if not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if data_str == "[DONE]" or not data_str:
                        continue
                    try:
                        data = json.loads(data_str)
                        # Extract content from choices
                        choices = data.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            rc = delta.get("reasoning_content")
                            if rc:
                                reasoning_content_parts.append(rc)
                            cont = delta.get("content")
                            if cont:
                                all_content_parts.append(cont)
                            fr = choices[0].get("finish_reason")
                            if fr:
                                finish_reason = fr
                        # Extract model and id
                        if not model_id:
                            model_id = data.get("model", "")
                        if not chunk_id:
                            chunk_id = data.get("id", "")
                        # Extract usage
                        chunk_usage = data.get("usage", {})
                        if chunk_usage:
                            pt = chunk_usage.get("prompt_tokens", 0)
                            ct = chunk_usage.get("completion_tokens", 0)
                            if pt > 0:
                                usage["prompt_tokens"] = pt
                            if ct > 0:
                                usage["completion_tokens"] = ct
                    except json.JSONDecodeError:
                        pass

            # R576 (2026-07-03): 处理 sse_buffer 残留.
            # 循环 while "\n" in sse_buffer 只处理含换行的完整行, 最后一行若无 trailing
            # newline (常见于 NVCF/integrate 流末尾的 content chunk, 连接读完即断) 会留在
            # sse_buffer 未被解析 → content 丢失 (实测 dsv4p force-stream 19/21 content=0c).
            # 修复: 循环结束后对 sse_buffer 残留再跑一遍行解析.
            if sse_buffer.strip():
                line = sse_buffer.strip()
                if line.startswith("data:"):
                    data_str = line[5:].strip()
                    if data_str and data_str != "[DONE]":
                        try:
                            data = json.loads(data_str)
                            choices = data.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                rc = delta.get("reasoning_content")
                                if rc:
                                    reasoning_content_parts.append(rc)
                                cont = delta.get("content")
                                if cont:
                                    all_content_parts.append(cont)
                                fr = choices[0].get("finish_reason")
                                if fr:
                                    finish_reason = fr
                            if not model_id:
                                model_id = data.get("model", "")
                            if not chunk_id:
                                chunk_id = data.get("id", "")
                            chunk_usage = data.get("usage", {})
                            if chunk_usage:
                                pt = chunk_usage.get("prompt_tokens", 0)
                                ct = chunk_usage.get("completion_tokens", 0)
                                if pt > 0:
                                    usage["prompt_tokens"] = pt
                                if ct > 0:
                                    usage["completion_tokens"] = ct
                        except json.JSONDecodeError:
                            pass

        except (http.client.RemoteDisconnected, ConnectionResetError, OSError,
                http.client.IncompleteRead, socket.timeout) as e:
            elapsed_ms = int((time.time() - t_start) * 1000)
            error_class = type(e).__name__
            _log("ERR", f"FORCE-STREAM-ACCUMULATE {error_class} after {elapsed_ms}ms: {e}")
            metrics["error_type"] = f"ForceStreamAccumulate_{error_class}"
        except Exception as e:
            elapsed_ms = int((time.time() - t_start) * 1000)
            error_class = type(e).__name__
            _log("ERR", f"FORCE-STREAM-ACCUMULATE unexpected {error_class} after {elapsed_ms}ms: {e}")
            metrics["error_type"] = f"ForceStreamAccumulate_{error_class}"

        if metrics.get("error_type"):
            metrics["status"] = 502
            metrics["duration_ms"] = int((time.time() - t_start) * 1000)
            # R507: ensure tier_model set even on force_stream_upgrade error path
            if not metrics.get("tier_model"):
                metrics["tier_model"] = metrics.get("mapped_model")
            _log_metrics(metrics)
            self._send_json(502, {"error": {"message": "upstream stream accumulation failed",
                                            "type": "upstream_error", "code": "502"}})
            try:
                conn.close()
            except Exception:
                pass
            return

        # Reconstruct non-stream OpenAI response format
        full_content = "".join(all_content_parts)
        full_reasoning = "".join(reasoning_content_parts)
        message = {"role": "assistant", "content": full_content}
        if full_reasoning:
            message["reasoning_content"] = full_reasoning

        non_stream_resp = {
            "id": chunk_id or ("chatcmpl-" + str(uuid.uuid4())[:8]),
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model_id or request_model,
            "choices": [{
                "index": 0,
                "message": message,
                "finish_reason": finish_reason or "stop",
            }],
        }
        if usage:
            non_stream_resp["usage"] = usage

        resp_body = json.dumps(non_stream_resp, ensure_ascii=False).encode("utf-8")

        # Update metrics
        metrics["status"] = 200
        metrics["duration_ms"] = int((time.time() - t_start) * 1000)
        if not metrics.get("ttfb_ms"):
            metrics["ttfb_ms"] = metrics["duration_ms"]
        if usage:
            metrics["input_tokens"] = usage.get("prompt_tokens", 0)
            metrics["output_tokens"] = usage.get("completion_tokens", 0)
        metrics["finish_reason"] = finish_reason or "stop"
        metrics["accumulated_stream_chars"] = len(full_content)
        if full_reasoning:
            metrics["accumulated_reasoning_chars"] = len(full_reasoning)

        _log("NV-FORCE-STREAM-OK", f"accumulated {len(all_content_parts)} chunks, "
              f"content={len(full_content)}c reasoning={len(full_reasoning)}c in {metrics['duration_ms']}ms")
        _log_metrics(metrics)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resp_body)))
        self.end_headers()
        self.wfile.write(resp_body)
        try:
            conn.close()
        except Exception:
            pass

    # ─── R1648b: /v1/messages — anthropic Messages endpoint ─────────────
    # Serves Claude Code (via cc4101, which after R1648e becomes a pure
    # passthrough to this endpoint). Flow: auth → anth_to_oai → execute_request
    # (existing NVCF 5key×mode chain) → oai SSE → anthropic SSE back to client.
    # No fallback in R1648b (R1648c adds 5key全坏→ms_gw). Isolated from the
    # openai /v1/chat/completions path by routing + a separate write helper.
    def _handle_messages_anthropic(self):
        if not self._check_auth():
            return
        t_start = time.time()
        request_id = str(uuid.uuid4())[:8]
        metrics = {
            "request_id": request_id,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "path": "/v1/messages",
            "proxy_role": PROXY_ROLE,
            "request_model": "?",
            "mapped_model": "?",
            "agent_type": "_nv_anthropic",
            "caller": _detect_caller(self.headers.get("User-Agent", ""), self.headers.get("X-Caller", "")),
            "stream": False,
            "total_input_chars": 0,
            "estimated_input_tokens": 0,
            "num_messages": 0,
            "num_tools": 0,
            "ttfb_ms": None,
            "duration_ms": 0,
            "status": 0,
            "finish_reason": None,
            "input_tokens": 0,
            "output_tokens": 0,
            "error_type": None,
            "error_message": None,
            "upstream": "nv",
        }

        try:
            body_len = int(self.headers.get("Content-Length", 0))
            if body_len <= 0 or body_len > 50 * 1024 * 1024:
                self._send_json(413, {"type": "error", "error": {
                    "type": "invalid_request_error",
                    "message": f"request body size {body_len} out of range (max 50MB)"}})
                metrics["status"] = 413
                metrics["error_type"] = "PayloadTooLarge"
                _log("ERROR", f"anth /v1/messages body size {body_len} rejected")
                _log_metrics(metrics)
                return
            raw_body = self.rfile.read(body_len)
            anth_body = json.loads(raw_body) if raw_body else {}
        except Exception as e:
            self._send_json(400, {"type": "error", "error": {
                "type": "invalid_request_error", "message": f"bad request: {e}"}})
            metrics["status"] = 400
            metrics["error_type"] = "BadRequest"
            _log("ERROR", f"anth /v1/messages bad request: {e}")
            _log_metrics(metrics)
            return

        request_model = anth_body.get("model", DEFAULT_NV_MODEL)
        is_stream = bool(anth_body.get("stream", False))
        mapped_model = detect_nv_model(request_model)
        metrics["request_model"] = request_model
        metrics["mapped_model"] = mapped_model
        metrics["start_tier_idx"] = get_tier_index(mapped_model)
        metrics["stream"] = is_stream
        # thinking_type for deadline scaling (mirrors _handle_openai_nv)
        thinking_field = anth_body.get("thinking")
        metrics["thinking_type"] = thinking_field.get("type") if isinstance(thinking_field, dict) else thinking_field

        # Anthropic → OpenAI request body (uses mapped_model as upstream model id)
        try:
            oai_body = anth_to_openai(anth_body, target_model=mapped_model)
        except Exception as e:
            self._send_json(400, {"type": "error", "error": {
                "type": "invalid_request_error", "message": f"format conversion failed: {e}"}})
            metrics["status"] = 400
            metrics["error_type"] = "FormatConversion"
            _log("ERROR", f"anth_to_openai failed: {e}")
            _log_metrics(metrics)
            return
        metrics["num_messages"] = len(oai_body.get("messages", []))
        metrics["num_tools"] = len(oai_body.get("tools", []))
        text_chars = _estimate_text_chars(oai_body)
        metrics["total_input_chars"] = text_chars
        metrics["estimated_input_tokens"] = int(text_chars / CHARS_PER_TOKEN_ESTIMATE)

        # R684 (same as cc4101): always force upstream stream=True — glm5.2 non-stream
        # returns empty content / finish_reason=length. is_stream here is the *client*
        # intent (CC stream=true → real-time SSE; stream=false → we collect+synthesize).
        oai_body["stream"] = True
        oai_body["stream_options"] = {"include_usage": True}
        is_stream_upstream = True

        # MSG-FIX parity with _handle_openai_nv: trailing assistant → user "Continue."
        messages = oai_body.get("messages", [])
        if messages and isinstance(messages[-1], dict) and messages[-1].get("role") == "assistant":
            oai_body["messages"].append({"role": "user", "content": "Continue."})

        # thinking-timeout parity (extended timeout for thinking requests)
        nvcf_cfg = NVCF_PEXEC_MODELS.get(mapped_model, {})
        is_thinking_req = bool(nvcf_cfg.get("inject")) or bool(oai_body.get("reasoning_effort")) or bool(oai_body.get("chat_template_kwargs")) or bool(oai_body.get("thinking"))
        if is_thinking_req:
            _log("NV-ANTH-THINKING", f"({mapped_model}) anth /v1/messages thinking request stream={is_stream}")
            result = execute_request(self, oai_body, mapped_model, request_id, metrics, t_start, upstream_timeout_override=NVU_FORCE_STREAM_UPGRADE_TIMEOUT)
        else:
            result = execute_request(self, oai_body, mapped_model, request_id, metrics, t_start)

        if not result.success:
            # Error path: return anthropic-format error (CC retries on api_error).
            if result.all_keys_exhausted:
                error_payload = format_nv_all_keys_exhausted(result, mapped_model, request_model)
                # format_nv_all_keys_exhausted returns (openai_payload, client_status)
                anth_err = convert_error_to_anth(error_payload[0], request_model)
                client_status = error_payload[1]
            else:
                error_json = result.final_error_json or {"error": {"message": getattr(result, "final_error_message", "") or "upstream failed"}}
                resp_status = result.final_resp_status or 502
                client_status = resp_status
                anth_err = convert_error_to_anth(error_json, request_model)
            extra_hdrs = {"retry-after": "5"} if client_status == 429 else None
            metrics["status"] = client_status
            metrics["error_type"] = "all_tiers_exhausted" if result.all_keys_exhausted else "nv_upstream_error"
            metrics["error_message"] = str(anth_err)[:200]
            metrics["duration_ms"] = int((time.time() - t_start) * 1000)
            if not metrics.get("tier_model"):
                metrics["tier_model"] = mapped_model
            _log_metrics(metrics)
            self._send_json(client_status, anth_err, extra_headers=extra_hdrs)
            return

        # ─── Success: stream or collect → anthropic SSE/JSON ───
        resp = result.resp
        conn = result.conn
        metrics["nv_key_idx"] = result.nv_key_idx
        metrics["tier_model"] = result.tier_model
        metrics["fallback_tiers_used"] = result.fallback_tiers_used
        if result.fallback_tiers_used and len(result.fallback_tiers_used) > 1:
            metrics["fallback_occurred"] = True

        if is_stream:
            self._stream_openai_to_anth(resp, conn, metrics, t_start, request_model)
        else:
            # Collect upstream stream, synthesize non-stream Anthropic JSON (mirrors
            # cc4101 collect_stream_to_anth). Reuses _accumulate_stream_to_nonstream's
            # read loop by collecting parts here, then oai_nonstream_to_anth.
            self._collect_stream_to_anth(resp, conn, metrics, t_start, request_model)

    def _stream_openai_to_anth(self, resp, conn, metrics, t_start, request_model):
        """Read NVCF OpenAI-SSE stream, convert each chunk to Anthropic SSE, write
        to client. Reuses the same deadline/zombie/poll infrastructure as
        _stream_openai_passthrough, but routes parsed chunks through
        OaiSseToAnthropicConverter instead of raw passthrough.

        R1648b: no breaker / no fallback here (R1648c adds nv breaker). Zombie/empty
        detection is kept so we emit api_error SSE (CC retries) instead of end_turn
        on empty completions — same survival semantics cc4101 had.
        """
        converter = OaiSseToAnthropicConverter(request_model)
        ttfb_recorded = False
        streaming_input_tokens = 0
        streaming_output_tokens = 0
        sse_buffer = ""
        # zombie/empty detection accumulators (mirror _stream_openai_passthrough)
        content_chars = 0
        reasoning_chars = 0
        saw_tool_calls = False
        zombie_detected = False

        # R850/R1407/R1627 deadline infrastructure (same as passthrough)
        _idle_s = NVU_STREAM_TOTAL_DEADLINE_S
        if metrics.get("thinking_type"):
            _idle_s = _idle_s * 2
        stream_idle_deadline = None
        _ic = metrics.get("total_input_chars", 0) or 0
        if _ic <= 50000:
            _fb_s = NVU_STREAM_FIRST_BYTE_DEADLINE_S
        elif _ic <= 200000:
            _fb_s = 60.0
        elif _ic <= 350000:
            _fb_s = 90.0
        else:
            _fb_s = 120.0
        stream_first_byte_deadline = time.time() + _fb_s
        _no_content_gap_s = NVU_STREAM_NO_CONTENT_GAP_S
        if _ic > 350000:
            _no_content_gap_s = 90.0
        elif _ic > 200000:
            _no_content_gap_s = 80.0
        if metrics.get("thinking_type"):
            _no_content_gap_s = _no_content_gap_s * 2
        last_real_content_time = None

        _poll_sock = None
        try:
            _poll_sock = conn.sock
            if _poll_sock is None and resp is not None:
                try:
                    _poll_sock = resp.fp.raw._sock
                except Exception:
                    _poll_sock = None
            if _poll_sock is not None:
                _poll_sock.settimeout(NVU_STREAM_POLL_S)
        except Exception as _e:
            _log("WARN", f"({request_model}) R1648b anth set poll socktimeout failed: {_e}")

        # SSE headers (anthropic event-stream)
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.close_connection = True
            self.end_headers()
        except (BrokenPipeError, ConnectionResetError, OSError) as e:
            _log("ERR", f"({request_model}) anth client gone before SSE headers: {e}")
            metrics["error_type"] = "client_gone_pre_stream"
            metrics["status"] = 499
            metrics["duration_ms"] = int((time.time() - t_start) * 1000)
            _log_metrics(metrics)
            try:
                conn.close()
            except Exception:
                pass
            return

        interrupted = False
        try:
            while True:
                if stream_idle_deadline is not None and time.time() > stream_idle_deadline:
                    metrics["error_type"] = "stream_total_deadline"
                    _log("NV-ANTH-DEADLINE", f"({request_model}) anth idle deadline exceeded")
                    interrupted = True
                    break
                if last_real_content_time is not None and time.time() - last_real_content_time > _no_content_gap_s:
                    metrics["error_type"] = "stream_no_content_gap"
                    _log("NV-ANTH-NO-CONTENT-GAP", f"({request_model}) anth no real content for "
                        f"{int(time.time()-last_real_content_time)}s")
                    interrupted = True
                    break
                if not ttfb_recorded and time.time() > stream_first_byte_deadline:
                    metrics["error_type"] = "stream_first_byte_timeout"
                    _log("NV-ANTH-FIRST-BYTE", f"({request_model}) anth first-byte deadline exceeded")
                    interrupted = True
                    break
                try:
                    chunk = resp.read(8192)
                except socket.timeout:
                    continue
                except OSError as _re:
                    if "timed out object" in str(_re) or "timeout" in str(_re).lower():
                        continue
                    raise
                if not chunk:
                    break
                if not ttfb_recorded:
                    metrics["ttfb_ms"] = int((time.time() - t_start) * 1000)
                    ttfb_recorded = True
                    stream_idle_deadline = time.time() + _idle_s
                    last_real_content_time = time.time()
                sse_buffer += chunk.decode("utf-8", errors="replace")

                # parse complete SSE events out of the buffer
                while "\n\n" in sse_buffer:
                    event_str, sse_buffer = sse_buffer.split("\n\n", 1)
                    data_str = ""
                    for line in event_str.split("\n"):
                        if line.startswith("data:"):
                            data_str = line[5:].strip()
                    if not data_str or data_str == "[DONE]":
                        continue
                    try:
                        chunk_data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    # track usage
                    chunk_usage = chunk_data.get("usage") or {}
                    if chunk_usage:
                        pt = chunk_usage.get("prompt_tokens", 0)
                        ct = chunk_usage.get("completion_tokens", 0)
                        if pt > 0:
                            streaming_input_tokens = pt
                        if ct > 0:
                            streaming_output_tokens = ct
                    choices = chunk_data.get("choices") or [{}]
                    delta = choices[0].get("delta") or {}
                    cont = delta.get("content")
                    if cont:
                        content_chars += len(cont)
                    rcont = delta.get("reasoning_content")
                    if rcont:
                        reasoning_chars += len(rcont)
                    for _tc in (delta.get("tool_calls") or []):
                        _fn = _tc.get("function", {}) if isinstance(_tc, dict) else {}
                        if _fn.get("arguments"):
                            saw_tool_calls = True
                    if cont or rcont or (delta.get("tool_calls") or []):
                        stream_idle_deadline = time.time() + _idle_s
                        last_real_content_time = time.time()
                    fr = choices[0].get("finish_reason")
                    if fr:
                        metrics["finish_reason"] = fr
                        # zombie detection (mirror passthrough R840/R852b)
                        if (fr in ("stop", "tool_calls")
                                and not saw_tool_calls
                                and content_chars < NVU_ZOMBIE_EMPTY_CONTENT_CHARS
                                and metrics.get("total_input_chars", 0) >= NVU_ZOMBIE_MIN_INPUT_CHARS):
                            zombie_detected = True
                            metrics["error_type"] = "zombie_empty_completion"
                            _log("NV-ANTH-ZOMBIE", f"({request_model}) anth zombie empty: fr={fr} "
                                f"content={content_chars}c reasoning={reasoning_chars}c input="
                                f"{metrics.get('total_input_chars',0)}c")
                    # convert + write
                    out_bytes = converter.feed_chunk(chunk_data)
                    if out_bytes:
                        try:
                            self.wfile.write(out_bytes)
                            self.wfile.flush()
                        except (BrokenPipeError, ConnectionResetError, OSError):
                            interrupted = True
                            break
        except (http.client.RemoteDisconnected, ConnectionResetError, OSError,
                http.client.IncompleteRead, socket.timeout) as e:
            error_class = type(e).__name__
            _log("ERR", f"NV-ANTH stream {error_class} after {int((time.time()-t_start)*1000)}ms: {e}")
            metrics["error_type"] = f"NVAnth_{error_class}"
            interrupted = True
        except Exception as e:
            error_class = type(e).__name__
            _log("ERR", f"NV-ANTH stream unexpected {error_class}: {e}")
            metrics["error_type"] = f"NVAnth_{error_class}"
            interrupted = True

        if metrics.get("error_type"):
            metrics["status"] = 502
        else:
            metrics["status"] = 200
        metrics["duration_ms"] = int((time.time() - t_start) * 1000)
        if streaming_input_tokens > 0:
            metrics["input_tokens"] = streaming_input_tokens
        if streaming_output_tokens > 0:
            metrics["output_tokens"] = streaming_output_tokens
        _log_metrics(metrics)

        # terminal SSE events. On zombie or interrupt → api_error so CC retries
        # (only safe if we haven't flushed real content yet; if content_chars>0 the
        # stream is partially delivered — still emit a graceful end so CC sees a
        # complete message boundary rather than a dangling one).
        is_zombie = zombie_detected
        is_interrupted_no_content = interrupted and content_chars == 0
        try:
            fin = converter.finish(
                interrupted=(is_interrupted_no_content and not is_zombie),
                zombie=is_zombie or is_interrupted_no_content,
                input_tokens_real=streaming_input_tokens,
            )
            if fin:
                self.wfile.write(fin)
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        try:
            conn.close()
        except Exception:
            pass

    def _collect_stream_to_anth(self, resp, conn, metrics, t_start, request_model):
        """Collect upstream OpenAI-SSE stream, synthesize a non-stream Anthropic
        message JSON (mirrors cc4101 collect_stream_to_anth). CC stream=false path.
        """
        sse_buffer = ""
        all_content_parts = []
        reasoning_parts = []
        tool_calls_data = []
        finish_reason = "stop"
        msg_id = f"msg_{uuid.uuid4().hex[:24]}"
        total_input_tokens = 0
        total_output_tokens = 0
        ttfb_recorded = False

        try:
            while True:
                try:
                    chunk = resp.read(8192)
                except socket.timeout:
                    continue
                except OSError as _re:
                    if "timed out object" in str(_re) or "timeout" in str(_re).lower():
                        continue
                    raise
                if not chunk:
                    break
                if not ttfb_recorded:
                    metrics["ttfb_ms"] = int((time.time() - t_start) * 1000)
                    ttfb_recorded = True
                sse_buffer += chunk.decode("utf-8", errors="replace")
                while "\n\n" in sse_buffer:
                    event_str, sse_buffer = sse_buffer.split("\n\n", 1)
                    data_str = ""
                    for line in event_str.split("\n"):
                        if line.startswith("data:"):
                            data_str = line[5:].strip()
                    if not data_str or data_str == "[DONE]":
                        continue
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    msg_id = data.get("id", msg_id)
                    choices = data.get("choices") or [{}]
                    delta = choices[0].get("delta") or {}
                    fr = choices[0].get("finish_reason")
                    rc = delta.get("reasoning_content") or ""
                    if rc:
                        reasoning_parts.append(rc)
                    cont = delta.get("content") or ""
                    if cont:
                        all_content_parts.append(cont)
                    for tc in (delta.get("tool_calls") or []):
                        fn = tc.get("function", {}) or {}
                        if tc.get("id"):
                            tool_calls_data.append({"id": tc["id"], "name": fn.get("name", ""), "arguments": fn.get("arguments", "")})
                        elif fn.get("arguments") and tool_calls_data:
                            tool_calls_data[-1]["arguments"] += fn["arguments"]
                    chunk_usage = data.get("usage") or {}
                    if chunk_usage:
                        total_input_tokens = chunk_usage.get("prompt_tokens", total_input_tokens)
                        total_output_tokens = chunk_usage.get("completion_tokens", total_output_tokens)
                    if fr:
                        finish_reason = fr
        except (http.client.RemoteDisconnected, ConnectionResetError, OSError,
                http.client.IncompleteRead, socket.timeout) as e:
            error_class = type(e).__name__
            _log("ERR", f"NV-ANTH collect {error_class} after {int((time.time()-t_start)*1000)}ms: {e}")
            metrics["error_type"] = f"NVAnthCollect_{error_class}"
        except Exception as e:
            error_class = type(e).__name__
            _log("ERR", f"NV-ANTH collect unexpected {error_class}: {e}")
            metrics["error_type"] = f"NVAnthCollect_{error_class}"

        content_text = "".join(all_content_parts)
        reasoning_text = "".join(reasoning_parts)

        # empty/zombie detection (mirror cc4101 collect)
        if finish_reason == "content_filter":
            metrics["empty_stream_response"] = True
            metrics["error_type"] = "upstream_content_filter"
        elif (not reasoning_text and not content_text and not tool_calls_data):
            metrics["empty_stream_response"] = True
        elif (finish_reason in ("stop", "tool_calls")
              and (len(reasoning_text) + len(content_text)) < 50
              and not any(tc.get("arguments") for tc in tool_calls_data)
              and metrics.get("total_input_chars", 0) >= 5000):
            metrics["empty_stream_response"] = True
            metrics["error_type"] = "zombie_empty_completion"

        if metrics.get("error_type"):
            metrics["status"] = 502
        else:
            metrics["status"] = 200
        metrics["duration_ms"] = int((time.time() - t_start) * 1000)
        metrics["input_tokens"] = total_input_tokens
        metrics["output_tokens"] = total_output_tokens
        metrics["finish_reason"] = finish_reason
        _log_metrics(metrics)

        if metrics.get("status") >= 400:
            anth_err = convert_error_to_anth(
                {"error": {"message": metrics.get("error_message") or metrics.get("error_type") or "upstream stream failed"}},
                request_model)
            self._send_json(metrics["status"], anth_err)
            try:
                conn.close()
            except Exception:
                pass
            return

        # synthesize non-stream Anthropic message JSON
        content = []
        if reasoning_text:
            content.append({"type": "thinking", "thinking": reasoning_text,
                            "signature": OAI_TO_ANTH_THINKING_SIG})
        if content_text:
            content.append({"type": "text", "text": content_text})
        for tc_data in tool_calls_data:
            try:
                input_data = json.loads(tc_data["arguments"])
            except json.JSONDecodeError:
                input_data = {"raw": tc_data["arguments"]}
            content.append({"type": "tool_use", "id": tc_data["id"],
                            "name": tc_data["name"], "input": input_data})
        if not content:
            content.append({"type": "text", "text": ""})
        stop_reason = "end_turn"
        if finish_reason == "length":
            stop_reason = "max_tokens"
        elif finish_reason == "tool_calls":
            stop_reason = "tool_use"
        anth_response = {
            "id": msg_id, "type": "message", "role": "assistant", "model": request_model,
            "content": content, "stop_reason": stop_reason, "stop_sequence": None,
            "usage": {"input_tokens": total_input_tokens, "output_tokens": total_output_tokens,
                      "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0},
        }
        self._send_json(metrics["status"], anth_response)
        try:
            conn.close()
        except Exception:
            pass

    def _stream_openai_passthrough(self, resp, conn, metrics, t_start, request_model):
        """Pass through OpenAI streaming SSE response directly to Hermes."""
        ttfb_recorded = False
        streaming_input_tokens = 0
        streaming_output_tokens = 0
        sse_buffer = ""
        # R840: 累积 content 字符数 + 是否见 tool_calls, 用于僵尸空响应检测.
        passthrough_content_chars = 0
        passthrough_reasoning_chars = 0  # R844 F3: 累积 reasoning_content (glm5.2 思考在此)
        passthrough_saw_tool_calls = False
        # R840: 僵尸空响应标记. 见 finish_reason=stop 且 content_chars<阈值 且无 tool_calls 且
        # 有 input → 判定空僵尸, 不写终末 chunk, abort 连接让 openclaw 走 fallback.
        zombie_detected = False
        # R1627: 全量缓冲模式. 不边读边 flush, 缓冲到流结束再一次性 flush 下游.
        # NVCF 卡死时丢弃缓冲 (从未 flush -> Scenario A 零内容 -> content_filter -> CC 自动重试).
        buffer_chunks = [] if NVU_STREAM_FULL_BUFFER else None
        # R850: 流式 idle deadline (真内容刷新, 非 ttfb 固定). 旧洞(R835): deadline = ttfb+90s
        # 固定不刷新 → GLM5.2 thinking 请求首块 reasoning 后上游长时间静默思考(实测>120s不发chunk),
        # 90s 固定 deadline 把还在思考的流误切 → 发 content_filter → cc4101 报 "Server error mid-response".
        # 现: ttfb 时设一次, 之后每收到真内容(content/reasoning_content/tool_calls)就刷新 = now+DEADLINE,
        # 只在"真内容间隔超 DEADLINE"才判 idle 切断. thinking 静默期间上游不发chunk→nv_gw的read阻塞→
        # 不刷新但也不误切(因为deadline只在收到chunk时检查, 阻塞期不检查). 真断流=read返回空或抛异常.
        # thinking 请求 DEADLINE 翻倍(容纳长思考): metrics.thinking_type 非空即 thinking 请求.
        _idle_s = NVU_STREAM_TOTAL_DEADLINE_S
        if metrics.get("thinking_type"):
            _idle_s = _idle_s * 2  # thinking 静默期长, 90s→180s
        stream_idle_deadline = None
        # R839: 首字节前绝对 deadline. 兜 "upstream 返回 200 头但 body 首字节永不来" (idle 盲区).
        # R1416: 固定 20s 对超大 context 请求太激进. DB 实测 (14:49-14:58 批):
        # total_input_chars=353,492 的请求 NVCF 正常 prefill 需 ttfb 43-81s 才吐首字节,
        # 固定 20s 把本来能成功的请求误杀成 zombie content_filter -> cc4101 重试同一个超大请求
        # -> 又 20s 超时 -> 死循环 (14:49-14:53 连发 7 次 first_byte_timeout). 改: 按 input 大小
        # 缩放 first-byte deadline, 小请求仍快失败 (抓真 hang), 大请求给足 prefill 时间.
        _ic = metrics.get("total_input_chars", 0) or 0
        if _ic <= 50000:
            _fb_s = NVU_STREAM_FIRST_BYTE_DEADLINE_S  # 默认 20s, 小请求
        elif _ic <= 200000:
            _fb_s = 60.0
        elif _ic <= 350000:
            _fb_s = 90.0
        else:
            _fb_s = 120.0
        stream_first_byte_deadline = time.time() + _fb_s
        # R1407: 真内容 idle gap 硬兜底. 旧洞 (R1405 诊断): NVCF 对大 context (~297K) 请求返回 200 头
        # + 持续发空 delta / SSE comment chunk 维持连接, 但真 content/reasoning/tool_calls 迟迟不来.
        # stream_idle_deadline (R850) 只在收到真内容时刷新, 理论上 90s 应 break, 但 DB 实测有请求
        # 跑 190s status=200 (input/output_tokens=0, finish_reason=null) → 90s deadline 未生效
        # (疑空 chunk 触发了 768 行的刷新, 或 read 阻塞未进 690 检查点). cc4101 非-thinking 100s
        # stall-watcher 先 kill → emit api_error → CC 报 "Server error mid-response" (CC 不重试 mid-flight
        # api_error, 直接报错用户). 修复: 独立跟踪 last_real_content_time, 60s (< cc4101 100s) 无真内容
        # 就 break + 发 content_filter error chunk, 让 nv_gw 先于 cc4101 主动快速失败 (status 502 非 200).
        # thinking 流 gap 翻倍 (120s), 容纳长思考静默 (与 _idle_s 翻倍逻辑一致).
        _no_content_gap_s = NVU_STREAM_NO_CONTENT_GAP_S
        # R1418: gap 按 input 缩放 (同 R1416 first-byte 逻辑). 实测 374K 请求 NVCF 吐 101 字符后
        # 卡 60s+ (16:12:44 stream_no_content_gap), 60s 对超大 context 后续 prefill 太短.
        # 上限 90s (< cc4101 IDLE_GAP 100s, 让 nv_gw 先 break 发 err_chunk). 小请求仍 60s.
        if _ic > 350000:
            _no_content_gap_s = 90.0
        elif _ic > 200000:
            _no_content_gap_s = 80.0
        if metrics.get("thinking_type"):
            _no_content_gap_s = _no_content_gap_s * 2
        last_real_content_time = None  # TTFB 时初始化; 真内容到达刷新; 60s 无真内容硬断
        _gap_sample_logged = False  # gap 触发时只记一次 chunk 样本
        # R1408: 入口设短轮询 read timeout. getresponse 后 conn.sock 为 None (http.client
        # 把 sock 移到 resp.fp.raw._sock, 同 cc4101 R853 坑), 旧代码 conn.sock.settimeout 静默失败
        # -> resp.read(8192) 无 timeout 继承连接阶段 66s -> 但 NVCF 200-then-hang 静默期 read
        # 阻塞 66s+ 不返回 -> 循环顶 deadline 检查跑不到. 现用 resp.fp.raw._sock 设 POLL_S=15s,
        # read 每 <=15s 抛 socket.timeout -> 内层 except continue -> deadline 检查每 15s 跑一次.
        _poll_sock = None
        try:
            _poll_sock = conn.sock
            if _poll_sock is None and resp is not None:
                try:
                    _poll_sock = resp.fp.raw._sock
                except Exception:
                    _poll_sock = None
            if _poll_sock is not None:
                _poll_sock.settimeout(NVU_STREAM_POLL_S)
        except Exception as _e:
            _log("WARN", f"({request_model}) R1408 set poll socktimeout failed: {_e}")

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        try:
            while True:
                if stream_idle_deadline is not None and time.time() > stream_idle_deadline:
                    metrics["error_type"] = "stream_total_deadline"
                    _log("NV-STREAM-DEADLINE", f"({request_model}) passthrough idle deadline "
                        f"{_idle_s}s after last-real-content exceeded, breaking (SSE keep-alive stall)")
                    break
                # R1407: 真内容 idle gap 硬兜底. 独立于 stream_idle_deadline (后者可能被空 chunk
                # 误刷新), 此检查直接看 wall-clock 距上次真内容的时长. 60s < cc4101 100s, 让 nv_gw 先断.
                if last_real_content_time is not None and time.time() - last_real_content_time > _no_content_gap_s:
                    metrics["error_type"] = "stream_no_content_gap"
                    _gap = int(time.time() - last_real_content_time)
                    _sample = sse_buffer[-200:].replace("\n", "\\n") if sse_buffer else "(empty)"
                    _log("NV-NO-CONTENT-GAP", f"({request_model}) no real content for {_gap}s "
                        f"(gap_limit={_no_content_gap_s}s, content_chars={passthrough_content_chars}, "
                        f"reasoning_chars={passthrough_reasoning_chars}, ttfb_recorded={ttfb_recorded}, "
                        f"thinking={'Y' if metrics.get('thinking_type') else 'N'}) — breaking to emit "
                        f"error chunk before cc4101 100s stall. sse_buffer_tail={_sample}")
                    break
                if not ttfb_recorded and time.time() > stream_first_byte_deadline:
                    metrics["error_type"] = "stream_first_byte_timeout"
                    _log("NV-STREAM-FIRST-BYTE-DEADLINE", f"({request_model}) passthrough first-byte deadline "
                        f"{_fb_s}s exceeded (input_chars={_ic}), breaking (upstream 200-then-hang)")
                    break
                # R1411: R1408 poll fix 的内层 except (注释 716 行提到但代码丢失). settimeout(15)
                # 让 read 每 <=15s 抛 socket.timeout, 必须在此接住 continue, 否则 timeout 直冲外层
                # except(line 875) 被当 stream break error 处理 -> 循环顶 deadline 检查永远跑不到
                # -> 实际靠 66s 连接 timeout 兜底 (97s 才 break), first_byte 20s deadline 形同虚设.
                # socket.SocketIO.read() 超时后下次抛裸 OSError("cannot read from timed out object")
                # (非 socket.timeout 子类, 同 cc4101 R846 修3), 也要 continue.
                try:
                    chunk = resp.read(8192)
                except socket.timeout:
                    continue
                except OSError as _re:
                    if "timed out object" in str(_re) or "timeout" in str(_re).lower():
                        continue
                    raise
                if not chunk:
                    remaining = sse_buffer.strip()
                    if remaining and remaining.startswith("data:") and remaining[5:].strip() != "[DONE]":
                        data_str = remaining[5:].strip()
                        if data_str:
                            try:
                                data = json.loads(data_str)
                                fr = data.get("choices", [{}])[0].get("finish_reason")
                                if fr:
                                    metrics["finish_reason"] = fr
                                chunk_usage = data.get("usage", {})
                                if chunk_usage:
                                    pt = chunk_usage.get("prompt_tokens", 0)
                                    ct = chunk_usage.get("completion_tokens", 0)
                                    if pt > 0:
                                        streaming_input_tokens = pt
                                    if ct > 0:
                                        streaming_output_tokens = ct
                            except Exception:
                                pass
                    break

                if not ttfb_recorded:
                    metrics["ttfb_ms"] = int((time.time() - t_start) * 1000)
                    ttfb_recorded = True
                    stream_idle_deadline = time.time() + _idle_s
                    last_real_content_time = time.time()  # R1407: TTFB 时初始化, 60s 无真内容兜底

                sse_buffer += chunk.decode("utf-8", errors="replace")

                # R840: 先解析本 chunk 的 SSE 行 (累积 content / tool_calls / finish_reason), 用于
                # 在 write 给 openclaw 之前判断是否空僵尸. 见僵尸则跳过 write + abort.
                try:
                    while "\n" in sse_buffer:
                        line, sse_buffer = sse_buffer.split("\n", 1)
                        line = line.strip()
                        if not line or line.startswith(":"):
                            continue
                        if not line.startswith("data:"):
                            continue
                        data_str = line[5:].strip()
                        if data_str == "[DONE]" or not data_str:
                            continue
                        try:
                            data = json.loads(data_str)
                            chunk_usage = data.get("usage", {})
                            if chunk_usage:
                                pt = chunk_usage.get("prompt_tokens", 0)
                                ct = chunk_usage.get("completion_tokens", 0)
                                if pt > 0:
                                    streaming_input_tokens = pt
                                if ct > 0:
                                    streaming_output_tokens = ct
                            choices = data.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {}) or {}
                                # 累积 content + reasoning_content 字符 (用于空僵尸判定)
                                cont = delta.get("content")
                                if cont:
                                    passthrough_content_chars += len(cont)
                                # R844 F3: 累积 reasoning_content (glm5.2 思考全在 reasoning_content)
                                rcont = delta.get("reasoning_content")
                                if rcont:
                                    passthrough_reasoning_chars += len(rcont)
                                # R850: 收到真内容(content/reasoning_content/tool_calls)刷新 idle deadline.
                                # 旧洞: deadline ttfb 后固定不刷新, thinking 长静默误切. 现按真内容刷新.
                                if cont or rcont or (delta.get("tool_calls") or []):
                                    stream_idle_deadline = time.time() + _idle_s
                                    last_real_content_time = time.time()  # R1407: 真内容刷新, 与 idle_deadline 同步
                                # R844 F4b: saw_tool_calls 要求真 arguments 非空 (空壳 id+空args 不算真工具调用)
                                # dsv4p 大 context 空壳: finish_reason=tool_calls 但 arguments 空 → 仍判僵尸
                                for _tc in (delta.get("tool_calls") or []):
                                    _fn = _tc.get("function", {}) if isinstance(_tc, dict) else {}
                                    if _fn.get("arguments"):
                                        passthrough_saw_tool_calls = True
                                        break
                                fr = choices[0].get("finish_reason")
                                if fr:
                                    metrics["finish_reason"] = fr
                                    # R840: 僵尸空响应检测. finish_reason=stop 且 content < 阈值
                                    # 且无 tool_calls 且 total_input_chars > 下限(大context) → 假完成空响应.
                                    # 用 total_input_chars(请求开始时已知) 而非 streaming_input_tokens
                                    # (SSE usage 在 finish_reason 之后才到, 时序来不及). 不写本 chunk, abort.
                                    # R844 F4b: fr in (stop, tool_calls) — dsv4p 空壳 finish_reason=tool_calls 也要抓
                                    # F3: 累积 reasoning_content (glm5.2 思考在此, stop 时 content 空但 reasoning 有也算非空)
                                    # R852b: 只看 passthrough_content_chars (text answer), 不加 reasoning_chars.
                                    # GLM5.2 thinking 模式实测产出 3920c reasoning 但 0c content — 答案写进思考里,
                                    # CC 收到"只有 thinking 没 text"报 empty/filtered completion. 故 thinking 不算有效完成.
                                    if (fr in ("stop", "tool_calls")
                                            and not passthrough_saw_tool_calls
                                            and passthrough_content_chars < NVU_ZOMBIE_EMPTY_CONTENT_CHARS
                                            and metrics.get("total_input_chars", 0) >= NVU_ZOMBIE_MIN_INPUT_CHARS):
                                        zombie_detected = True
                                        metrics["error_type"] = "zombie_empty_completion"
                                        _log("NV-ZOMBIE-EMPTY", f"({request_model}) passthrough zombie empty "
                                            f"completion: finish_reason={fr} but content_chars="
                                            f"{passthrough_content_chars} reasoning_chars={passthrough_reasoning_chars} "
                                            f"< {NVU_ZOMBIE_EMPTY_CONTENT_CHARS} (content-only, R852b), input_chars={metrics.get('total_input_chars', 0)} "
                                            f">= {NVU_ZOMBIE_MIN_INPUT_CHARS}, no real tool_calls — aborting stream to trigger fallback")
                        except json.JSONDecodeError:
                            pass
                except Exception:
                    pass

                # R840: 僵尸检测命中 → 不写本 chunk (含 finish_reason 终末信号), 跳出循环 abort 连接
                if zombie_detected:
                    break

                # R1627: 全量缓冲模式下不立即 flush, 攒到流结束再一次性发 (防 mid-response 卡死).
                if buffer_chunks is not None:
                    buffer_chunks.append(chunk)
                else:
                    try:
                        self.wfile.write(chunk)
                        self.wfile.flush()
                    except Exception:
                        break

        except (http.client.RemoteDisconnected, ConnectionResetError,
                OSError, http.client.IncompleteRead, socket.timeout) as e:
            elapsed_ms = int((time.time() - t_start) * 1000)
            error_class = type(e).__name__
            _log("ERR", f"NV stream {error_class} after {elapsed_ms}ms: {e}")
            _log("NV-STREAMBREAK-STATE", f"({request_model}) stream break: {error_class} elapsed={elapsed_ms}ms content_flushed={passthrough_content_chars}c reasoning_flushed={passthrough_reasoning_chars}c ttfb_recorded={ttfb_recorded} saw_tool_calls={passthrough_saw_tool_calls} - " + ("RETRYABLE(content=0)" if passthrough_content_chars==0 else "FLUSHED(content>0,cannot retry)"))
            metrics["error_type"] = f"NVStream_{error_class}"
        except Exception as e:
            elapsed_ms = int((time.time() - t_start) * 1000)
            error_class = type(e).__name__
            _log("ERR", f"NV stream unexpected {error_class} after {elapsed_ms}ms: {e}")
            metrics["error_type"] = f"NVStream_{error_class}"

        if metrics.get("error_type"):
            metrics["status"] = 502
        else:
            metrics["status"] = 200
        metrics["duration_ms"] = int((time.time() - t_start) * 1000)
        if streaming_input_tokens > 0:
            metrics["input_tokens"] = streaming_input_tokens
        if streaming_output_tokens > 0:
            metrics["output_tokens"] = streaming_output_tokens
        _log_metrics(metrics)

        # R1627: 全量缓冲模式 — 正常结束 (无 error_type 且非 zombie) 时一次性 flush 全部缓冲给下游.
        # 此时 NVCF 流已正常结束 (收到 finish_reason/[DONE]), cc4101 收到完整响应, CC 不中断.
        # 卡死/错误路径 (error_type 非空或 zombie_detected) 不 flush 缓冲, 直接丢弃, 走下方 content_filter
        # 分支 (因从未 flush, 下游收到零内容 -> Scenario A -> CC 自动重试下个 key).
        _r1627_flushed_downstream = False
        if buffer_chunks is not None and not metrics.get("error_type") and not zombie_detected:
            try:
                full_payload = b"".join(buffer_chunks)
                self.wfile.write(full_payload)
                self.wfile.flush()
                _r1627_flushed_downstream = True
                _log("NV-STREAM-BUFFER-FLUSH", f"({request_model}) full-buffer flushed {len(full_payload)}b to downstream "
                    f"(content_chars={passthrough_content_chars}c reasoning={passthrough_reasoning_chars}c, dur={metrics.get('duration_ms')}ms)")
            except Exception as e:
                _log("ERR", f"NV-STREAM-BUFFER-FLUSH write failed: {e}")
                metrics["error_type"] = "buffer_flush_write_failed"
                metrics["status"] = 502
        buffer_chunks = None  # 释放内存

        # R840: zombie 空响应 → 主动写一个 finish_reason=content_filter 的 SSE chunk 给 openclaw, 让其
        # mapOpenAIStopReason 返回 stopReason="error" → openclaw throw → fallback 链生效.
        # 之前用 SO_LINGER RST 方案无效: HTTP/1.0 close 先发 FIN, openclaw 收到 200+空body 正常结束.
        # 改用 SSE error chunk 走 openclaw 正常解析路径, 让其主动判 error.
        # R846: 扩展至所有上游断流错误 (stream_total_deadline/stream_first_byte_timeout/NVStream_*).
        # 旧洞: 这些路径只 break+conn.close(), wire 上是干净 EOF, cc4101 收到空 200 → Claude Code
        # 看到空响应. 现统一写 content_filter error chunk, 复用 cc4101 stream.py 的 zombie 分支
        # (finish_reason==content_filter → _emit_graceful_end(zombie=True) → api_error → CC 重试).
        # metrics 仍记真实 error_type, wire 信号统一用 content_filter (零下游改动).
        # R1410: 仅在未向下游 flush 过任何真内容 (passthrough_content_chars==0) 时才注入 content_filter
        # error chunk. 路径A (200-then-hang, ttfb_recorded=False, content=0): 注入让 cc4101 走 zombie→
        # api_error→CC 重试, 有效. 路径B (content_flushed>0, 上游流到中途 SSL EOF / timeout): 此时下游
        # 已收到部分内容, 再注入 content_filter error chunk 会让 cc4101 在已输出中途塞 error → CC 看到的
        # 是"响应进行中被打断"= mid-response 弹窗. 且 HTTP 协议下已 flush 的字节收不回, 重试无意义.
        # 改: 路径B 不注入 error chunk, 仅 conn.close() 让下游收干净中途 EOF, cc4101 走 interrupted/
        # graceful_end 把已收到内容自然收尾 (发 end_turn), 比 mid-response 弹窗更可接受.
        # R1627: 缓冲模式下, 未向下游 flush (即 _r1627_flushed_downstream=False) 就走 content_filter
        # (Scenario A 零内容 -> CC 自动重试). 旧行为 (非缓冲) 按 passthrough_content_chars==0 判定.
        _r1627_should_emit_cf = (zombie_detected or metrics.get("error_type")) and (not _r1627_flushed_downstream) and (passthrough_content_chars == 0 or buffer_chunks is None)
        if _r1627_should_emit_cf:
            try:
                # R846 Fix6: 前置 \n\n 确保上游最后一个 event 的 SSE 终止符完整.
                # 旧洞: 上游 passthrough chunk 的 \n\n 可能残留在 sse_buffer 未 flush, 或被 8192 read
                # 边界切断, 致 cc4101 buffer 里上一个 event (如 reasoning_content chunk) 无 \n\n
                # 终止, 与本 content_filter chunk 拼成 "}],data: {...content_filter...}" 单个 event,
                # cc4101 json.loads 失败 → malformed → content_filter 信号被吞 → cc4101 返回空 200.
                # 前置 \n\n 让两 event 必定分离, cc4101 split("\n\n") 能正确切出 content_filter.
                err_chunk = ('\n\ndata: {"choices":[{"index":0,"delta":{},"finish_reason":"content_filter"}]}\n\n'
                             'data: [DONE]\n\n').encode("utf-8")
                self.wfile.write(err_chunk)
                self.wfile.flush()
                _log("NV-UPSTREAM-ERROR-CHUNK", f"({request_model}) sent finish_reason=content_filter error "
                    f"SSE chunk (zombie={zombie_detected} error_type={metrics.get('error_type')}) to downstream, "
                    f"triggers cc4101 zombie→api_error→CC retry")
            except Exception as e:
                _log("ERR", f"NV-UPSTREAM-ERROR-CHUNK write failed: {e}")
        else:
            # R1413: 路径B (content_flushed>0, 不发 content_filter). 上面 if 块未命中说明已有真内容
            # flush 给下游. 旧洞(R1410): 路径B 只 conn.close() 关上游, 但下游 self.wfile 未发任何终止
            # 信号 ([DONE]/finish_reason), HTTP 响应体未正常结束 → cc4101 resp.read() 一直阻塞等���多数据
            # → 收不到 EOF → 直到 stall-watcher 100s 兜底 kill → StreamStallWatcher → CC mid-response.
            # (21:19:02 nv_gw break 但 cc4101 21:19:42 才 stall, 差40s 实锤: 下游连接悬空).
            # 修复: 路径B 主动写 [DONE]+flush 关下游, 让 cc4101 读到 [DONE] 走 _emit_graceful_end()
            # 把已输出内容当完整响应收尾 (发 end_turn), 不再 stall-kill → 不再 mid-response.
            # 注意: 若上游断流是 zombie/error 但已有内容, 发 [DONE] 让下游正常收尾优于发 content_filter
            # (后者会在已输出中途塞 error→mid-response). content_flushed==0 的路径A 仍由上面 if 发
            # content_filter 走 zombie→重试.
            # R1627: 缓冲模式下, 卡死已由上面 content_filter 分支处理 (Scenario A), 此处不再发 [DONE].
            # 仅旧行为 (非缓冲, 边读边 flush 了部分内容) 走此 Scenario B [DONE] 收尾分支.
            if (zombie_detected or metrics.get("error_type")) and passthrough_content_chars > 0 and not (buffer_chunks is None and NVU_STREAM_FULL_BUFFER):
                try:
                    done_chunk = b'data: [DONE]\n\n'
                    self.wfile.write(done_chunk)
                    self.wfile.flush()
                    _log("NV-STREAM-DONE-FLUSH", f"({request_model}) sent [DONE] to close downstream after "
                        f"mid-stream break (content_flushed={passthrough_content_chars}c, error_type="
                        f"{metrics.get('error_type')}) — closing downstream conn to force cc4101 EOF")
                    # R1414: 仅 flush [DONE] 不够 (cc4101 22:00:22 后收不到 22:01:22 写的 [DONE],
                    # 推测 self.wfile BufferedWriter + BaseHTTPRequestHandler 延迟关连接所致).
                    # 主动 self.connection.close() 强制 TCP 发 FIN, cc4101 resp.read() 立即返回 [DONE]+EOF.
                    try:
                        self.connection.close()
                    except Exception as _ce:
                        _log("ERR", f"NV-STREAM-DONE-FLUSH conn.close failed: {_ce}")
                except Exception as e:
                    _log("ERR", f"NV-STREAM-DONE-FLUSH write failed: {e}")
        try:
            conn.close()
        except Exception:
            pass


    # ─── /v1/models ───
    def _proxy_models(self):
        """Return OpenAI-format model list for Hermes (single canonical model)."""
        if not self._check_auth():
            return
        all_models = []
        for model_key in NV_MODEL_TIERS:
            context_len = MODEL_INPUT_TOKEN_SAFETY.get(model_key, DEFAULT_CONTEXT_FALLBACK)
            all_models.append({
                "id": model_key,
                "object": "model",
                "created": 0,
                "owned_by": "nvidia_hermes",
                "context_length": context_len,
            })
        self._send_json(200, {"object": "list", "data": all_models})

    # ─── Helpers ───
    def _check_auth(self):
        """Gate /v1/* endpoints on Authorization: Bearer <NVU_GATEWAY_API_KEY>
        or x-api-key: <NVU_GATEWAY_API_KEY>. /health & CORS preflight are exempt
        (handled by callers never invoking this). Empty key => no auth (back-compat).
        """
        expected = NVU_GATEWAY_API_KEY
        if not expected:
            return True
        auth = self.headers.get("Authorization") or self.headers.get("x-api-key") or ""
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
        else:
            token = auth.strip()
        if token != expected:
            self._send_json(401, {"error": {"message": "invalid api key",
                                            "type": "invalid_request_error", "code": "401"}})
            return False
        return True

    def _peer_fallback(self, body, mapped_model, is_stream, metrics):
        """Forward request to peer nv_gw (same model) when local all_tiers_exhausted.

        Returns True if we successfully relayed a response to the client (stream or
        non-stream), False if peer also failed (caller returns local 502).
        Loop prevention: sets X-Fallback-Hop: 1; peer sees hop≥1 and won't re-forward.
        Auth: sends Authorization: Bearer <NVU_GATEWAY_API_KEY> so peer's _check_auth passes.
        Safety (cc2): only called at all_tiers_exhausted, never on single-key SSL error.
        """
        if not NVU_PEER_FALLBACK_URL:
            return False
        # body 入参是已解析的 dict (handlers.py L134 json.loads(raw)), 重新序列化为
        # JSON bytes 给 http.client (传 dict 会触发 "can't concat str to bytes").
        if isinstance(body, (dict, list)):
            body_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")
        elif isinstance(body, str):
            body_bytes = body.encode("utf-8")
        elif isinstance(body, (bytes, bytearray)):
            body_bytes = bytes(body)
        else:
            _log("NV-PEER-FB", f"body type {type(body).__name__} not serializable, abort")
            return False
        t_fb_start = time.time()
        # parse peer URL → http.client connection
        try:
            from urllib.parse import urlparse
            p = urlparse(NVU_PEER_FALLBACK_URL)
            host = p.hostname
            port = p.port or 40006
            peer_path = p.path.rstrip("/") + "/v1/chat/completions"
        except Exception as e:
            _log("NV-PEER-FB", f"bad NVU_PEER_FALLBACK_URL={NVU_PEER_FALLBACK_URL}: {e}")
            return False

        # copy inbound headers, override hop + auth + host
        fwd_headers = {}
        ct = self.headers.get("Content-Type", "application/json")
        fwd_headers["Content-Type"] = ct
        fwd_headers["X-Fallback-Hop"] = "1"
        fwd_headers["X-Fallback-Origin"] = PROXY_ROLE or "unknown"
        if NVU_GATEWAY_API_KEY:
            fwd_headers["Authorization"] = f"Bearer {NVU_GATEWAY_API_KEY}"
        # caller-supplied headers we want to preserve (e.g. X-Caller)
        for h in ("X-Caller", "X-Request-Id"):
            v = self.headers.get(h)
            if v:
                fwd_headers[h] = v
        fwd_headers["Content-Length"] = str(len(body_bytes))

        peer_conn = None
        try:
            peer_conn = http.client.HTTPConnection(host, port,
                                                  timeout=NVU_PEER_FALLBACK_TIMEOUT)
            peer_conn.request("POST", peer_path, body=body_bytes, headers=fwd_headers)
            resp = peer_conn.getresponse()
        except Exception as e:
            elapsed_ms = int((time.time() - t_fb_start) * 1000)
            _log("NV-PEER-FB", f"peer connect/request failed after {elapsed_ms}ms: "
                               f"{type(e).__name__}: {e}")
            if peer_conn:
                try: peer_conn.close()
                except Exception: pass
            metrics["peer_fallback_error"] = f"connect_{type(e).__name__}"
            metrics["peer_fallback_ms"] = elapsed_ms
            return False

        # peer returned an error status (e.g. 502/429) → don't relay, let caller 502
        if resp.status >= 500 or resp.status == 429:
            elapsed_ms = int((time.time() - t_fb_start) * 1000)
            # drain so connection can be reused/closed cleanly
            try: resp.read()
            except Exception: pass
            try: peer_conn.close()
            except Exception: pass
            _log("NV-PEER-FB", f"peer returned {resp.status} after {elapsed_ms}ms, "
                               f"not relaying, returning local 502")
            metrics["peer_fallback_error"] = f"peer_http_{resp.status}"
            metrics["peer_fallback_ms"] = elapsed_ms
            return False

        # success path — relay response to client
        metrics["peer_fallback_ms"] = int((time.time() - t_fb_start) * 1000)
        metrics["peer_fallback_status"] = resp.status
        ttfb_start = time.time()
        try:
            # send status + headers
            self.send_response(resp.status)
            relay_ct = resp.getheader("Content-Type") or ct
            self.send_header("Content-Type", relay_ct)
            # stream or chunked: prefer Connection close, no Content-Length
            self.send_header("Connection", "close")
            # propagate hop info so downstream knows this was a fallback
            self.send_header("X-Fallback-Served-By", PROXY_ROLE or "unknown")
            self.end_headers()

            # relay body in chunks (works for both SSE stream and buffered JSON)
            total = 0
            while True:
                # R1411: R1408 poll fix 的内层 except (注释 716 行提到但代码丢失). settimeout(15)
                # 让 read 每 <=15s 抛 socket.timeout, 必须在此接住 continue, 否则 timeout 直冲外层
                # except(line 875) 被当 stream break error 处理 -> 循环顶 deadline 检查永远跑不到
                # -> 实际靠 66s 连接 timeout 兜底 (97s 才 break), first_byte 20s deadline 形同虚设.
                # socket.SocketIO.read() 超时后下次抛裸 OSError("cannot read from timed out object")
                # (非 socket.timeout 子类, 同 cc4101 R846 修3), 也要 continue.
                try:
                    chunk = resp.read(8192)
                except socket.timeout:
                    continue
                except OSError as _re:
                    if "timed out object" in str(_re) or "timeout" in str(_re).lower():
                        continue
                    raise
                if not chunk:
                    break
                if not metrics.get("ttfb_ms"):
                    metrics["ttfb_ms"] = int((time.time() - ttfb_start) * 1000)
                self.wfile.write(chunk)
                total += len(chunk)
            metrics["peer_fallback_bytes"] = total
            metrics["status"] = resp.status
            metrics["duration_ms"] = int((time.time() - t_fb_start) * 1000)
            _log("NV-PEER-FB", f"peer fallback OK: status={resp.status} "
                               f"bytes={total} ttfb={metrics.get('ttfb_ms')}ms")
            return True
        except Exception as e:
            elapsed_ms = int((time.time() - t_fb_start) * 1000)
            _log("NV-PEER-FB", f"peer relay failed after {elapsed_ms}ms: "
                               f"{type(e).__name__}: {e}")
            metrics["peer_fallback_error"] = f"relay_{type(e).__name__}"
            metrics["peer_fallback_ms"] = elapsed_ms
            return False
        finally:
            try: peer_conn.close()
            except Exception: pass

    def _send_json(self, code, data, extra_headers=None):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self._send_raw(code, body, "application/json", extra_headers)

    def _send_raw(self, code, body_bytes, content_type="application/json", extra_headers=None):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body_bytes)))
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, str(v))
        self.end_headers()
        self.wfile.write(body_bytes)

    def log_message(self, fmt, *args):
        pass  # Suppress default logging
