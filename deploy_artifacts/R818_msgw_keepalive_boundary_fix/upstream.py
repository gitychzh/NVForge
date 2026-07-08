#!/usr/bin/env python3
"""Upstream request execution + 2D (variant, key) rotation + cycle for ms_gw.

Core flow (per /v1/chat/completions request):
  1. _next_ms_n(model) → N  (持久化计数器 +1)
     variant_idx = (N // NUM_KEYS) % NUM_VARIANTS
     key_idx     = N % NUM_KEYS
  2. _try_ms_keys:
     for v_attempt in range(NUM_VARIANTS + 1):          # variant 轮换
       if variant cooling → skip
       for k_attempt in range(NUM_KEYS + 2):            # key 轮换 (同 variant)
         key_idx = (start_key_idx + k_attempt) % NUM_KEYS
         if key cooling → continue
         # build request with variants[variant_idx] + MS_KEYS[key_idx]
         resp = send to ModelScope
         result = _check_ms_response(resp)
         if success → return (relay)
         if cycle (empty_200/error body/upstream 5xx/timeout) → mark_key_cooling, continue
       # all keys of this variant failed → mark_variant_cooling, next variant
     # all variants exhausted → mark_all_exhausted, return error

  Cycle 不碰计数器 N (N 只在请求���始 +1 一次) — cooldown 恢复后自然轮到.
  empty_200 FASTBREAK: 连续 N 次 choices:null/error → 提前 break, 不试完 70 槽.
"""
import http.client
import json
import socket
import ssl
import sys
import time
import os
from urllib.parse import urlparse

from .config import (
    MS_BASEURL, MS_KEYS, NUM_KEYS, NUM_VARIANTS,
    MODEL_REGISTRY, UPSTREAM_TIMEOUT, PROXY_TIMEOUT,
    MIN_OUTBOUND_INTERVAL_S, EMPTY_200_FASTBREAK_THRESHOLD,
)
from .rr_counter import _next_ms_n
from .cooldown import (
    is_key_cooling, mark_key_cooling, reset_key,
    is_variant_cooling, mark_variant_cooling,
    is_all_exhausted_cooling, mark_all_exhausted,
)
from .logger import _log, _log_metrics, _log_error_detail

# ─── Burst throttle (between outbound requests) ──────────────────────────
_last_outbound_ts = 0.0
_outbound_lock = __import__("threading").Lock()

def _throttle_outbound():
    """Enforce MIN_OUTBOUND_INTERVAL_S between outbound requests (rpm=1 protection)."""
    global _last_outbound_ts
    import threading
    with _outbound_lock:
        now = time.monotonic()
        wait = MIN_OUTBOUND_INTERVAL_S - (now - _last_outbound_ts)
        if wait > 0:
            time.sleep(wait)
        _last_outbound_ts = time.monotonic()


# ─── Request sanitization (thinking params strip) ────────────────────────
# MS glm5.2 thinking: reasoning_effort + thinking_budget (41001 config 实证).
# NVCF glm5.2 thinking: chat_template_kwargs.enable_thinking (nv-uni config 实证).
# Agent fallback from NVCF may carry NVCF-style params — strip them.

_NVCF_STYLE_PARAMS = {
    "chat_template_kwargs",       # NVCF pexec style
    "thinking",                   # some clients send this
    "thinking_effort",            # alternate naming
}

# MS-supported OpenAI params (whitelist, others passed through best-effort)
_MS_PASSTHROUGH_PARAMS = {
    "model", "messages", "max_tokens", "max_completion_tokens",
    "reasoning_effort", "thinking_budget",
    "temperature", "top_p", "stream", "stop",
    "tools", "tool_choice", "frequency_penalty", "presence_penalty",
    "n", "user", "response_format", "seed", "logprobs",
}


def _sanitize_request_body(body, model_spec):
    """Strip NVCF-style params, keep MS-compatible params.

    Returns a new dict (does not mutate input).
    """
    if not isinstance(body, dict):
        return body
    cleaned = {}
    for k, v in body.items():
        if k in _NVCF_STYLE_PARAMS:
            _log("MS-SANITIZE", f"stripped NVCF-style param: {k}")
            continue
        cleaned[k] = v
    # Map agent-facing model_id → backend variant model_id (done by caller)
    return cleaned


# ─── Response validation (white-list + error body detection) ─────────────
# MS does NOT return 429. It returns:
#   - HTTP 200 + {"choices":null, "usage":{all 0}}  (surge/quota malformed)
#   - HTTP 200 + {"error":{"code":"insufficient_quota",...}}  (quota out)
#   - HTTP 200 + {"error":{"code":"limit_burst_rate",...}}  (rate limit)
#   - HTTP 200 + {"choices":[{"message":{"content":""}}]}  (empty content)
# litellm asserts choices is not None → crashes. We detect and cycle.

