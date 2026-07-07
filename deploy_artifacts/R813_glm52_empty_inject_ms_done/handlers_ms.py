#!/usr/bin/env python3
"""HTTP handler for ms_gw — /health, /v1/models, /v1/chat/completions.

OpenAI-format passthrough (agents speak OpenAI; no Anthropic conversion).
Stream: 前置错误检查已在 upstream._try_ms_keys 做完 (第一 chunk 已预读),
  handler 直接 send 200 + 透传 (含已预读的 first_chunk) + 后续 chunk.
"""
import http.client
import json
import os
import socket
import ssl
import sys
import time
import uuid
from http.server import BaseHTTPRequestHandler

from .config import (
    LISTEN_HOST, LISTEN_PORT, PROXY_ROLE,
    MS_KEYS, NUM_KEYS, NUM_VARIANTS, MODEL_REGISTRY, DEFAULT_MODEL,
    MS_BASEURL, MSU_GATEWAY_API_KEY, AUTH_ENABLED,
)
from .logger import _log, _log_metrics, _log_error_detail
from .upstream import _try_ms_keys, _sanitize_request_body
from .error_mapping import (
    auth_error, bad_request_error, model_not_found_error,
    all_keys_exhausted_error,
)
from .cooldown import snapshot as cooldown_snapshot
from .rr_counter import _get_rr_counter_snapshot


