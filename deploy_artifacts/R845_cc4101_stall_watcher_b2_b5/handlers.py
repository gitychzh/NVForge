#!/usr/bin/env python3
"""cc4101 HTTP handler — Anthropic format only (/v1/messages).

R684: Serves only Claude Code (cc2) on HM2. Anthropic /v1/messages → glm5.2
(nv_gw primary, ms_gw fallback). Always forces upstream stream=true.

Delegation:
  - Upstream primary→fallback  → upstream.py
  - Format conversion          → converters.py (Anthropic↔OpenAI)
  - Streaming                  → stream.py (Anthropic SSE)
  - Error mapping              → error_mapping.py
  - DB logging                 → db.py (async)
"""
import http.server
import json
import os
import time
import datetime
import hmac
import uuid
import urllib.parse

from .config import (
    MODEL_INPUT_TOKEN_SAFETY,
    CHARS_PER_TOKEN_ESTIMATE, CC4101_GATEWAY_API_KEY, AUTH_ENABLED,
    CC_FRONTEND_MODEL, PROXY_ROLE, map_model,
)
from .logger import _log, _log_metrics, _log_error_detail
from .converters import anth_to_openai, _estimate_text_chars
from .stream import stream_to_anth, collect_stream_to_anth
from .error_mapping import (
    convert_error, get_upstream_status_for_client, is_input_overflow,
)
from .upstream import execute_request
from .db import enqueue_metrics