class MSResponseCheck:
    """Result of checking an MS upstream response."""
    def __init__(self):
        self.success = False
        self.cycle = False           # → try next key
        self.reason = ""             # cycle reason
        self.error_body = None       # parsed error dict if present
        self.empty_200 = False       # choices:null or empty content
        self.is_stream_error = False # stream first-chunk error
        self.is_rate_limit = False   # R806: 429/limit_burst_rate -- backoff not cycle
        self.backoff_s = 0.0         # R806: backoff seconds when is_rate_limit


def _check_ms_nonstream(resp, body_bytes):
    """Check a non-stream MS response. Returns MSResponseCheck."""
    result = MSResponseCheck()
    if resp.status != 200:
        # Non-200 → cycle (treat as transient)
        result.cycle = True
        result.reason = f"http_{resp.status}"
        return result
    try:
        body = json.loads(body_bytes)
    except Exception as e:
        result.cycle = True
        result.reason = f"bad_json: {e}"
        return result
    # Explicit error body
    if isinstance(body, dict) and body.get("error"):
        result.error_body = body["error"]
        code = body["error"].get("code", "unknown")
        result.cycle = True
        result.reason = f"error_body:{code}"
        return result
    # choices missing or null
    choices = body.get("choices") if isinstance(body, dict) else None
    if not choices:
        result.empty_200 = True
        result.cycle = True
        result.reason = "choices_null"
        return result
    # choices[0] must have message with content, or delta (stream)
    try:
        first = choices[0]
    except (IndexError, KeyError, TypeError):
        result.empty_200 = True
        result.cycle = True
        result.reason = "choices_empty_list"
        return result
    msg = first.get("message") if isinstance(first, dict) else None
    if msg is not None:
        content = msg.get("content")
        reasoning = msg.get("reasoning_content")
        # content can be string or list (multimodal) — accept non-empty
        content_nonempty = (
            (isinstance(content, str) and content != "") or
            (isinstance(content, list) and len(content) > 0)
        )
        # glm5.2 thinking: when thinking enabled and max_tokens small, content may
        # be empty but reasoning_content holds the actual output. Treat as success.
        reasoning_nonempty = (
            (isinstance(reasoning, str) and reasoning != "") or
            (isinstance(reasoning, list) and len(reasoning) > 0)
        )
        if content_nonempty or reasoning_nonempty:
            result.success = True
            return result
        # empty content + empty reasoning — could be tool_calls only
        if msg.get("tool_calls"):
            result.success = True
            return result
        result.empty_200 = True
        result.cycle = True
        result.reason = "content_empty"
        return result
    # No message key — but delta might still be valid (MS sometimes sends delta without message)
    delta = first.get("delta") if isinstance(first, dict) else None
    if isinstance(delta, dict) and (delta.get("content") or delta.get("reasoning_content")):
        result.success = True
        return result
    result.empty_200 = True
    result.cycle = True
    result.reason = "no_message_key"
    return result