class ProxyHandler(BaseHTTPRequestHandler):
    # Quiet default access log (we do our own structured logging)
    def log_message(self, fmt, *args):
        pass

    # ─── GET ─────────────────────────────────────────────────────────────
    def do_GET(self):
        from urllib.parse import urlparse
        parsed = urlparse(self.path)
        if parsed.path in ("/health", "/"):
            self._handle_health()
            return
        if parsed.path in ("/v1/models", "/models"):
            self._handle_models()
            return
        self._send_json(404, {"error": {"message": f"Not found: {parsed.path}",
                                        "type": "ms_not_found"}})

    def do_HEAD(self):
        from urllib.parse import urlparse
        parsed = urlparse(self.path)
        if parsed.path in ("/health", "/", "/v1/models", "/models",
                           "/v1/chat/completions", "/chat/completions"):
            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers",
                         "Authorization, Content-Type, X-Caller")
        self.end_headers()

    # ─── POST /v1/chat/completions ───────────────────────────────────────
    def do_POST(self):
        from urllib.parse import urlparse
        parsed = urlparse(self.path)
        if parsed.path in ("/v1/chat/completions", "/chat/completions"):
            self._handle_chat()
            return
        self._send_json(404, {"error": {"message": f"Not found: {parsed.path}",
                                        "type": "ms_not_found"}})

    # ─── /health ─────────────────────────────────────────────────────────
    def _handle_health(self):
        snap = cooldown_snapshot()
        body = {
            "status": "ok" if NUM_KEYS > 0 else "degraded",
            "proxy": "ms_gw",
            "role": PROXY_ROLE,
            "listen": f"{LISTEN_HOST}:{LISTEN_PORT}",
            "num_keys": NUM_KEYS,
            "num_variants": NUM_VARIANTS,
            "models": list(MODEL_REGISTRY.keys()),
            "default_model": DEFAULT_MODEL,
            "ms_baseurl": MS_BASEURL,
            "rr_counters": _get_rr_counter_snapshot(),
            "cooldown": snap,
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self._send_json(200, body)

    # ─── /v1/models ──────────────────────────────────────────────────────
    def _handle_models(self):
        data = []
        for mid, spec in MODEL_REGISTRY.items():
            data.append({
                "id": mid,
                "object": "model",
                "created": 1700000000,
                "owned_by": "ms_gw",
                "name": spec.get("name", mid),
                "context_window": spec.get("context_window", 131072),
                "context_length": spec.get("context_window", 131072),  # R699 BUG-4: OpenAI标准字段名是context_length不是context_window. hermes background_review找context_length找不到→None→默认32768→报32K<64K失败. 加alias让客户端认出真实128K.
                "max_tokens": spec.get("max_tokens", 32768),
                "supports_thinking": spec.get("supports_thinking", False),
                "disabled": spec.get("_disabled", False),
            })
        self._send_json(200, {"object": "list", "data": data})

    # ─── /v1/chat/completions handler ────────────────────────────────────
    def _handle_chat(self):
        t_start = time.monotonic()  # for duration
        t_start_wall = time.time()  # R699 BUG-6: wall clock for ts (monotonic -> 1970)
        request_id = str(uuid.uuid4())[:8]

        # Auth
        if AUTH_ENABLED and not self._check_auth():
            status, err = auth_error()
            self._send_json(status, err)
            return

        # Read body
        try:
            body_len = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            body_len = 0
        try:
            raw = self.rfile.read(body_len) if body_len > 0 else b""
        except Exception as e:
            status, err = bad_request_error(f"read body failed: {e}")
            self._send_json(status, err)
            return

        # Parse
        try:
            req_body = json.loads(raw) if raw else {}
        except Exception as e:
            status, err = bad_request_error(f"invalid JSON: {e}")
            self._send_json(status, err)
            return

        agent_model = req_body.get("model") or DEFAULT_MODEL
        is_stream = bool(req_body.get("stream", False))

        # Caller detection
        user_agent = self.headers.get("User-Agent", "")
        x_caller = self.headers.get("X-Caller", "")
        caller = self._detect_caller(user_agent, x_caller)

        # Model exists?
        spec = MODEL_REGISTRY.get(agent_model)
        if not spec:
            status, err = model_not_found_error(agent_model)
            self._send_json(status, err)
            return
        if spec.get("_disabled"):
            from .error_mapping import model_disabled_error
            status, err = model_disabled_error(agent_model)
            self._send_json(status, err)
            return

        # Sanitize (strip NVCF-style params)
        cleaned_body = _sanitize_request_body(req_body, spec)

        metrics = {
            "request_id": request_id,
            "ts": int(t_start_wall * 1000),
            "caller": caller,
            "agent_model": agent_model,
            "is_stream": is_stream,
            "backend": "ms",
        }

        # Execute with 2D rotation
        result = _try_ms_keys(cleaned_body, agent_model, request_id,
                              metrics, t_start, is_stream)

        if not result.relay:
            # Error path
            status = result.error_status or 502
            err_body = result.error_body or {"error": {"message": "ms_gw: unknown failure"}}
            # Inject cycle attempts for debugging
            if isinstance(err_body, dict) and "error" in err_body:
                err_body["error"]["attempts"] = result.attempts[-5:]
            metrics["status"] = "error"
            metrics["error_status"] = status
            metrics["attempts_count"] = len(result.attempts)
            metrics["duration_ms"] = int((time.monotonic() - t_start) * 1000)
            _log_metrics(metrics)
            self._send_json(status, err_body)
            return

        # Success — relay
        metrics["backend_model"] = result.metrics.get("backend_model")
        metrics["variant_idx"] = result.metrics.get("variant_idx")
        metrics["key_idx"] = result.metrics.get("key_idx")
        metrics["cycle_attempts_before_success"] = len(
            [a for a in result.attempts if "ok" not in a.get("status", "")])

        if is_stream:
            self._relay_stream(result, metrics, t_start, request_id, agent_model)
        else:
            self._relay_nonstream(result, metrics, t_start, request_id, agent_model)

    # ─── Non-stream relay ────────────────────────────────────────────────
    def _relay_nonstream(self, result, metrics, t_start, request_id, agent_model):
        try:
            resp_status = result.metrics.get("_resp_status", 200)
            resp_body = result.metrics.get("_resp_body", b"")
            if isinstance(resp_body, str):
                resp_body = resp_body.encode("utf-8")
            # Rewrite model in body to agent-facing id (so agent sees glm5_2_ms not variant)
            try:
                parsed = json.loads(resp_body)
                if isinstance(parsed, dict):
                    parsed["model"] = agent_model
                    resp_body = json.dumps(parsed, ensure_ascii=False).encode("utf-8")
            except Exception:
                pass  # pass through as-is on parse failure

            self.send_response(resp_status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp_body)))
            self.send_header("X-MS-Backend-Model", result.metrics.get("backend_model", ""))
            self.send_header("X-MS-Variant", str(result.metrics.get("variant_idx", "")))
            self.send_header("X-MS-Key", str(result.metrics.get("key_idx", "")))
            self.send_header("X-MS-Proxy", "ms_gw")
            self.end_headers()
            self.wfile.write(resp_body)

            metrics["status"] = "ok"
            metrics["duration_ms"] = int((time.monotonic() - t_start) * 1000)
            metrics["resp_status"] = resp_status
            _log_metrics(metrics)
        except Exception as e:
            _log("MS-RELAY-ERR", f"req={request_id} nonstream relay: {type(e).__name__}: {e}")
            _log_error_detail({"request_id": request_id, "phase": "nonstream_relay",
                                "error": str(e)})
        finally:
            try:
                if result.conn: result.conn.close()
            except Exception:
                pass

    # ─── Stream relay ────────────────────────────────────────────────────
    def _relay_stream(self, result, metrics, t_start, request_id, agent_model):
        """Relay SSE stream. First chunk already prefetched & validated."""
        first_chunk = result.metrics.get("_first_chunk", b"")
        conn = result.conn
        resp = result.resp
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("X-MS-Backend-Model", result.metrics.get("backend_model", ""))
            self.send_header("X-MS-Variant", str(result.metrics.get("variant_idx", "")))
            self.send_header("X-MS-Key", str(result.metrics.get("key_idx", "")))
            self.send_header("X-MS-Proxy", "ms_gw")
            self.end_headers()

            # Replay prefetched first chunk
            if first_chunk:
                self.wfile.write(first_chunk)
                self.wfile.flush()

            # Stream the rest
            bytes_relayed = len(first_chunk)
            # We may need to rewrite model name in SSE chunks — but rewriting stream
            # chunks inline is fragile (partial JSON across chunks). Skip rewriting
            # for stream; agent gets backend variant name in SSE model field (cosmetic).
            # R797b: ModelScope 上游在 data: [DONE] 后常不关连接, resp.read(8192) 会阻塞到
            # UPSTREAM_TIMEOUT(300s). 转发完 [DONE] 后主动 break, 让下游 (cc4101 collect_stream)
            # 立即收尾, 不再等上游 EOF.
            done_seen = False
            _tail = b""  # 滚动缓冲, 跨 chunk 边界检测 [DONE]
            while not done_seen:
                try:
                    chunk = resp.read(8192)
                except (http.client.IncompleteRead, http.client.RemoteDisconnected,
                        ConnectionResetError, socket.timeout) as e:
                    _log("MS-STREAM-EOF", f"req={request_id} stream ended: {type(e).__name__}")
                    break
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()
                bytes_relayed += len(chunk)
                # 检测 [DONE] (可能跨 chunk 边界, 用滚动 tail 最多 16B)
                _tail = (_tail + chunk)[-16:]
                if b"[DONE]" in _tail:
                    _log("MS-STREAM-DONE", f"req={request_id} forwarded [DONE], closing client stream after {bytes_relayed}b")
                    done_seen = True

            metrics["status"] = "ok"
            metrics["duration_ms"] = int((time.monotonic() - t_start) * 1000)
            metrics["bytes_relayed"] = bytes_relayed
            _log_metrics(metrics)
        except (http.client.RemoteDisconnected, ConnectionResetError,
                BrokenPipeError, OSError) as e:
            _log("MS-STREAM-CLIENT-EOF", f"req={request_id} client disconnected: "
                  f"{type(e).__name__}")
            metrics["status"] = "client_disconnect"
            metrics["duration_ms"] = int((time.monotonic() - t_start) * 1000)
            _log_metrics(metrics)
        except Exception as e:
            _log("MS-STREAM-ERR", f"req={request_id} {type(e).__name__}: {e}")
            _log_error_detail({"request_id": request_id, "phase": "stream_relay",
                                "error": str(e)})
        finally:
            try:
                if conn: conn.close()
            except Exception:
                pass

    # ─── Auth check ──────────────────────────────────────────────────────
    def _check_auth(self):
        """Require Authorization: Bearer <MSU_GATEWAY_API_KEY> or X-Api-Key.
        /health is exempt."""
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:].strip()
            if token == MSU_GATEWAY_API_KEY:
                return True
        xk = self.headers.get("X-Api-Key", "")
        if xk == MSU_GATEWAY_API_KEY:
            return True
        # Allow litellm-local compat (so CC's existing key works for testing)
        if MSU_GATEWAY_API_KEY and xk == "sk-litellm-local":
            return True
        return False

    # ─── Helpers ─────────────────────────────────────────────────────────
    @staticmethod
    def _detect_caller(user_agent, x_caller=""):
        ua = (user_agent or "").lower()
        xc = (x_caller or "").lower()
        if "hermes" in ua or "hermes" in xc:
            return "hermes"
        if "openclaw" in ua or "openclaw" in xc:
            return "openclaw"
        if "opencode" in ua or "opencode" in xc:
            return "opencode"
        if "curl" in ua:
            return "curl"
        return "unknown"

    def _send_json(self, status, body_dict):
        try:
            body = json.dumps(body_dict, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            _log("MS-SEND-ERR", f"_send_json: {type(e).__name__}: {e}")
