#!/usr/bin/env python3
"""纯 HTTP 传输层 — 从 upstream.py 拆出 (R-modref).

只管: URL 解析, HTTP POST, socket 超时切换, _UpstreamError 异常.
不管: 路由策略, 超时分档, 熔断, fallback, 错误分类.

改网络层 = 只动本文件.
"""
import json
import http.client
import socket
import urllib.parse

from .config import (
    UPSTREAM_TIMEOUT,
    UPSTREAM_HEADER_TIMEOUT,
    CC4101_STREAM_POLL_S,
)
from .logger import _log


class _UpstreamError(Exception):
    """Upstream HTTP error with classification kind for routing logic."""
    def __init__(self, kind, status, error_json, message):
        self.kind = kind          # "client_4xx" | "server_5xx" | "conn" | "timeout"
        self.status = status      # upstream HTTP status (0 for conn/timeout)
        self.error_json = error_json  # upstream error body (dict) — for 4xx
        self.message = message
        super().__init__(message)


def _parse_url(url):
    """Parse upstream URL into (scheme, host, port, path)."""
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path or "/v1/chat/completions"
    if parsed.query:
        path += "?" + parsed.query
    return parsed.scheme, host, port, path


def _restore_read_timeout(conn, read_timeout, resp=None):
    """R822/R853/R-bugfix-E: after response headers arrive, switch the socket
    to timeout=None (infinite blocking). stream.py uses select + deadline to
    control read timing, not socket timeout.

    Old approach set socket timeout=30s, but http.client's BufferedReader fp
    enters "timed out" state after a socket timeout, and subsequent resp.read()
    forever raises "cannot read from timed out object" → dead loop, can't
    receive nv_gw flush data → empty 200 ("模型未返回任何内容").
    """
    try:
        sock = conn.sock
        if sock is None and resp is not None:
            try:
                sock = resp.fp.raw._sock
            except Exception:
                sock = None
        if sock is not None:
            sock.settimeout(None)  # R-bugfix-E: 无限阻塞, stream.py 用 select 控制
            return True
    except Exception:
        pass
    return False


def _call_upstream(oai_body, url, model, token, request_id,
                   timeout=UPSTREAM_TIMEOUT, header_timeout=None,
                   idle_timeout=CC4101_STREAM_POLL_S,
                   caller_tag="cc-via-cc4101"):
    """Make one streaming POST to an upstream. Returns (resp, conn) on HTTP 200,
    or raises _UpstreamError with classification on any failure.

    We do NOT read the body here — the caller streams it. For non-200 we read
    the error body for classification.

    header_timeout: connect + TTFB timeout (caller passes value from
    timeout_strategy.get_primary_header_timeout / get_fallback_header_timeout).
    """
    scheme, host, port, path = _parse_url(url)
    if header_timeout is None:
        header_timeout = min(timeout, UPSTREAM_HEADER_TIMEOUT)

    if scheme == "https":
        conn = http.client.HTTPSConnection(host, port, timeout=header_timeout)
    else:
        conn = http.client.HTTPConnection(host, port, timeout=header_timeout)

    # R1705: 透传 anthropic body (不做 anth→oai 转换, 转换下沉 nv_gw/ms_gw /v1/messages 端点).
    body_bytes = json.dumps(oai_body, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "Accept": "text/event-stream",
        "Connection": "close",
        "anthropic-version": "2023-06-01",
        "X-Caller": caller_tag,  # R1700: 供下游网关日志区分来源
    }
    try:
        conn.request("POST", path, body=body_bytes, headers=headers)
        resp = conn.getresponse()
    except socket.timeout as e:
        try:
            conn.close()
        except Exception:
            pass
        raise _UpstreamError("timeout", 0, None,
                             f"header/ttfb timeout after {header_timeout}s: {e}")
    except (ConnectionRefusedError, ConnectionResetError, OSError,
            http.client.HTTPException) as e:
        try:
            conn.close()
        except Exception:
            pass
        raise _UpstreamError("conn", 0, None, f"{type(e).__name__}: {e}")

    _restore_read_timeout(conn, idle_timeout, resp=resp)

    if resp.status != 200:
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

    return resp, conn