def _check_ms_stream_first_chunk(first_chunk_str, resp_status=200):
    """Check the first chunk of a stream response BEFORE sending 200 to client.

    Returns MSResponseCheck. If success, it is safe to start streaming (send 200).
    If cycle, we should NOT send 200 -- cycle to next key instead.
    R806: resp_status non-200 (429/5xx) = aliyun rate limit -> backoff, not cycle-swap.
    """
    result = MSResponseCheck()
    # R806: ModelScope now returns 429 directly (was 200+error body). Detect rate limit.
    if resp_status != 200:
        rl_codes = ("limit_burst_rate", "insufficient_quota", "rate_limit", "quota")
        body_hint = (first_chunk_str or "").lower()
        if resp_status == 429 or any(c in body_hint for c in rl_codes):
            result.is_rate_limit = True
            result.backoff_s = 3.0
            result.cycle = True
            result.reason = "http_%d_rate_limit" % resp_status
            return result
        result.cycle = True
        result.reason = "http_%d" % resp_status
        return result
    if not first_chunk_str:
        result.empty_200 = True
        result.cycle = True
        result.reason = "stream_empty_first_chunk"
        return result
    # SSE format: "data: {...}\n\n"
    data_lines = []
    for line in first_chunk_str.splitlines():
        if line.startswith("data:"):
            payload = line[5:].strip()
            if payload == "[DONE]":
                continue
            data_lines.append(payload)
    if not data_lines:
        # Could be a comment line (":\n\n") — stream heartbeat. Treat as not-yet-error.
        # But if that's ALL we got in first chunk, it's ambiguous — treat as cycle.
        result.empty_200 = True
        result.cycle = True
        result.reason = "stream_no_data_lines"
        return result
    # Try to parse first data payload
    for payload in data_lines:
        try:
            obj = json.loads(payload)
        except Exception:
            continue
        if isinstance(obj, dict):
            if obj.get("error"):
                result.error_body = obj["error"]
                result.cycle = True
                result.reason = f"stream_error_body:{obj['error'].get('code','?')}"
                return result
            choices = obj.get("choices")
            if choices is None:
                result.empty_200 = True
                result.cycle = True
                result.reason = "stream_choices_null"
                return result
            if isinstance(choices, list) and len(choices) > 0:
                first = choices[0]
                if isinstance(first, dict) and first.get("delta"):
                    result.success = True
                    return result
                # Some MS chunks have choices[0] without delta (role chunk)
                if isinstance(first, dict) and (first.get("delta") is not None or
                                                first.get("message") is not None or
                                                first.get("index") is not None):
                    result.success = True
                    return result
    # Couldn't find a definitive success signal — be conservative, cycle.
    result.empty_200 = True
    result.cycle = True
    result.reason = "stream_no_valid_choice"
    return result


# ─── Connection ───────────────────────────────────────────────────────────
_parsed = urlparse(MS_BASEURL)
_MS_HOST = _parsed.hostname
_MS_PORT = _parsed.port or (443 if _parsed.scheme == "https" else 80)
_MS_SCHEME = _parsed.scheme
_MS_PATH_PREFIX = _parsed.path.rstrip("/")  # usually "/v1"

_ssl_ctx = ssl.create_default_context() if _MS_SCHEME == "https" else None


def _open_ms_conn():
    """Open a fresh connection to ModelScope."""
    if _MS_SCHEME == "https":
        conn = http.client.HTTPSConnection(_MS_HOST, _MS_PORT,
                                           timeout=UPSTREAM_TIMEOUT,
                                           context=_ssl_ctx)
    else:
        conn = http.client.HTTPConnection(_MS_HOST, _MS_PORT,
                                          timeout=UPSTREAM_TIMEOUT)
    return conn


# ─── Result container ────────────────────────────────────────────────────
class MSExecResult:
    def __init__(self):
        self.relay = False          # if True, resp/conn ready for handler to stream/relay
        self.resp = None            # http.client.HTTPResponse (for relay)
        self.conn = None            # the connection (handler must close)
        self.error_status = None    # if not relay: error status to send
        self.error_body = None      # if not relay: error body (dict)
        self.metrics = {}           # extra metrics
        self.attempts = []          # cycle attempt log


