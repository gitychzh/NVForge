#!/usr/bin/env python3
"""Upstream request executor for cc4101 — primary→fallback two-stage, always stream.

R684: Simplified from legacy-cc/gateway/upstream.py. No v×k cycling, no NV tiers,
no MS-NV interleaving. Just:
  1. Try PRIMARY (nv_gw glm5_2_nv) with stream=true.
  2. On 5xx / connection error / timeout / empty stream → try FALLBACK (ms_gw dsv4p_ms).
  3. On 4xx (client/quota) → do NOT fall back (same content will fail same way);
     return the error to the handler for Anthropic error formatting.

The handler (handlers.py) owns response formatting (stream or collect) and the
metrics lifecycle. This module returns an UpstreamResult with resp+conn ready
to read (stream) or an error classification.
"""
import json
import time
import http.client
import socket
import urllib.parse

from .config import (
    UPSTREAM_TIMEOUT,
    UPSTREAM_IDLE_TIMEOUT,
    UPSTREAM_HEADER_TIMEOUT,
    PRIMARY_HEADER_TIMEOUT,
    FALLBACK_HEADER_TIMEOUT,
    CC4101_TOTAL_BUDGET_S,
    RETRY_PRIMARY_AFTER_FALLBACK,
    CC4101_STREAM_POLL_S,
    PRIMARY_UPSTREAM_URL, PRIMARY_UPSTREAM_MODEL, PRIMARY_UPSTREAM_TOKEN,
    FALLBACK_UPSTREAM_URL, FALLBACK_UPSTREAM_MODEL, FALLBACK_UPSTREAM_TOKEN,
)
from .logger import _log, _log_error_detail
from .circuit import is_primary_open, record_primary_success, record_primary_failure


class UpstreamResult:
    def __init__(self):
        self.success = False
        self.resp = None          # http.client.HTTPResponse (ready to read SSE)
        self.conn = None          # http.client.HTTPConnection (caller closes)
        self.upstream_used = None  # "primary" | "fallback"
        self.mapped_model = None   # the model id sent upstream
        # error classification (when not success)
        self.error_kind = None     # "client_4xx" | "server_5xx" | "conn" | "timeout" | "empty_stream"
        self.error_status = 0      # upstream HTTP status (for 4xx/5xx)
        self.error_json = None     # upstream error body (dict) — for 4xx
        self.error_message = ""    # human-readable
        self.elapsed_ms = 0


def _parse_url(url):
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path or "/v1/chat/completions"
    if parsed.query:
        path += "?" + parsed.query
    return parsed.scheme, host, port, path


def _restore_read_timeout(conn, read_timeout):
    """R822: after response headers arrive, switch the socket back to the long
    read timeout so a slow body stream (long generation) is not killed by the
    short header timeout. http.client applies sock.settimeout on read()."""
    try:
        sock = conn.sock
        if sock is not None:
            sock.settimeout(read_timeout)
    except Exception:
        pass  # best-effort; header timeout will still apply as fallback


def _call_upstream(oai_body, url, model, token, request_id, timeout=UPSTREAM_TIMEOUT, header_timeout=None, idle_timeout=CC4101_STREAM_POLL_S):
    """Make one streaming POST to an upstream. Returns (resp, conn) on HTTP 200,
    or raises _UpstreamError with classification on any failure.

    We do NOT read the body here — the caller streams it. For non-200 we read
    the error body for classification.

    R823: header_timeout is the per-stage connect+TTFB timeout. If None, falls
    back to min(timeout, UPSTREAM_HEADER_TIMEOUT) (R822 behavior). Caller passes
    PRIMARY_HEADER_TIMEOUT / FALLBACK_HEADER_TIMEOUT to differentiate: primary
    (nv_gw) fails fast at 15s since its empty200 cycle takes 60s to fully fail
    and we want to hand off to fallback quickly; fallback (ms_gw) gets 30s so
    7-key RR with 3s 429-backoff (~18s worst case) can actually find a warm key.
    """
    scheme, host, port, path = _parse_url(url)
    if header_timeout is None:
        header_timeout = min(timeout, UPSTREAM_HEADER_TIMEOUT)
    header_timeout = min(header_timeout, timeout)  # never exceed body timeout
    if scheme == "https":
        conn = http.client.HTTPSConnection(host, port, timeout=header_timeout)
    else:
        conn = http.client.HTTPConnection(host, port, timeout=header_timeout)

    body_bytes = json.dumps(oai_body, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "Accept": "text/event-stream",
        "Connection": "close",
    }
    try:
        conn.request("POST", path, body=body_bytes, headers=headers)
        resp = conn.getresponse()
    except socket.timeout as e:
        try:
            conn.close()
        except Exception:
            pass
        raise _UpstreamError("timeout", 0, None, f"header/ttfb timeout after {header_timeout}s: {e}")
    except (ConnectionRefusedError, ConnectionResetError, OSError,
            http.client.HTTPException) as e:
        try:
            conn.close()
        except Exception:
            pass
        raise _UpstreamError("conn", 0, None, f"{type(e).__name__}: {e}")

    # R822/R830/R845: response header received — restore read timeout for body streaming.
    # R845 B7: per-read 改用短轮询 CC4101_STREAM_POLL_S(默认30s) 而非旧 UPSTREAM_IDLE_TIMEOUT(150s),
    # 让 stream.py 主循环的双门槛 stall-watcher 在 read 阻塞时也能获得检查点 (每 POLL_S 抛 socket.timeout→continue→检查).
    # UPSTREAM_IDLE_TIMEOUT(150s) 退为"总预算"语义, 由 stream.py 的 except 用 elapsed>=UPSTREAM_IDLE_TIMEOUT 判定真 idle.
    _restore_read_timeout(conn, idle_timeout)

    if resp.status != 200:
        # Read error body for classification
        try:
            err_bytes = resp.read()
            try:
                err_json = json.loads(err_bytes.decode("utf-8", errors="replace"))
            except Exception:
                err_json = {"error": {"message": err_bytes.decode("utf-8", errors="replace")[:500]}}
        except Exception:
            err_json = {"error": {"message": f"upstream status {resp.status} (no body)"}}
        try:
            conn.close()
        except Exception:
            pass
        kind = "client_4xx" if 400 <= resp.status < 500 else "server_5xx"
        raise _UpstreamError(kind, resp.status, err_json, f"upstream {resp.status}")

    # 200 — caller will stream. (Empty-stream detection happens in stream.py
    # when no content arrives; that's a fallback trigger, handled by caller.)
    return resp, conn


