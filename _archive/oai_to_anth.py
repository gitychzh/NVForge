#!/usr/bin/env python3
"""OpenAI → Anthropic response/SSE conversion (R1648b).

Reverse direction of `anth_to_oai.py`. Used by nv_gw `/v1/messages` endpoint:
nv_gw feeds NVCF OpenAI-SSE chunks in, emits Anthropic-SSE events out, so that
cc4101 (pure passthrough after R1648e) / Claude Code see a native Anthropic stream.

Design (why a stateful class, not a ported cc4101 `stream_to_anth`):
  cc4101's `stream_to_anth` (~600 lines) braids three concerns together:
    (1) OpenAI-chunk → Anthropic-SSE event mapping (pure conversion),
    (2) a stall-watcher + idle-deadline + timed-out-object recv-fallback loop, and
    (3) cc4101 circuit-breaker bookkeeping (record_primary_failure/success).
  nv_gw already owns (2) — its `_stream_openai_passthrough` read loop has the
  R850/R1407/R1627 idle-deadline + no-content-gap + full-buffer fixes that are
  *newer* than cc4101's. And (3) belongs to nv_gw's own breaker (R1648c), not
  to the converter. So we extract ONLY (1) here as a self-contained converter
  the read loop can call per-chunk. This avoids re-implementing (and drifting
  from) nv_gw's stream infra, and avoids dragging cc4101's stall-watcher
  duplication into nv_gw.

The caller (nv_gw handlers) owns: the read loop, the NVCF deadlines, the
zombie/empty detection, conn lifecycle, and writing bytes to the client socket.
This module only turns parsed OpenAI chunk dicts into Anthropic SSE byte strings.

Constants (self-contained, no config dependency — mirrors the R1648a rule that
made `anth_to_oai.py` copy-safe across gateways):
  THINKING_SIGNATURE — placeholder signature for thinking blocks. cc4101 uses
    a fixed placeholder and Claude Code accepts it; we reuse the same value so
    behavior is identical. Overridable via env like the rest.
"""
import json
import os
import sys
import uuid

THINKING_SIGNATURE = os.environ.get(
    "THINKING_SIGNATURE",
    "ErUB3WY0k2GCM2h+4O0S3Y3W3Y3f3Y3f3Y3f3Y3f3Y3f3Y3f3Y3f3Y3f3Y3f3Y3f3Y3f",
)


def _sse_bytes(event_type, data_dict):
    """Serialize one Anthropic SSE event to bytes (event: + data: + blank line)."""
    payload = json.dumps(data_dict, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event_type}\ndata: {payload}\n\n".encode("utf-8")