def _try_ms_keys(body, agent_model, request_id, metrics, t_start,
                 is_stream, upstream_timeout_override=None):
    """Try MS keys with 2D rotation. Returns MSExecResult.

    body: sanitized OpenAI request body (agent-facing model_id still in body['model'])
    agent_model: the agent-facing model_id (e.g. "glm5_2_ms")
    """
    result = MSExecResult()
    spec = MODEL_REGISTRY.get(agent_model)
    if not spec or spec.get("_disabled"):
        from .error_mapping import model_disabled_error, model_not_found_error
        if not spec:
            status, err = model_not_found_error(agent_model)
        else:
            status, err = model_disabled_error(agent_model)
        result.error_status = status
        result.error_body = err
        return result

    variants = spec["variants"]
    if not variants:
        from .error_mapping import model_disabled_error
        status, err = model_disabled_error(agent_model)
        result.error_status = status
        result.error_body = err
        return result

    # All-exhausted cooldown check
    if is_all_exhausted_cooling(agent_model):
        from .error_mapping import all_keys_exhausted_error
        _log("MS-ALL-EXHAUSTED-COOL", f"model={agent_model} in all-exhausted cooldown")
        status, err = all_keys_exhausted_error(agent_model, "all_exhausted_cooldown_active")
        result.error_status = status
        result.error_body = err
        return result

    # Get next N from persistent counter → start (variant, key)
    n = _next_ms_n(agent_model)
    start_variant = (n // NUM_KEYS) % NUM_VARIANTS
    start_key = n % NUM_KEYS
    _log("MS-RR", f"req={request_id} model={agent_model} N={n} "
                  f"start_variant={start_variant} start_key={start_key}")

    backend_model_name = ""  # set per attempt

    for v_offset in range(NUM_VARIANTS + 1):
        variant_idx = (start_variant + v_offset) % NUM_VARIANTS
        if is_variant_cooling(agent_model, variant_idx):
            continue
        backend_model_name = variants[variant_idx]
        # Per-variant empty counter: fastbreak should not starve a variant by
        # carrying over failures from the previous variant.
        consecutive_empty = 0

        for k_offset in range(NUM_KEYS + 2):
            key_idx = (start_key + k_offset) % NUM_KEYS
            if is_key_cooling(agent_model, variant_idx, key_idx):
                continue

            api_key = MS_KEYS[key_idx]
            elapsed_ms = int((time.monotonic() - t_start) * 1000)

            # Build outbound body: replace model with backend variant
            out_body = dict(body)
            out_body["model"] = backend_model_name

            # Throttle (rpm=1 protection)
            _throttle_outbound()

            attempt = {
                "variant_idx": variant_idx, "key_idx": key_idx,
                "backend_model": backend_model_name,
                "t_request_ms": elapsed_ms,
            }
            conn = None
            try:
                conn = _open_ms_conn()
                path = _MS_PATH_PREFIX + "/chat/completions"
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream" if is_stream else "application/json",
                }
                body_bytes = json.dumps(out_body, ensure_ascii=False).encode("utf-8")
                conn.request("POST", path, body=body_bytes, headers=headers)
                # Set read timeout after request sent
                conn.sock.settimeout(UPSTREAM_TIMEOUT)
                resp = conn.getresponse()

                if is_stream:
                    # Read first chunk to check for error BEFORE committing 200 to client
                    first_chunk = resp.read(8192)
                    first_str = first_chunk.decode("utf-8", errors="replace") if first_chunk else ""
                    chk = _check_ms_stream_first_chunk(first_str, resp.status)
                    if chk.success:
                        # Safe to relay — but we already consumed first_chunk.
                        # Hand off to handler: we'll re-inject first_chunk.
                        reset_key(agent_model, variant_idx, key_idx)
                        result.relay = True
                        result.resp = resp
                        result.conn = conn
                        result.metrics["first_chunk_prefetched"] = True
                        result.metrics["backend_model"] = backend_model_name
                        result.metrics["variant_idx"] = variant_idx
                        result.metrics["key_idx"] = key_idx
                        result.metrics["first_chunk_bytes"] = len(first_chunk)
                        # Stash first chunk for handler to replay
                        result.metrics["_first_chunk"] = first_chunk
                        result.attempts.append({**attempt, "status": "stream_ok"})
                        _log("MS-OK-STREAM", f"req={request_id} v{variant_idx}k{key_idx} "
                              f"backend={backend_model_name} first={len(first_chunk)}B")
                        return result
                    else:
                        # R806: rate-limit short-circuit. ModelScope 429/limit_burst_rate is
                        # transient (per-account burst). Do NOT mark_key_cooling -- that would
                        # cascade to all 7 keys -> variant exhausted -> cc4101 long stall.
                        # Instead: drain+close, backoff sleep, key stays eligible, continue.
                        if getattr(chk, "is_rate_limit", False):
                            _bo = float(getattr(chk, "backoff_s", 3.0) or 3.0)
                            _log("MS-RL-BACKOFF", f"req={request_id} v{variant_idx}k{key_idx} "
                                  f"reason={chk.reason} backoff {_bo:.1f}s (key kept warm)")
                            try:
                                while True:
                                    more = resp.read(1024)
                                    if not more:
                                        break
                            except Exception:
                                pass
                            try:
                                conn.close()
                            except Exception:
                                pass
                            time.sleep(_bo)
                            attempt["status"] = f"stream_rl_backoff:{chk.reason}"
                            result.attempts.append(attempt)
                            continue
                        # Cycle -- don't send 200 to client
                        reason = chk.reason
                        attempt["status"] = f"stream_cycle:{reason}"
                        result.attempts.append(attempt)
                        mark_key_cooling(agent_model, variant_idx, key_idx)
                        if chk.empty_200:
                            consecutive_empty += 1
                        _log("MS-STREAM-CYCLE", f"req={request_id} v{variant_idx}k{key_idx} "
                              f"cycle ({reason})")
                        # drain & close
                        try:
                            while True:
                                more = resp.read(1024)
                                if not more:
                                    break
                        except Exception:
                            pass
                        try: conn.close()
                        except Exception: pass
                        if consecutive_empty >= EMPTY_200_FASTBREAK_THRESHOLD:
                            _log("MS-FASTBREAK", f"req={request_id} stream "
                                  f"consecutive_empty={consecutive_empty} "
                                  f">= {EMPTY_200_FASTBREAK_THRESHOLD}, breaking")
                            mark_variant_cooling(agent_model, variant_idx)
                            break  # out of key loop, try next variant
                        continue
                else:
                    # Non-stream: read full body, check
                    body_bytes_resp = resp.read()
                    chk = _check_ms_nonstream(resp, body_bytes_resp)
                    if chk.success:
                        reset_key(agent_model, variant_idx, key_idx)
                        result.relay = True
                        result.resp = resp
                        result.conn = conn
                        result.metrics["backend_model"] = backend_model_name
                        result.metrics["variant_idx"] = variant_idx
                        result.metrics["key_idx"] = key_idx
                        result.metrics["_resp_body"] = body_bytes_resp
                        result.metrics["_resp_status"] = resp.status
                        result.attempts.append({**attempt, "status": "ok"})
                        _log("MS-OK", f"req={request_id} v{variant_idx}k{key_idx} "
                              f"backend={backend_model_name} status={resp.status}")
                        return result
                    else:
                        reason = chk.reason
                        attempt["status"] = f"cycle:{reason}"
                        result.attempts.append(attempt)
                        mark_key_cooling(agent_model, variant_idx, key_idx)
                        if chk.empty_200:
                            consecutive_empty += 1
                        _log("MS-CYCLE", f"req={request_id} v{variant_idx}k{key_idx} "
                              f"cycle ({reason}) empty_consecutive={consecutive_empty}")
                        try: conn.close()
                        except Exception: pass
                        if consecutive_empty >= EMPTY_200_FASTBREAK_THRESHOLD:
                            _log("MS-FASTBREAK", f"req={request_id} nonstream "
                                  f"consecutive_empty={consecutive_empty} "
                                  f">= {EMPTY_200_FASTBREAK_THRESHOLD}, breaking")
                            mark_variant_cooling(agent_model, variant_idx)
                            break  # try next variant
                        continue

            except (http.client.RemoteDisconnected, ConnectionResetError,
                    OSError, http.client.IncompleteRead, socket.timeout,
                    ssl.SSLError) as e:
                elapsed_ms = int((time.monotonic() - t_start) * 1000)
                attempt["status"] = f"exc:{type(e).__name__}"
                result.attempts.append(attempt)
                mark_key_cooling(agent_model, variant_idx, key_idx)
                _log("MS-EXC", f"req={request_id} v{variant_idx}k{key_idx} "
                      f"{type(e).__name__}: {e} ({elapsed_ms}ms)")
                _log_error_detail({
                    "request_id": request_id, "t_ms": elapsed_ms,
                    "variant_idx": variant_idx, "key_idx": key_idx,
                    "backend_model": backend_model_name,
                    "error_type": type(e).__name__, "error": str(e),
                })
                if conn:
                    try: conn.close()
                    except Exception: pass
                continue
            except Exception as e:
                elapsed_ms = int((time.monotonic() - t_start) * 1000)
                attempt["status"] = f"exc:{type(e).__name__}"
                result.attempts.append(attempt)
                _log("MS-EXC-UNEXP", f"req={request_id} v{variant_idx}k{key_idx} "
                      f"{type(e).__name__}: {e} ({elapsed_ms}ms)")
                _log_error_detail({
                    "request_id": request_id, "t_ms": elapsed_ms,
                    "variant_idx": variant_idx, "key_idx": key_idx,
                    "backend_model": backend_model_name,
                    "error_type": type(e).__name__, "error": str(e),
                    "unexpected": True,
                })
                if conn:
                    try: conn.close()
                    except Exception: pass
                continue

        # All keys of this variant failed → cool variant, try next
        if not result.relay:
            mark_variant_cooling(agent_model, variant_idx)
            _log("MS-VARIANT-EXHAUSTED", f"req={request_id} variant={variant_idx} "
                  "all keys failed, cooling variant")

    # All variants × keys exhausted
    mark_all_exhausted(agent_model)
    attempt_summary = "; ".join(
        f"v{a.get('variant_idx')}k{a.get('key_idx')}={a.get('status','?')}"
        for a in result.attempts[:20]
    ) or "no_attempts"
    from .error_mapping import all_keys_exhausted_error
    status, err = all_keys_exhausted_error(agent_model, attempt_summary)
    result.error_status = status
    result.error_body = err
    _log("MS-ALL-EXHAUSTED", f"req={request_id} model={agent_model} "
          f"attempts={len(result.attempts)} summary={attempt_summary[:200]}")
    return result
