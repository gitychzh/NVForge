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

    def __init__(self, request_model):
        self.request_model = request_model
        self.message_start_sent = False
        self.message_delta_sent = False
        self.next_block_idx = 0
        self.active_block_type = None  # "thinking" | "text" | "tool_use"
        # token accumulators (from SSE usage chunks)
        self.input_tokens = 0
        self.output_tokens = 0
        # content accumulators (caller uses these for zombie/empty detection)
        self.content_chars = 0
        self.reasoning_chars = 0
        self.saw_real_tool_call = False
        self.pending_stop_reason = None
        self.finish_reason_seen = None

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
                              "cache_read_input_tokens": 0},
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
                if fn.get("arguments"):
                    out += _sse_bytes("content_block_delta", {
                        "type": "content_block_delta", "index": self.next_block_idx - 1,
                        "delta": {"type": "input_json_delta", "partial_json": fn["arguments"]},
                    })
            elif fn.get("arguments") and self.active_block_type == "tool_use":
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

    def finish(self, interrupted=False, zombie=False, input_tokens_real=0):
        """Emit terminal events (content_block_stop, message_delta, message_stop).

        caller contract:
          zombie=True        → emit api_error SSE (so CC retries), not end_turn.
          interrupted=True   → emit api_error SSE (upstream cut mid-flight, no finish_reason).
          otherwise          → emit graceful message_delta + message_stop.

        Returns bytes to write. Always non-empty.
        """
        out = b""
        out += self._close_active_block()
        if not self.message_start_sent:
            out += self._emit_message_start()

        if zombie:
            out += _sse_bytes("error", {
                "type": "error",
                "error": {"type": "api_error",
                          "message": "upstream returned empty/filtered completion, please retry"},
            })
            out += _sse_bytes("message_stop", {"type": "message_stop"})
            return out

        if interrupted and self.pending_stop_reason is None:
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
            usage_delta = {"output_tokens": real_output}
            if real_input > 0:
                usage_delta["input_tokens"] = real_input
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