class OaiSseToAnthropicConverter:
    """Stateful OpenAI-SSE → Anthropic-SSE converter.

    Lifecycle (nv_gw handlers calls these in order):
      c = OaiSseToAnthropicConverter(request_model)
      for each parsed openai chunk dict:
          out += c.feed_chunk(chunk_data)
      out += c.finish(stop_reason=None, interrupted=False, zombie=False)
    """

    def __init__(self, request_model, request_id=None):
        self.request_model = request_model
        # R1826: rid for [NV-TOOLCALL-JSON-BAD] observation log (passed by handlers);
        # lets us correlate malformed tool_call arguments back to nv_requests row.
        # None-safe: older call sites that don't pass it still work.
        self.request_id = request_id
        self.message_start_sent = False
        self.message_delta_sent = False
        self.next_block_idx = 0
        self.active_block_type = None  # "thinking" | "text" | "tool_use"
        # token accumulators (from SSE usage chunks)
        self.input_tokens = 0
        self.output_tokens = 0
        # R2223 t1: NVCF 上游真实返回 prompt_tokens_details.cached_tokens (实测命中,
        # 如 40834 prompt 里 384 cached). oai_to_anth 此前只读 prompt_tokens/completion_tokens,
        # cache_creation/read_input_tokens 全程硬编码 0 报给 cc4101 → cc2 jsonl usage 缓存
        # 命中全 0 (R2192 抓包铁证). 透传真实 cached_tokens 让 cc2 看到 cache_read 真实值 (纯增益).
        self.cache_read_tokens = 0
        # content accumulators (caller uses these for zombie/empty detection)
        self.content_chars = 0
        self.reasoning_chars = 0
        self.saw_real_tool_call = False
        self.pending_stop_reason = None
        self.finish_reason_seen = None
        # R1826 bug8 dump wire (PURE OBSERVATION, no downgrade):
        # Accumulate each tool_use's full arguments string (keyed by tool_use id) as
        # partial_json chunks stream through feed_chunk. At finish() we json.loads()
        # each accumulation point to detect malformed tool_call arguments BEFORE the
        # CC SDK receives the assembled partial_json and throws "could not be parsed".
        # This is diagnostic ONLY — it never alters the `out` byte stream and never
        # downgrades; it just prints [NV-TOOLCALL-JSON-BAD] to stderr (docker logs).
        self.tool_args_acc = {}        # tool_use id -> concatenated arguments str
        self.tool_ids_order = []       # tool_use ids in arrival order
        self._active_tool_id = None    # current tool_use id receiving arg deltas
        self._tc_json_bad_logged = False  # guard: log at most once per request
        # R1837 bug8 downgrade: tool_use id -> content_block index (so finish() can
        # emit fix-up input_json_delta targeted at the RIGHT block when args are
        # malformed). Populated in feed_chunk at content_block_start for tool_use.
        self._tool_block_index = {}
        # R1839 bug8 降级兜底 (监督者 05:50 强制): finish() 正常完成路径若任何
        # tool_use 的累积 args json.loads() 失败 → 强制 stop_reason=end_turn (非
        # tool_use), 让 CC SDK 不走 tool_use 解析路径 (已流式 relay 的 partial_json
        # 被 stop_reason=end_turn 语义下忽略), session 不中断。绝不靠前缀匹配 (R1832/
        # R1836 前缀法天生漏网新形态)。存降级标记 + bad tid 列表供 finish() 决策。
        self._downgrade_to_end_turn = False
        self._downgrade_bad_tids = []

    # ─── block helpers ───────────────────────────────────────────────
    def _close_active_block(self):
        out = b""
        if self.active_block_type is not None:
            out += _sse_bytes("content_block_stop",
                              {"type": "content_block_stop", "index": self.next_block_idx - 1})
            self.active_block_type = None
        return out

    def _emit_message_start(self, msg_id=None, input_tokens_est=0):
        out = b""
        if not self.message_start_sent:
            out += _sse_bytes("message_start", {
                "type": "message_start",
                "message": {
                    "id": msg_id or f"msg_{uuid.uuid4().hex[:24]}",
                    "type": "message", "role": "assistant",
                    "model": self.request_model, "content": [],
                    "stop_reason": None, "stop_sequence": None,
                    "usage": {"input_tokens": input_tokens_est, "output_tokens": 0,
                              "cache_creation_input_tokens": 0,
                              "cache_read_input_tokens": self.cache_read_tokens},
                },
            })
            self.message_start_sent = True
        return out

    def feed_chunk(self, chunk_data):
        """Feed one parsed OpenAI SSE chunk dict. Returns bytes to write to client.

        Does NOT emit message_stop / final message_delta — those come from finish().
        Returns b"" for chunks with no convertible content (e.g. usage-only, empty delta).
        """
        out = b""
        if not isinstance(chunk_data, dict):
            return out

        # usage (may arrive in any chunk; track but don't emit yet)
        chunk_usage = chunk_data.get("usage") or {}
        if chunk_usage:
            pt = chunk_usage.get("prompt_tokens", 0)
            ct = chunk_usage.get("completion_tokens", 0)
            if pt > 0:
                self.input_tokens = pt
            if ct > 0:
                self.output_tokens = ct
            # R2223 t1: NVCF 返回 prompt_tokens_details.cached_tokens (实测可命中).
            # 透传给 cc4101, 让 cc2 usage 看到 cache_read 真实值.
            _ptd = chunk_usage.get("prompt_tokens_details") or {}
            _ct = _ptd.get("cached_tokens") or 0
            if _ct:
                self.cache_read_tokens = _ct

        # ensure message_start goes out before any delta (use upstream msg id if present)
        if not self.message_start_sent:
            out += self._emit_message_start(
                chunk_data.get("id", f"msg_{uuid.uuid4().hex[:24]}"))

        choices = chunk_data.get("choices") or [{}]
        delta = choices[0].get("delta") or {}
        finish_reason = choices[0].get("finish_reason")

        # accumulate content chars (caller reads these for zombie detection)
        _delta_content = delta.get("content") or ""
        if _delta_content:
            self.content_chars += len(_delta_content)
        _delta_reasoning = delta.get("reasoning_content") or ""
        if _delta_reasoning:
            self.reasoning_chars += len(_delta_reasoning)
        for _tc in (delta.get("tool_calls") or []):
            _fn = _tc.get("function", {}) or {}
            if _tc.get("id") and _fn.get("arguments"):
                self.saw_real_tool_call = True

        # ── Reasoning / thinking ──
        # Anthropic: thinking blocks must precede text/tool_use and cannot reopen
        # after. Once a text/tool_use block started, drop further reasoning deltas.
        reasoning = delta.get("reasoning_content")
        if reasoning and self.active_block_type not in (None, "thinking"):
            reasoning = None
        if reasoning:
            if self.active_block_type != "thinking":
                out += self._close_active_block()
                out += _sse_bytes("content_block_start", {
                    "type": "content_block_start", "index": self.next_block_idx,
                    "content_block": {"type": "thinking", "thinking": "",
                                      "signature": THINKING_SIGNATURE},
                })
                self.next_block_idx += 1
                self.active_block_type = "thinking"
            out += _sse_bytes("content_block_delta", {
                "type": "content_block_delta", "index": self.next_block_idx - 1,
                "delta": {"type": "thinking_delta", "thinking": reasoning},
            })

        # ── Text ──
        text_delta = delta.get("content")
        if text_delta and self.active_block_type != "text":
            out += self._close_active_block()
            out += _sse_bytes("content_block_start", {
                "type": "content_block_start", "index": self.next_block_idx,
                "content_block": {"type": "text", "text": ""},
            })
            self.next_block_idx += 1
            self.active_block_type = "text"
        if text_delta:
            out += _sse_bytes("content_block_delta", {
                "type": "content_block_delta", "index": self.next_block_idx - 1,
                "delta": {"type": "text_delta", "text": text_delta},
            })

        # ── Tool calls ──
        tool_calls = delta.get("tool_calls") or []
        for tc in tool_calls:
            fn = tc.get("function", {}) or {}
            if tc.get("id"):
                out += self._close_active_block()
                out += _sse_bytes("content_block_start", {
                    "type": "content_block_start", "index": self.next_block_idx,
                    "content_block": {
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": fn.get("name", ""),
                        "input": {},
                    },
                })
                self.next_block_idx += 1
                self.active_block_type = "tool_use"
                # R1837: record this tool_use's content_block index so finish() can
                # target a fix-up input_json_delta at the right block if its args
                # turn out malformed on completion.
                self._tool_block_index[tc["id"]] = self.next_block_idx - 1
                # R1826 bug8 dump wire (PURE OBSERVATION): track this tool_use's id so
                # subsequent arg deltas accumulate into it. Append to tool_ids_order.
                self._active_tool_id = tc["id"]
                if tc["id"] not in self.tool_args_acc:
                    self.tool_args_acc[tc["id"]] = ""
                    self.tool_ids_order.append(tc["id"])
                if fn.get("arguments"):
                    self.tool_args_acc[tc["id"]] += fn["arguments"]
                    out += _sse_bytes("content_block_delta", {
                        "type": "content_block_delta", "index": self.next_block_idx - 1,
                        "delta": {"type": "input_json_delta", "partial_json": fn["arguments"]},
                    })
            elif fn.get("arguments") and self.active_block_type == "tool_use":
                # R1826 bug8 dump wire: accumulate continuation args into active tool_use.
                if self._active_tool_id is not None:
                    self.tool_args_acc[self._active_tool_id] += fn["arguments"]
                out += _sse_bytes("content_block_delta", {
                    "type": "content_block_delta", "index": self.next_block_idx - 1,
                    "delta": {"type": "input_json_delta", "partial_json": fn["arguments"]},
                })

        # ── Finish reason (track; do NOT emit stop here — caller decides zombie vs end) ──
        if finish_reason:
            self.finish_reason_seen = finish_reason
            if finish_reason == "content_filter":
                self.pending_stop_reason = None  # caller turns this into zombie
            elif finish_reason == "length":
                self.pending_stop_reason = "max_tokens"
            elif finish_reason == "tool_calls":
                self.pending_stop_reason = "tool_use"
            else:
                self.pending_stop_reason = "end_turn"

        return out

    def _tc_json_bad_check(self):
        """R1826 bug8 dump wire — PURE OBSERVATION, no downgrade.

        json.loads() each accumulated tool_use arguments string. If any are
        malformed (the case CC SDK hits and throws "could not be parsed"), emit a
        single `[NV-TOOLCALL-JSON-BAD]` stderr line (→ docker logs) capturing
        request_id, which tool_use id(s) are bad, and a truncated raw fragment.
        NEVER alters the SSE `out` stream and NEVER downgrades — diagnostic only.
        Logs at most once per request via `_tc_json_bad_logged`.
        """
        if self._tc_json_bad_logged or not self.tool_ids_order:
            return
        bad = []
        for tid in self.tool_ids_order:
            raw = self.tool_args_acc.get(tid, "")
            try:
                json.loads(raw if raw else "{}")
            except json.JSONDecodeError:
                bad.append((tid, raw))
        if not bad:
            return
        # R1832 bug8 noise filter — PURE OBSERVATION, no downgrade.
        # The bug8 observer has fired the SAME 2 self-feedback hits every round
        # since R1829: rid 9885ad97 (tool_call whose args = the R1829 round file
        # markdown body) and rid 791d66bf (args = STATE.md body). These are NOT
        # ordinary user traffic — they're cc2 reading its own STATE/round files,
        # where the model emits a long markdown doc as a tool_call content field
        # that never closes its JSON quote. They are real JSON-bad but a known
        # artifact of the self-feedback workflow, not bug8 triggering in the
        # normal link. Suppress their noisy dump so the next genuine malformed
        # tool_call (non-self-feedback) actually stands out in docker logs.
        # Patterns cover: bare `{"content": "# <markdown>` (unclosed quote), and
        # self-feedback doc bodies that mention STATE/round markers. NEVER alters
        # the SSE `out` stream and NEVER downgrades — still diagnostic only.
        # R1836 扩展: R1832 只盖 `{"content": "#` 前缀, 但 cc2 改用 bash heredoc 写
        # STATE/round 后模型生成 args=`{"command": "cat > ... << 'STATEEOF'\\n# cc2 自优化
        # 交接棒 STATE..."` (heredoc 内末正确转义双引号 → JSON-bad), 前缀是 `{"command": "`
        # 非 `{"content": "#` 绕过了 R1832 过滤 (R1836 30min 2 命中 nec83bc5ac/4e8fb7a9
        # 全 restart 后). 故扩前缀检查盖第二种自反馈路径 (bash command), marker 列表不变.
        # 仍纯观测, 绝不降级不中断.
        # R2180: 更新自反馈过滤 (marker+prefix 老化). 旧 marker "# R18" 只匹配 R18xx 轮号,
        # 轮号进 R21xx 后失效; 旧 prefix 没覆盖 Write 工具的 {"file_path": " 前缀 (cc2 改用
        # Write 写 STATE/round 后模型生成的 args 前缀). 6h 实测 8 命中全漏网打印 (R2174-R2179).
        # 改: marker 用通用文本 (非轮号) + prefix 加 file_path. R1839 真降级已兜住危害
        # (final_stop=end_turn, session 不中断), 此处只是观测噪音过滤, 让真非自反馈畸形凸显.
        SELF_FB_MARKERS = ("cc2 自优化", "hm2_cc2", "openclaw2 自优化", "交接棒 STATE", "STATE.md", "hm2_oc2")
        SELF_FB_PREFIXES = ('{"content": "#', '{"command": "', '{"file_path": "')
        real_bad = []
        for tid, raw in bad:
            r = raw or ""
            stripped = r.lstrip()
            if stripped.startswith(SELF_FB_PREFIXES) and any(m in r for m in SELF_FB_MARKERS):
                continue
            real_bad.append((tid, raw))
        if not real_bad:
            return
        self._tc_json_bad_logged = True
        rid = self.request_id or "-"
        for tid, raw in real_bad:
            frag = (raw or "")[:500]
            print(f"[NV-TOOLCALL-JSON-BAD] rid={rid} tid={tid} len={len(raw or '')} "
                  f"frag={frag!r}", file=sys.stderr, flush=True)

    def _detect_bad_tool_args(self):
        """R1839 bug8 降级兜底 (监督者 05:50 强制) — 真降级, 非观测。

        对每个累积的 tool_use args 做 json.loads() 校验 (不挑食, 不靠前缀过滤:
        R1832/R1836 的前缀法天生漏网新形态, 监督者已确认 05:28 仍因第三种前缀漏网
        而中断)。任一 tids 的 args json.loads() 失败 → 记为 bad, 触发降级。

        绝不向 CC relay 畸形 tool_use 的语义: finish() 会把 final_stop 强制 end_turn
        (非 tool_use), 让 CC SDK 不走 tool_use args 解析路径 → 已流式 relay 的
        partial_json 在 stop_reason=end_turn 语义下被忽略 → CC 不抛 "could not be
        parsed" → session 不中断。宁可 drop tool_call 让 cc2 这轮没拿到工具结果
        (session 活着, 下轮 timer 接力), 也不要 relay 畸形 JSON 让 CC 中断。
        返回 bad tids 列表 (空 = 全合法, 无需降级)。
        """
        if not self.tool_ids_order:
            return []
        bad_tids = []
        for tid in self.tool_ids_order:
            raw = self.tool_args_acc.get(tid, "")
            try:
                json.loads(raw if raw else "{}")
            except json.JSONDecodeError:
                bad_tids.append(tid)
        return bad_tids

    def finish(self, interrupted=False, zombie=False, input_tokens_real=0, flushed_content_chars=0):
        """Emit terminal events (content_block_stop, message_delta, message_stop).

        caller contract:
          zombie=True        → R1771: 若 flushed_content_chars>0 (已有真内容 flush 给 CC),
                              不发 event: error (CC SDK 会当致命错中断 session), 改发
                              graceful message_delta(stop_reason=tool_use/end_turn)+message_stop,
                              让 CC 把已收内容当完整响应收尾, 不中断。零内容场景仍发
                              api_error 让 CC 重试。
          interrupted=True   → emit api_error SSE (upstream cut mid-flight, no finish_reason).
          otherwise          → emit graceful message_delta + message_stop.

        Returns bytes to write. Always non-empty.
        """
        out = b""
        # R1827 bug8 dump wire 去噪: 只在正常完成路径 (非 zombie 非 interrupted) 校验
        # args JSON。zombie/interrupted 路径 args 必被流式截断 (如 ttfb 75s 抢断 fallback
        # 时 args 正在生成), json.loads 必失败 → 误报噪声盖信号。真 bug8 = finish_reason=
        # tool_calls 正常完成但 args 仍畸形; 只该路径 fire。zero-content zombie 路径 CC
        # 已被 graceful/error 兜底, 不依赖 args 解析, 漏报无害。
        if not zombie and not interrupted:
            self._tc_json_bad_check()
            # R1839 bug8 降级兜底 (监督者 05:50 强制): 真降级, 非观测。检测累积
            # tool_use args 是否畸形 (不挑食, json.loads 全检, 不靠前缀过滤), 任一
            # 畸形 → 强制 final_stop=end_turn (非 tool_use)。CC SDK 看 stop_reason
            # 决定是否走 tool_use 解析路径: end_turn → 不解析已 relay 的 partial_json
            # → 不抛 "could not be parsed" → session 不中断。content_block_stop 仍发
            # (让事件序列闭合合法)。绝不删已 relay 的 partial_json (丢不回) — 靠
            # stop_reason=end_turn 让 CC SDK 忽略它。
            bad_tids = self._detect_bad_tool_args()
            if bad_tids:
                self._downgrade_to_end_turn = True
                self._downgrade_bad_tids = bad_tids
                rid_dn = self.request_id or "-"
                # 备注降级触发 (区别于纯观测 _tc_json_bad_check): 这条 flag 才是
                # "真改 SSE out" 的标志 (强制改 stop_reason)。
                print(f"[NV-TOOLCALL-JSON-DOWNGRADE] rid={rid_dn} bad_tids={bad_tids} "
                      f"-> final_stop=end_turn (CC SDK 忽略已 relay partial_json, "
                      f"session 不中断)", file=sys.stderr, flush=True)
        out += self._close_active_block()
        if not self.message_start_sent:
            out += self._emit_message_start()

        if zombie:
            # R1771: 有真内容时伪装成完整响应收尾, 不发 event: error (会致 CC mid-response 中断)
            # R1820 用户兜底诉求: message_start_sent=True ⟺ nv_gw 已 send_response(200)+flush message_start,
            # CC 已进入流式接收。此时即使 flushed_content_chars=0 (如 bug7 cap 在主循环入参 break,
            # prebuffer 已 flush 但 parse 计数还没累加) 也必须 graceful end, 绝不发 event: error
            # (CC SDK 把 event:error 当致命错中断整个 session)。
            if flushed_content_chars > 0 or self.message_start_sent:
                if not self.message_delta_sent:
                    real_output = self.output_tokens
                    real_input = self.input_tokens or input_tokens_real
                    final_stop = self.pending_stop_reason or "end_turn"
                    # R1932 bug8 根因修复 (监督者 21:00 深度定位): NVCF "半响应" —
                    # 声明 finish_reason=tool_calls 但实际未发任何带 id+args 的真 tool_call
                    # delta (saw_real_tool_call=False)。pending_stop_reason 被 finish_reason
                    # chunk 设成 "tool_use" 但 CC SDK 看不到 tool_use block → "could not be
                    # parsed" → session 中断 (3 次/2d) + 132 次 malformed retry。
                    # 修复: 声明 tool_use 但未真正发 tool_use block → 强制 end_turn, 让 CC SDK
                    # 不走 tool_use 解析路径。镜像 R1839 _detect_bad_tool_args 模式, 补 finish()
                    # 漏读的 saw_real_tool_call flag (line 74 init/166 set, 此前从不被读)。
                    # 与 R1839 互补: R1839 兜 "有 block 但 args 畸形", R1932 兜 "声明 tool_calls
                    # 但压根没发 block"。正常 tool_call (id+args 齐全) saw_real_tool_call=True 不受影响。
                    if self.pending_stop_reason == "tool_use" and not self.saw_real_tool_call:
                        final_stop = "end_turn"
                    # R1839 bug8 降级兜底: 畸形 tool_use args → 强制 end_turn
                    if self._downgrade_to_end_turn:
                        final_stop = "end_turn"
                    usage_delta = {"output_tokens": real_output}
                    if real_input > 0:
                        usage_delta["input_tokens"] = real_input
                    if self.cache_read_tokens > 0:
                        usage_delta["cache_read_input_tokens"] = self.cache_read_tokens
                    out += _sse_bytes("message_delta", {
                        "type": "message_delta",
                        "delta": {"stop_reason": final_stop, "stop_sequence": None},
                        "usage": usage_delta,
                    })
                    self.message_delta_sent = True
                out += _sse_bytes("message_stop", {"type": "message_stop"})
                return out
            # 零内容 zombie: 保留 event: error 让 CC 重试
            out += _sse_bytes("error", {
                "type": "error",
                "error": {"type": "api_error",
                          "message": "upstream returned empty/filtered completion, please retry"},
            })
            out += _sse_bytes("message_stop", {"type": "message_stop"})
            return out

        # R1820 用户兜底诉求: message_start 已发 (200 头已出去, CC 已进入流式) → 不再发
        # event: error (CC SDK 判 mid-response 中断 session)。只有 message_start 都没发的
        # 极早期失败 (send_response 之前) 才允许 event: error, 此时 CC 自动重试, 不算中断。
        if interrupted and self.pending_stop_reason is None and not self.message_start_sent:
            out += _sse_bytes("error", {
                "type": "error",
                "error": {"type": "api_error",
                          "message": "upstream stream interrupted before completion"},
            })
            out += _sse_bytes("message_stop", {"type": "message_stop"})
            return out

        if not self.message_delta_sent:
            real_output = self.output_tokens
            real_input = self.input_tokens or input_tokens_real
            final_stop = self.pending_stop_reason or "end_turn"
            # R1932 bug8 根因修复 (监督者 21:00 深度定位): 见 zombie 路径同款注释。
            # 正常完成路径 (非 zombie 非 interrupted): NVCF 声明 finish_reason=tool_calls 但
            # 未发真 tool_call delta (saw_real_tool_call=False) → 强制 end_turn, 免 CC SDK
            # 走 tool_use 解析抛 "could not be parsed"。saw_real_tool_call (line 166) 只在
            # tool_call delta 带 id+非空 args 时置真, 故正常 tool_call 不受影响。
            if self.pending_stop_reason == "tool_use" and not self.saw_real_tool_call:
                final_stop = "end_turn"
            # R1839 bug8 降级兜底 (监督者 05:50 强制): 正常完成路径, 任一累积
            # tool_use args 畸形 → 强制 end_turn (非 tool_use)。CC SDK 看
            # stop_reason=end_turn 不走 tool_use 解析路径, 已 relay 的 partial_json
            # 被忽略 → 不抛 "could not be parsed" → session 不中断。宁可丢这轮
            # tool 结果 (下轮 timer 接力) 不让 CC 中断。
            if self._downgrade_to_end_turn:
                final_stop = "end_turn"
            usage_delta = {"output_tokens": real_output}
            if real_input > 0:
                usage_delta["input_tokens"] = real_input
            if self.cache_read_tokens > 0:
                usage_delta["cache_read_input_tokens"] = self.cache_read_tokens
            out += _sse_bytes("message_delta", {
                "type": "message_delta",
                "delta": {"stop_reason": final_stop, "stop_sequence": None},
                "usage": usage_delta,
            })
            self.message_delta_sent = True
        out += _sse_bytes("message_stop", {"type": "message_stop"})
        return out