class _UpstreamError(Exception):
    def __init__(self, kind, status, error_json, message):
        self.kind = kind
        self.status = status
        self.error_json = error_json
        self.message = message
        super().__init__(message)


def execute_request(oai_body, request_id, metrics, t_start):
    """Try primary, then fallback on retryable failures, then retry primary
    if fallback also fails (R822). Returns UpstreamResult.

    oai_body already has stream=True set by the handler.
    """
    result = UpstreamResult()
    attempts = []  # for metrics
    t_start_mon = time.monotonic()  # R823: total-budget baseline across stages

    def _try_primary(stage_label):
        """One primary attempt. Returns True on success, client_4xx for
        non-retryable client errors, False for retryable failures."""
        t0 = time.monotonic()
        try:
            resp, conn = _call_upstream(
                oai_body, PRIMARY_UPSTREAM_URL, PRIMARY_UPSTREAM_MODEL,
                PRIMARY_UPSTREAM_TOKEN, request_id,
                header_timeout=PRIMARY_HEADER_TIMEOUT,
            )
        except _UpstreamError as e:
            ms = int((time.monotonic() - t0) * 1000)
            attempts.append({"stage": stage_label, "kind": e.kind, "status": e.status, "elapsed_ms": ms, "message": e.message})
            metrics["primary_error_type"] = e.kind
            metrics["primary_elapsed_ms"] = ms
            _log("PRIMARY-FAIL", f"primary ({PRIMARY_UPSTREAM_MODEL}) {e.kind} status={e.status} after {ms}ms ({stage_label}): {e.message[:160]}")
            if e.kind == "client_4xx":
                result.error_kind = e.kind
                result.error_status = e.status
                result.error_json = e.error_json
                result.error_message = e.message
                result.elapsed_ms = ms
                metrics["upstream_used"] = "primary"
                metrics["mapped_model"] = PRIMARY_UPSTREAM_MODEL
                metrics["key_cycle_details"] = attempts
                return "client_4xx"
            record_primary_failure()  # R824d: retryable fail -> may open circuit
            return False  # retryable: server_5xx / conn / timeout
        except Exception as e:
            ms = int((time.monotonic() - t0) * 1000)
            _log("PRIMARY-ERR", f"primary unexpected {type(e).__name__} ({stage_label}): {e}")
            _log_error_detail({
                "request_id": request_id, "stage": stage_label,
                "error": f"{type(e).__name__}: {e}", "elapsed_ms": ms,
            })
            attempts.append({"stage": stage_label, "kind": "unexpected", "elapsed_ms": ms, "message": str(e)})
            metrics["primary_error_type"] = "unexpected"
            metrics["primary_elapsed_ms"] = ms
            record_primary_failure()  # R824d: unexpected retryable
            return False
        # success
        result.success = True
        result.resp = resp
        result.conn = conn
        result.upstream_used = "primary"
        result.mapped_model = PRIMARY_UPSTREAM_MODEL
        result.elapsed_ms = int((time.monotonic() - t0) * 1000)
        metrics["upstream_used"] = "primary"
        metrics["mapped_model"] = PRIMARY_UPSTREAM_MODEL
        metrics["key_cycle_details"] = attempts
        record_primary_success()  # R824d: primary healthy -> close circuit
        return True

    # ── Stage 1: primary ── (R824d: circuit breaker — skip primary if OPEN)
    if is_primary_open():
        _log("PRIMARY-BREAKER-SKIP", f"primary skipped (circuit OPEN), going straight to fallback")
        metrics["primary_breaker_skipped"] = True
        r = False
    else:
        r = _try_primary("primary")
        if r is True:
            return result
        if r == "client_4xx":
            return result  # client error, do not fall back

    # ── Stage 2: fallback ──
    oai_body_fb = dict(oai_body)
    oai_body_fb["model"] = FALLBACK_UPSTREAM_MODEL
    t0 = time.monotonic()
    try:
        resp, conn = _call_upstream(
            oai_body_fb, FALLBACK_UPSTREAM_URL, FALLBACK_UPSTREAM_MODEL,
            FALLBACK_UPSTREAM_TOKEN, request_id,
            header_timeout=FALLBACK_HEADER_TIMEOUT,
        )
        result.success = True
        result.resp = resp
        result.conn = conn
        result.upstream_used = "fallback"
        result.mapped_model = FALLBACK_UPSTREAM_MODEL
        result.elapsed_ms = int((time.monotonic() - t0) * 1000)
        metrics["upstream_used"] = "fallback"
        metrics["mapped_model"] = FALLBACK_UPSTREAM_MODEL
        metrics["fallback_triggered"] = True
        metrics["key_cycle_details"] = attempts
        _log("FALLBACK-OK", f"fallback ({FALLBACK_UPSTREAM_MODEL}) connected after primary fail, {result.elapsed_ms}ms")
        return result
    except _UpstreamError as e:
        fb_ms = int((time.monotonic() - t0) * 1000)
        attempts.append({"stage": "fallback", "kind": e.kind, "status": e.status, "elapsed_ms": fb_ms, "message": e.message})
        _log("FALLBACK-FAIL", f"fallback ({FALLBACK_UPSTREAM_MODEL}) {e.kind} status={e.status} after {fb_ms}ms: {e.message[:160]}")
        # R822: retry primary once after fallback fails (primary often recovers faster
        # than a storming fallback). R823: gate on total budget so a simultaneous
        # rate-limit on both upstreams does not amplify to 3x timeout (24s->36s+).
        # If remaining budget < PRIMARY_HEADER_TIMEOUT, skip retry and fail fast.
        elapsed_total = time.monotonic() - t_start_mon
        remaining = CC4101_TOTAL_BUDGET_S - elapsed_total
        if RETRY_PRIMARY_AFTER_FALLBACK and remaining >= PRIMARY_HEADER_TIMEOUT and not is_primary_open():
            r2 = _try_primary("primary_retry")
            if r2 is True:
                metrics["primary_retry_succeeded"] = True
                metrics["fallback_error_type"] = e.kind
                metrics["fallback_elapsed_ms"] = fb_ms
                _log("PRIMARY-RETRY-OK", f"primary retry succeeded after fallback fail (fb {e.kind} {fb_ms}ms), {result.elapsed_ms}ms")
                return result
            if r2 == "client_4xx":
                metrics["fallback_error_type"] = e.kind
                metrics["fallback_elapsed_ms"] = fb_ms
                return result
            metrics["primary_retry_succeeded"] = False
            metrics["fallback_error_type"] = e.kind
            metrics["fallback_elapsed_ms"] = fb_ms
        # final failure -- report fallback error
        result.error_kind = e.kind
        result.error_status = e.status
        result.error_json = e.error_json
        result.error_message = e.message
        result.elapsed_ms = fb_ms
        metrics["upstream_used"] = "fallback"
        metrics["mapped_model"] = FALLBACK_UPSTREAM_MODEL
        metrics["fallback_triggered"] = True
        metrics["key_cycle_details"] = attempts
        return result
    except Exception as e:
        fb_ms = int((time.monotonic() - t0) * 1000)
        _log("FALLBACK-ERR", f"fallback unexpected {type(e).__name__}: {e}")
        _log_error_detail({
            "request_id": request_id, "stage": "fallback",
            "error": f"{type(e).__name__}: {e}", "elapsed_ms": fb_ms,
        })
        attempts.append({"stage": "fallback", "kind": "unexpected", "elapsed_ms": fb_ms, "message": str(e)})
        elapsed_total = time.monotonic() - t_start_mon
        remaining = CC4101_TOTAL_BUDGET_S - elapsed_total
        if RETRY_PRIMARY_AFTER_FALLBACK and remaining >= PRIMARY_HEADER_TIMEOUT and not is_primary_open():
            r2 = _try_primary("primary_retry")
            if r2 is True or r2 == "client_4xx":
                metrics["primary_retry_succeeded"] = (r2 is True)
                return result
        result.error_kind = "unexpected"
        result.error_message = str(e)
        result.elapsed_ms = fb_ms
        metrics["upstream_used"] = "fallback"
        metrics["mapped_model"] = FALLBACK_UPSTREAM_MODEL
        metrics["fallback_triggered"] = True
        metrics["key_cycle_details"] = attempts
        return result
