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
    NVU_STREAM_TOTAL_DEADLINE_S,
    NVU_STREAM_FIRST_BYTE_DEADLINE_S,
    NVU_ZOMBIE_EMPTY_CONTENT_CHARS,
    NVU_ZOMBIE_MIN_INPUT_CHARS,
    NVU_PEER_FALLBACK_ENABLED,
    NVU_PEER_FALLBACK_URL,
    NVU_PEER_FALLBACK_TIMEOUT,
    NVU_MS_GW_FALLBACK_ENABLED,
    NVU_MS_GW_FALLBACK_URL,
    NVU_MS_GW_FALLBACK_TOKEN,
    NVU_MS_GW_FALLBACK_TIMEOUT,
    NVU_MS_GW_FALLBACK_MODELMAP,
    NVU_KEYS, NV_INTEGRATE_HOST,
    is_key_cooling, mark_key_cooling, reset_key429_count,
)
from .logger import _log, _log_metrics, _log_error_detail
from .upstream import execute_request, UpstreamResult
from .error_mapping import format_nv_all_keys_exhausted, format_nv_error_upstream


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
        if parsed.path in ("/health", "/", "/v1/models", "/models", "/v1/chat/completions", "/chat/completions", "/v1/embeddings", "/embeddings"):
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

        _log("REQ", f"model={request_model}→{mapped_model}→tier_idx={metrics['start_tier_idx']} "
                    f"stream={is_stream} msgs={len(body.get('messages',[]))} agent=_nv caller={metrics['caller']} "
                    f"effort={metrics['reasoning_effort']} thinking={metrics['thinking_type']}")

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
                # R832: 同模型 fallback 到 ms_gw (优先于 peer-fb). 禁止跨模型 fallback.
                # mapped_model 在 NVU_MS_GW_FALLBACK_MODELMAP 里 → 转发到 ms_gw:40007 同模型.
                if (NVU_MS_GW_FALLBACK_ENABLED and NVU_MS_GW_FALLBACK_URL
                        and hop_n < 1 and not is_429
                        and mapped_model in NVU_MS_GW_FALLBACK_MODELMAP):
                    _ms_model = NVU_MS_GW_FALLBACK_MODELMAP[mapped_model]
                    _log("NV-MS-FB", f"local all_tiers_exhausted (model={mapped_model}), "
                                     f"attempting same-model fallback to {NVU_MS_GW_FALLBACK_URL} "
                                     f"as {_ms_model}")
                    ok = self._ms_gw_fallback(body, mapped_model, _ms_model, is_stream, metrics)
                    if ok:
                        metrics["ms_gw_fallback_used"] = True
                        metrics["fallback_from"] = mapped_model
                        metrics["fallback_to"] = _ms_model
                        metrics["fallback_occurred"] = True
                        _log_metrics(metrics)
                        return
                    _log("NV-MS-FB", f"ms_gw same-model fallback FAILED for model={mapped_model}, "
                                     f"(relay_started={metrics.get('ms_gw_relay_started', False)})")
                    # R832: 若 ms_gw relay 已开始 (200+headers 已发给客户端), 中途超时/断流,
                    # 不能再 _send_json(502) — 502 文本会拼进已发的流式响应致客户端 JSON 解析失败.
                    # 直接 _log_metrics + return (连接已半残, 客户端会收到截断的流).
                    if metrics.get("ms_gw_relay_started"):
                        _log_metrics(metrics)
                        return
                elif (NVU_PEER_FALLBACK_ENABLED and NVU_PEER_FALLBACK_URL
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
        # R832e: record upstream_type/function_id for integrate vs pexec channel tracking
        metrics["function_id"] = result.function_id
        # R832f: NVCF per-request trace id 落库 (与 NVCF 抓包/客服对账用)
        metrics["nvcf_reqid"] = getattr(result, "nvcf_reqid", "") or ""
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
        # R835: 流式 idle deadline (首字节后). conn.sock.settimeout 是 per-read, SSE keep-alive chunk
        # 绕过 → 流永不中断 → openclaw 等到 lane 120s 杀 (R834 审计 P0: 流持续 102s). 此 deadline
        # 从首字节(ttfb)之后算, 不从 t_start 算 — 避免砍 glm5.2 thinking 慢 ttfb(实测 max 71s, 由
        # NVU_INTEGRATE_THINKING_TIMEOUT_S per-attempt 管). 只兜"流已开始但持续不结束"的僵尸流.
        stream_idle_deadline = None  # 设为首字节时刻 + NVU_STREAM_TOTAL_DEADLINE_S
        # R839: 首字节前绝对 deadline. 兜 "upstream 返回 200 头但 body 首字节永不来" (idle deadline 盲区).
        # 从 t_start(进循环前)算, 不等首字节. 超过就 break + 记 stream_first_byte_timeout.
        stream_first_byte_deadline = time.time() + NVU_STREAM_FIRST_BYTE_DEADLINE_S

        try:
            while True:
                if stream_idle_deadline is not None and time.time() > stream_idle_deadline:
                    metrics["error_type"] = "stream_total_deadline"
                    _log("NV-STREAM-DEADLINE", f"({request_model}) accumulate-stream idle deadline "
                        f"{NVU_STREAM_TOTAL_DEADLINE_S}s after ttfb exceeded, breaking (SSE keep-alive stall)")
                    break
                if not ttfb_recorded and time.time() > stream_first_byte_deadline:
                    metrics["error_type"] = "stream_first_byte_timeout"
                    _log("NV-STREAM-FIRST-BYTE-DEADLINE", f"({request_model}) accumulate-stream first-byte deadline "
                        f"{NVU_STREAM_FIRST_BYTE_DEADLINE_S}s exceeded, breaking (upstream 200-then-hang)")
                    break
                chunk = resp.read(8192)
                if not chunk:
                    break

                if not ttfb_recorded:
                    metrics["ttfb_ms"] = int((time.time() - t_start) * 1000)
                    ttfb_recorded = True
                    stream_idle_deadline = time.time() + NVU_STREAM_TOTAL_DEADLINE_S

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
        # R835: 不再用 duration_ms 兜底 ttfb (旧逻辑掩盖流式超时无首字节真相, 11575=11575 铁证).
        # 没收到首字节就留 0, 让 stall-watcher/DB 能识别. stream_total_deadline 已记 error_type.
        if not metrics.get("ttfb_ms"):
            metrics["ttfb_ms"] = 0
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

    def _stream_openai_passthrough(self, resp, conn, metrics, t_start, request_model):
        """Pass through OpenAI streaming SSE response directly to Hermes."""
        ttfb_recorded = False
        streaming_input_tokens = 0
        streaming_output_tokens = 0
        sse_buffer = ""
        # R840: 累积 content 字符数 + 是否见 tool_calls, 用于僵尸空响应检测.
        passthrough_content_chars = 0
        passthrough_saw_tool_calls = False
        # R840: 僵尸空响应标记. 见 finish_reason=stop 且 content_chars<阈值 且无 tool_calls 且
        # 有 input → 判定空僵尸, 不写终末 chunk, abort 连接让 openclaw 走 fallback.
        zombie_detected = False
        # R835: 流式 idle deadline (首字节后). conn.sock.settimeout 是 per-read, SSE upstream 持续发
        # keep-alive chunk 绕过 per-read 超时 → 流永不中断 → openclaw 等流结束等到 100s abort (R834 P0
        # 铁证: 流持续 102s). 此 deadline 从首字节(ttfb)之后算, 不从 t_start 算 — 避免砍 glm5.2 thinking
        # 慢 ttfb(实测 max 71s, 由 NVU_INTEGRATE_THINKING_TIMEOUT_S per-attempt 管). 只兜"流已开始但持续
        # 不结束"的僵尸流. 超过就 break + 记 stream_total_deadline, 截断喂饭式卡死.
        stream_idle_deadline = None  # 设为首字节时刻 + NVU_STREAM_TOTAL_DEADLINE_S
        # R839: 首字节前绝对 deadline. 兜 "upstream 返回 200 头但 body 首字节永不来" (idle deadline 盲区).
        # 从 t_start(进循环前)算, 不等首字节. 超过就 break + 记 stream_first_byte_timeout.
        stream_first_byte_deadline = time.time() + NVU_STREAM_FIRST_BYTE_DEADLINE_S

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        try:
            while True:
                if stream_idle_deadline is not None and time.time() > stream_idle_deadline:
                    metrics["error_type"] = "stream_total_deadline"
                    _log("NV-STREAM-DEADLINE", f"({request_model}) passthrough idle deadline "
                        f"{NVU_STREAM_TOTAL_DEADLINE_S}s after ttfb exceeded, breaking (SSE keep-alive stall)")
                    break
                if not ttfb_recorded and time.time() > stream_first_byte_deadline:
                    metrics["error_type"] = "stream_first_byte_timeout"
                    _log("NV-STREAM-FIRST-BYTE-DEADLINE", f"({request_model}) passthrough first-byte deadline "
                        f"{NVU_STREAM_FIRST_BYTE_DEADLINE_S}s exceeded, breaking (upstream 200-then-hang)")
                    break
                chunk = resp.read(8192)
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
                    stream_idle_deadline = time.time() + NVU_STREAM_TOTAL_DEADLINE_S

                sse_buffer += chunk.decode("utf-8", errors="replace")

                # R840: 先解析本 chunk 的 SSE 行 (累积 content / tool_calls / finish_reason), 用于
                # 在 write 给 openclaw 之前判断是否空僵尸. 见僵尸则跳过 write + abort, 不让 openclaw
                # 收到正常流结束信号 (chunk.done), 强制 reader.read() 抛错 → fallback.
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
                                # 累积 content 字符 (用于空僵尸判定)
                                cont = delta.get("content")
                                if cont:
                                    passthrough_content_chars += len(cont)
                                # 标记见 tool_calls (工具调用响应绝不判僵尸, 即使 content 空)
                                if delta.get("tool_calls"):
                                    passthrough_saw_tool_calls = True
                                fr = choices[0].get("finish_reason")
                                if fr:
                                    metrics["finish_reason"] = fr
                                    # R840: 僵尸空响应检测. finish_reason=stop 且 content < 阈值
                                    # 且无 tool_calls 且 total_input_chars > 下限(大context) → 假完成空响应.
                                    # 用 total_input_chars(请求开始时已知) 而非 streaming_input_tokens
                                    # (SSE usage 在 finish_reason 之后才到, 时序来不及). 不写本 chunk, abort.
                                    if (fr == "stop"
                                            and not passthrough_saw_tool_calls
                                            and passthrough_content_chars < NVU_ZOMBIE_EMPTY_CONTENT_CHARS
                                            and metrics.get("total_input_chars", 0) >= NVU_ZOMBIE_MIN_INPUT_CHARS):
                                        zombie_detected = True
                                        metrics["error_type"] = "zombie_empty_completion"
                                        _log("NV-ZOMBIE-EMPTY", f"({request_model}) passthrough zombie empty "
                                            f"completion: finish_reason=stop but content_chars="
                                            f"{passthrough_content_chars} < {NVU_ZOMBIE_EMPTY_CONTENT_CHARS}, "
                                            f"input_chars={metrics.get('total_input_chars', 0)} >= {NVU_ZOMBIE_MIN_INPUT_CHARS}, "
                                            f"no tool_calls — aborting stream to trigger openclaw fallback (avoid 8min stall)")
                        except json.JSONDecodeError:
                            pass
                except Exception:
                    pass

                # R840: 僵尸检测命中 → 不写本 chunk (含 finish_reason 终末信号), 跳出循环 abort 连接
                if zombie_detected:
                    break

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

        # R1397: zombie 空响应 → 主动写一个 finish_reason=timeout 的 SSE error chunk 给 openclaw.
        # 根因深挖: R840 用 finish_reason=content_filter, openclaw mapOpenAIStopReason 返回
        # stopReason="error" + errorMessage="Provider finish_reason: content_filter", 但该消息不匹配
        # openclaw classifyFailoverClassificationFromMessage 任何 pattern (无 HTTP status / 无
        # rate_limit/timeout/server_error 关键词) → failoverReason=null → isFailoverAssistantError=false
        # → failoverFailure=false → shouldRotateAssistant=false → resolveRunFailoverDecision 返回
        # "continue_normal" (不 fallback), run 以 isError=true 结束 → 用户见 "Server error mid-response".
        # 修复: 改用 finish_reason=timeout → errorMessage="Provider finish_reason: timeout" 命中
        # ERROR_PATTERNS.timeout ("timeout" 子串) → failoverReason="timeout" → isFailoverAssistantError=true
        # → failoverFailure=true → shouldRotateAssistant=true (harnessOwnsTransport=false for openclaw
        # embedded harness, 故 timeout 的 harnessOwnsTransport 特例不阻断) → action="fallback_model"
        # → throw FailoverError(reason=timeout) → 外层 model fallback 链生效 (ms_gw/glm5_2_ms 等).
        # 之前 SO_LINGER RST 方案无效: BaseHTTPServer HTTP/1.0 close 先发 FIN, openclaw 收 200+空body
        # 正常结束不抛错. SSE error chunk 走 openclaw 正常解析路径, 让其主动判 error+fallback.
        if zombie_detected:
            try:
                err_chunk = ('data: {"choices":[{"index":0,"delta":{},"finish_reason":"timeout"}]}\n\n'
                             'data: [DONE]\n\n').encode("utf-8")
                self.wfile.write(err_chunk)
                self.wfile.flush()
                _log("NV-ZOMBIE-ERROR-CHUNK", f"({request_model}) sent finish_reason=timeout error "
                    f"SSE chunk to openclaw, should trigger model fallback (failoverReason=timeout)")
            except Exception as e:
                _log("ERR", f"NV-ZOMBIE-ERROR-CHUNK write failed: {e}")
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
        fwd_headers["Connection"] = "close"
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
                chunk = resp.read(8192)
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

    def _ms_gw_fallback(self, body, nv_model, ms_model, is_stream, metrics):
        """R832: Forward request to ms_gw:40007 SAME-MODEL backend when local
        all_tiers_exhausted. Replaces cross-model FALLBACK_GRAPH (glm5_2_nv→dsv4p_nv).
        Reuses _peer_fallback relay framework, but:
          - URL = NVU_MS_GW_FALLBACK_URL (ms_gw:40007, not peer nv_gw)
          - body model rewritten: nv_model → ms_model (e.g. glm5_2_nv → glm5_2_ms)
          - auth = NVU_MS_GW_FALLBACK_TOKEN (ms_gw token, not nv-gw-token)
        Returns True if relayed OK, False if ms_gw also failed.
        """
        if not NVU_MS_GW_FALLBACK_URL:
            return False
        # 复制 body 并改写 model 名 (nv → ms 同模型)
        if isinstance(body, (dict, list)):
            import copy
            fb_body = copy.deepcopy(body)
            if isinstance(fb_body, dict):
                fb_body["model"] = ms_model
            body_bytes = json.dumps(fb_body, ensure_ascii=False).encode("utf-8")
        elif isinstance(body, str):
            try:
                _j = json.loads(body)
                _j["model"] = ms_model
                body_bytes = json.dumps(_j, ensure_ascii=False).encode("utf-8")
            except Exception:
                body_bytes = body.encode("utf-8")
        elif isinstance(body, (bytes, bytearray)):
            body_bytes = bytes(body)
        else:
            _log("NV-MS-FB", f"body type {type(body).__name__} not serializable, abort")
            return False
        t_fb_start = time.time()
        try:
            from urllib.parse import urlparse
            p = urlparse(NVU_MS_GW_FALLBACK_URL)
            host = p.hostname
            port = p.port or 40007
            ms_path = p.path.rstrip("/") + "/v1/chat/completions"
        except Exception as e:
            _log("NV-MS-FB", f"bad NVU_MS_GW_FALLBACK_URL={NVU_MS_GW_FALLBACK_URL}: {e}")
            return False
        fwd_headers = {}
        ct = self.headers.get("Content-Type", "application/json")
        fwd_headers["Content-Type"] = ct
        fwd_headers["X-Fallback-Hop"] = "1"
        fwd_headers["X-Fallback-Origin"] = PROXY_ROLE or "unknown"
        if NVU_MS_GW_FALLBACK_TOKEN:
            fwd_headers["Authorization"] = f"Bearer {NVU_MS_GW_FALLBACK_TOKEN}"
        for h in ("X-Caller", "X-Request-Id"):
            v = self.headers.get(h)
            if v: fwd_headers[h] = v
        fwd_headers["Connection"] = "close"
        fwd_headers["Content-Length"] = str(len(body_bytes))
        ms_conn = None
        try:
            ms_conn = http.client.HTTPConnection(host, port,
                                                  timeout=NVU_MS_GW_FALLBACK_TIMEOUT)
            ms_conn.request("POST", ms_path, body=body_bytes, headers=fwd_headers)
            resp = ms_conn.getresponse()
        except Exception as e:
            elapsed_ms = int((time.time() - t_fb_start) * 1000)
            _log("NV-MS-FB", f"ms_gw connect/request failed after {elapsed_ms}ms: "
                               f"{type(e).__name__}: {e}")
            if ms_conn:
                try: ms_conn.close()
                except Exception: pass
            metrics["ms_gw_fallback_error"] = f"connect_{type(e).__name__}"
            metrics["ms_gw_fallback_ms"] = elapsed_ms
            return False
        if resp.status >= 500 or resp.status == 429:
            elapsed_ms = int((time.time() - t_fb_start) * 1000)
            try: resp.read()
            except Exception: pass
            try: ms_conn.close()
            except Exception: pass
            _log("NV-MS-FB", f"ms_gw returned {resp.status} after {elapsed_ms}ms, "
                               f"not relaying, returning local 502")
            metrics["ms_gw_fallback_error"] = f"ms_http_{resp.status}"
            metrics["ms_gw_fallback_ms"] = elapsed_ms
            return False
        # success path — relay
        metrics["ms_gw_fallback_ms"] = int((time.time() - t_fb_start) * 1000)
        metrics["ms_gw_fallback_status"] = resp.status
        ttfb_start = time.time()
        relay_started = False  # R832: 一旦 send_response(200)+headers 发出, 中途异常不能再 _send_json(502) 否则 502 文本拼进已发的流式响应
        try:
            self.send_response(resp.status)
            relay_ct = resp.getheader("Content-Type") or ct
            self.send_header("Content-Type", relay_ct)
            self.send_header("Connection", "close")
            self.send_header("X-Fallback-Served-By", "ms_gw")
            self.end_headers()
            relay_started = True  # headers 已发, 此后出错只能断连, 不能再 _send_json
            total = 0
            while True:
                chunk = resp.read(8192)
                if not chunk: break
                if not metrics.get("ttfb_ms"):
                    metrics["ttfb_ms"] = int((time.time() - ttfb_start) * 1000)
                self.wfile.write(chunk)
                total += len(chunk)
            metrics["ms_gw_fallback_bytes"] = total
            metrics["status"] = resp.status
            metrics["duration_ms"] = int((time.time() - t_fb_start) * 1000)
            _log("NV-MS-FB", f"ms_gw fallback OK: status={resp.status} "
                               f"bytes={total} ttfb={metrics.get('ttfb_ms')}ms")
            return True
        except Exception as e:
            elapsed_ms = int((time.time() - t_fb_start) * 1000)
            _log("NV-MS-FB", f"ms_gw relay failed after {elapsed_ms}ms: "
                               f"{type(e).__name__}: {e} (relay_started={relay_started})")
            metrics["ms_gw_fallback_error"] = f"relay_{type(e).__name__}"
            metrics["ms_gw_fallback_ms"] = elapsed_ms
            # 关键: 如果已经开始 relay (headers 已发), 不能返回 False 让外层 _send_json(502),
            # 否则 502 错误文本会被拼进已发的 200 流式响应 → 客户端 JSON 解析失败 (openclaw 飞书卡死).
            # relay_started=True 时, 连接已半残, 只能标记让外层直接 return (不再 _send_json).
            metrics["ms_gw_relay_started"] = relay_started
            return False
        finally:
            try: ms_conn.close()
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