def convert_error_to_anth(error_json, request_model):
    """Convert an OpenAI-format error → Anthropic-format error (R1648b).

    Mirrors cc4101's `error_mapping.convert_error` (oai→anth) so nv_gw's
    `/v1/messages` endpoint can return errors in the format Claude Code expects,
    without depending on cc4101. CC error-type semantics that drive each branch
    (see cc4101 error_mapping.py docstring) are preserved verbatim.

      - 429 quota/rate → rate_limit_error (CC backoff)
      - "inappropriate content" → invalid_request_error (CC stops)
      - input-overflow phrases → invalid_request_error (CC stops, no compact)
      - everything else → api_error (CC retries)
    """
    err = error_json.get("error", error_json) if isinstance(error_json, dict) else error_json
    if isinstance(err, dict):
        msg = err.get("message", str(err))
    else:
        msg = str(err)
    msg_lower = msg.lower()
    err_type = "api_error"

    err_code = ""
    if isinstance(err, dict):
        err_code = (err.get("code") or "").lower()
    is_quota_exhausted = (
        "insufficient_quota" in err_code
        or ("quota" in msg_lower and "exceeded" in msg_lower)
        or ("exceeded your current quota" in msg_lower)
    )

    if is_quota_exhausted:
        err_type = "rate_limit_error"
    elif "rate limit" in msg_lower or "rate_limit" in msg_lower or "429" in msg_lower:
        err_type = "rate_limit_error"
    elif "inappropriate content" in msg_lower:
        err_type = "invalid_request_error"
    elif (("range of input length" in msg_lower)
          or ("invalidparameter" in msg_lower and ("input length" in msg_lower or "input token" in msg_lower or "exceeds" in msg_lower))):
        err_type = "invalid_request_error"
    return {"type": "error", "error": {"type": err_type, "message": msg}, "model": request_model}


