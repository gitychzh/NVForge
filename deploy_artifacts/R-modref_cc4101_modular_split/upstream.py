#!/usr/bin/env python3
"""upstream.py — deprecated (R-modref).

代码已拆为 3 个模块:
  - http_client.py    纯 HTTP 传输 (_call_upstream, _parse_url, _restore_read_timeout, _UpstreamError)
  - timeout_strategy.py  超时分档 (get_primary_header_timeout, get_fallback_header_timeout)
  - routing.py         路由 + 熔断 + fallback + 错误分类 (execute_request, UpstreamResult)

本文件保留 re-export 兼容旧 import:
    from .upstream import execute_request, UpstreamResult
"""
from .routing import execute_request, UpstreamResult
from .http_client import _call_upstream, _UpstreamError, _parse_url, _restore_read_timeout
from .timeout_strategy import get_primary_header_timeout, get_fallback_header_timeout

__all__ = [
    "execute_request", "UpstreamResult",
    "_call_upstream", "_UpstreamError", "_parse_url", "_restore_read_timeout",
    "get_primary_header_timeout", "get_fallback_header_timeout",
]