class ProxyHandler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ("/health", "/"):
            self._send_json(200, {
                "status": "ok",
                "proxy_role": PROXY_ROLE,
                "primary": os.environ.get("PRIMARY_UPSTREAM_MODEL", "glm5_2_nv"),
                "fallback": os.environ.get("FALLBACK_UPSTREAM_MODEL", "dsv4p_ms"),
                "port": int(os.environ.get("LISTEN_PORT", "4101")),
            })
        elif parsed.path in ("/v1/models", "/models"):
            self._anthropic_models_list()
        elif parsed.path.startswith("/v1/models/") or parsed.path.startswith("/models/"):
            model_id = parsed.path.split("/models/")[1].strip("/")
            self._anthropic_model_detail(model_id)
        else:
            self._send_json(404, {"error": "not found"})

    def do_HEAD(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ("/health", "/", "/v1/models", "/models") or parsed.path.startswith("/v1/models/") or parsed.path.startswith("/models/"):
            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/v1/messages":
            # Auth check. Claude Code (Anthropic JS SDK) sends `x-api-key: <token>`,
            # NOT `Authorization: Bearer <token>` (OpenAI style). Accept both so CC
            # can actually authenticate. (R690: this was the #1 blocker — CC got 401.)
            if AUTH_ENABLED:
                token = ""
                xkey = self.headers.get("x-api-key", "")
                if xkey:
                    token = xkey.strip()
                if not token:
                    auth = self.headers.get("Authorization", "")
                    if auth.lower().startswith("bearer "):
                        token = auth[7:].strip()
                # R690 cc2 red-team: constant-time compare to avoid timing side-channel
                # on token comparison (defense-in-depth; local-only, but cheap).
                if not hmac.compare_digest(token, CC4101_GATEWAY_API_KEY):
                    self._send_json(401, {"type": "error", "error": {
                        "type": "authentication_error",
                        "message": "invalid or missing API key (expected x-api-key or Bearer cc4101-token)"}})
                    return
            self._handle_messages()
        else:
            self._send_json(404, {"error": {"message": f"cc4101 only serves /v1/messages. Role={PROXY_ROLE}", "type": "invalid_request_error"}})

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    # ─── /v1/messages ───
    def _handle_messages(self):
        t_start = time.time()
        request_id = str(uuid.uuid4())[:8]
        metrics = {
            "request_id": request_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "path": "/v1/messages",
            "proxy_role": PROXY_ROLE,
            "request_model": "?",
            "mapped_model": "?",
            "upstream_used": "?",
            "fallback_triggered": False,
            "is_stream": False,
            "num_messages": 0,
            "num_tools": 0,
            "total_input_chars": 0,
            "ttfb_ms": None,
            "duration_ms": 0,
            "status": 0,
            "finish_reason": None,
            "input_tokens": 0,
            "output_tokens": 0,
            "error_type": None,
            "error_message": None,
            "primary_error_type": None,
            "primary_elapsed_ms": None,
        }

        try:
            length = int(self.headers.get("Content-Length", 0))
            # R690 cc2 red-team: cap request body at 50 MB. CC request bodies are
            # small (system prompt + history + tools), so 50 MB is a generous ceiling
            # that still rejects accidental unbounded reads / memory DoS.
            if length <= 0 or length > 50 * 1024 * 1024:
                self._send_json(413, {"type": "error", "error": {
                    "type": "invalid_request_error",
                    "message": f"request body size {length} out of range (max 50MB)"}})
                metrics["status"] = 413; metrics["error_type"] = "PayloadTooLarge"
                _log("ERROR", f"body size {length} rejected")
                _log_metrics(metrics); enqueue_metrics(metrics)
                return
            raw_body = self.rfile.read(length)
            anth_body = json.loads(raw_body)
        except Exception as e:
            self._send_json(400, {"error": {"message": f"bad request: {e}"}})
            metrics["status"] = 400; metrics["error_type"] = "BadRequest"; metrics["error_message"] = str(e)
            _log("ERROR", f"bad request: {e}")
            _log_metrics(metrics); enqueue_metrics(metrics)
            return

        request_model = anth_body.get("model", CC_FRONTEND_MODEL)
        is_stream = anth_body.get("stream", False)
        metrics["request_model"] = request_model
        metrics["is_stream"] = is_stream

        mapped_model = map_model(request_model)

        # Convert Anthropic → OpenAI. mapped_model becomes the upstream model id.
        oai_body = anth_to_openai(anth_body, target_model=mapped_model)
        metrics["num_messages"] = len(oai_body.get("messages", []))
        metrics["num_tools"] = len(oai_body.get("tools", []))
        text_chars = _estimate_text_chars(oai_body)
        metrics["total_input_chars"] = text_chars
        metrics["estimated_input_tokens"] = int(text_chars / CHARS_PER_TOKEN_ESTIMATE)

        # ─── R684: ALWAYS force upstream stream=true ───
        # glm5.2 non-stream returns empty content / finish_reason=length on both
        # nv_gw (empty200) and ms_gw (content=""). Only stream is reliable.
        # CC stream=true  → stream_to_anth (real-time SSE to CC)
        # CC stream=false → collect_stream_to_anth (collect upstream stream,
        #                  synthesize non-stream Anthropic JSON to CC)
        oai_body["stream"] = True
        oai_body["stream_options"] = {"include_usage": True}
        _log("REQ", f"model={request_model}→{mapped_model} cc_stream={is_stream} "
                    f"msgs={metrics['num_messages']} tools={metrics['num_tools']}")

        # ─── Execute: primary → fallback ───
        result = execute_request(oai_body, request_id, metrics, t_start)

        if not result.success:
            # Upstream error from both stages (or 4xx from primary that we didn't retry).
            err_json = result.error_json or {"error": {"message": result.error_message or "upstream failed"}}
            resp_status = result.error_status or 502

            # Input overflow → invalid_request_error (CC stops, no compact)
            if is_input_overflow(err_json, resp_status):
                _log("INPUT-OVERFLOW", f"400 input overflow → invalid_request_error")
                err_msg = json.dumps(err_json)[:500]
                self._send_json(400, {"type": "error", "error": {
                    "type": "invalid_request_error",
                    "message": f"Input tokens exceed backend limit. Please start a new conversation. Detail: {err_msg}",
                    "model": request_model}})
                metrics["status"] = 400
                metrics["error_type"] = "InputExceedsInvalidRequest"
                metrics["duration_ms"] = int((time.time() - t_start) * 1000)
                _log_metrics(metrics); enqueue_metrics(metrics)
                return

            client_status = get_upstream_status_for_client(resp_status)
            error_payload = convert_error(err_json, request_model)
            extra_hdrs = {"retry-after": "5"} if client_status == 429 else None
            metrics["status"] = client_status
            metrics["error_type"] = result.error_kind or "upstream_error"
            metrics["error_message"] = str(err_json)[:200]
            metrics["duration_ms"] = int((time.time() - t_start) * 1000)
            _log_metrics(metrics); enqueue_metrics(metrics)
            self._send_json(client_status, error_payload, extra_headers=extra_hdrs)
            return

        # ─── Success: stream or collect ───
        resp = result.resp
        conn = result.conn

        if is_stream:
            # Real-time SSE to CC. (If primary produces an empty stream mid-flight,
            # we can't retry — SSE headers already sent. stream_to_anth records
            # empty_stream_response in metrics; CC will retry the whole request.)
            # R845 B5: 兜底 client 早断 (BrokenPipe/ConnectionReset) — stream_to_anth 内部已 close conn,
            # 但若异常从 _send_sse 等路径冒泡到此, handlers 层再兜一次, 确保 conn 不泄漏 + metrics 记录.
            try:
                stream_to_anth(self, resp, request_model, result.mapped_model, conn, metrics, t_start)
            except (BrokenPipeError, ConnectionResetError, OSError) as e:
                _log("ERR", f"client gone mid-stream after {int((time.time()-t_start)*1000)}ms: {e}")
                if not metrics.get("error_type"):
                    metrics["error_type"] = "client_gone_mid_stream"
                if not metrics.get("status"):
                    metrics["status"] = 499
                metrics["duration_ms"] = int((time.time() - t_start) * 1000)
                _log_metrics(metrics)
                try:
                    conn.close()
                except Exception:
                    pass
            enqueue_metrics(metrics)
            return
        else:
            # Collect upstream stream, synthesize non-stream Anthropic JSON.
            # R684: if primary produced an empty stream, we cannot retry on fallback
            # here — collect_stream_to_anth already sent the synthesized response
            # (with empty content) to CC. The empty_stream_response flag is recorded
            # in metrics + error_detail JSONL so the failure is visible; CC will
            # retry the whole request and likely hit fallback on the next attempt
            # (execute_request tries primary first each time, but a persistent
            # primary empty-stream is a real NVCF/glm5.2 issue to investigate
            # via the metrics, not something this proxy can paper over mid-response).
            # R845 B5: 同 stream 路径的 client 早断兜底.
            try:
                collect_stream_to_anth(self, resp, request_model, result.mapped_model, conn, metrics, t_start)
            except (BrokenPipeError, ConnectionResetError, OSError) as e:
                _log("ERR", f"client gone mid-collect after {int((time.time()-t_start)*1000)}ms: {e}")
                if not metrics.get("error_type"):
                    metrics["error_type"] = "client_gone_mid_stream"
                if not metrics.get("status"):
                    metrics["status"] = 499
                metrics["duration_ms"] = int((time.time() - t_start) * 1000)
                _log_metrics(metrics)
                try:
                    conn.close()
                except Exception:
                    pass
            enqueue_metrics(metrics)
            return

    # ─── /v1/models (Anthropic format) ───
    def _anthropic_models_list(self):
        self._send_json(200, {
            "data": [{
                "id": CC_FRONTEND_MODEL,
                "type": "model",
                "display_name": "GLM-5.2 (cc4101)",
                "created_at": "2024-01-01T00:00:00Z",
                "context_window": MODEL_INPUT_TOKEN_SAFETY,
            }],
            "has_more": False,
        })

    def _anthropic_model_detail(self, model_id):
        self._send_json(200, {
            "id": model_id,
            "type": "model",
            "display_name": "GLM-5.2 (cc4101)",
            "created_at": "2024-01-01T00:00:00Z",
            "context_window": MODEL_INPUT_TOKEN_SAFETY,
        })

    # ─── Helpers ───
    def _send_json(self, code, data, extra_headers=None):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self._send_raw(code, body, "application/json", extra_headers)

    def _send_raw(self, code, body_bytes, content_type="application/json", extra_headers=None):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body_bytes)))
        self.send_header("Connection", "close")
        self.close_connection = True
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, str(v))
        self.end_headers()
        self.wfile.write(body_bytes)

    def _send_sse(self, event_type, data_dict):
        data_str = json.dumps(data_dict, ensure_ascii=False)
        msg = f"event: {event_type}\ndata: {data_str}\n\n"
        try:
            self.wfile.write(msg.encode("utf-8"))
            self.wfile.flush()
        except Exception:
            pass

    def log_message(self, fmt, *args):
        pass