def oai_nonstream_to_anth(openai_json, request_model):
    """Convert a non-stream OpenAI Chat Completions JSON response → Anthropic message JSON.

    Used by the nv_gw `/v1/messages` non-stream path (when upstream actually
    returns non-stream JSON, which for glm5.2 is rare — nv_gw forces stream
    upstream and accumulates — but provided for completeness / future models).
    """
    content = []
    choices = openai_json.get("choices") or [{}]
    choice = choices[0] if choices else {}
    msg = choice.get("message") or {}
    if msg.get("reasoning_content"):
        content.append({"type": "thinking", "thinking": msg["reasoning_content"],
                        "signature": THINKING_SIGNATURE})
    if msg.get("content"):
        content.append({"type": "text", "text": msg["content"]})
    for tc in (msg.get("tool_calls") or []):
        fn = tc.get("function", {}) or {}
        try:
            input_data = json.loads(fn.get("arguments", "{}"))
        except json.JSONDecodeError:
            input_data = {"raw": fn.get("arguments", "")}
        content.append({"type": "tool_use", "id": tc.get("id", ""),
                        "name": fn.get("name", ""), "input": input_data})
    if not content:
        content.append({"type": "text", "text": ""})

    fr = choice.get("finish_reason")
    stop_reason = "end_turn"
    if fr == "length":
        stop_reason = "max_tokens"
    elif fr == "tool_calls":
        stop_reason = "tool_use"
    elif fr == "content_filter":
        stop_reason = "end_turn"

    usage = openai_json.get("usage") or {}
    return {
        "id": openai_json.get("id", f"msg_{uuid.uuid4().hex[:24]}"),
        "type": "message",
        "role": "assistant",
        "model": request_model,
        "content": content,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        },
    }
