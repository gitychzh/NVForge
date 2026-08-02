#!/usr/bin/env python3
"""路由 + 熔断 + fallback + 错误分类 — 从 upstream.py 拆出 (R-modref).

编排: 查熔断 → 选目标 → 调 http_client → 分类结果.
不管: HTTP 传输细节 (在 http_client.py), 超时分档 (在 timeout_strategy.py).

改路由/fallback 策略 = 只动本文件.
"""
import copy
import json
import os
import time

from .config import (
    PRIMARY_UPSTREAM_URL, PRIMARY_UPSTREAM_MODEL, PRIMARY_UPSTREAM_TOKEN,
    FALLBACK_UPSTREAM_URL, FALLBACK_UPSTREAM_MODEL, FALLBACK_UPSTREAM_TOKEN,
    FORCE_FALLBACK_MODEL,
)
from .logger import _log, _log_error_detail
from .circuit import is_primary_open, record_primary_success, record_primary_failure
from .http_client import _call_upstream, _UpstreamError
from .timeout_strategy import get_primary_header_timeout, get_fallback_header_timeout


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


def _should_record_primary_failure(error_kind, elapsed_ms):
    """R1602: 区分"cc4101 自抢超时" vs "nv_gw 真坏".

    仅当 (a) nv_gw 明确返回 5xx, 或 (b) timeout 但耗时已 > CHAIN_BUDGET_S
    (说明 nv_gw 跑完 chain 仍没好, 真坏), 或 (c) conn/unexpected 才计数.
    header 超时且耗时 < CHAIN_BUDGET_S 大概率是 cc4101 抢断, 不计数.
    """
    _CHAIN_BUDGET_S = int(os.environ.get("CC4101_CHAIN_BUDGET_S", "450"))
    return (
        error_kind == "server_5xx"
        or (error_kind == "timeout" and elapsed_ms > _CHAIN_BUDGET_S * 1000)
        or error_kind not in ("timeout", "server_5xx")
    )


def execute_request(anth_body, request_id, metrics, t_start,
                    header_timeout_override=None):
    """Try primary (nv_gw glm5_2_nv); on retryable failure try fallback (ms_gw glm5_2_ms).

    R854 曾删 fallback; R1643 加回(末位兜底, nv 不限额优先, ms 限额仅兜底):
      - primary circuit OPEN -> 直走 fallback(省 nv 超时, 不每条等 60-120s).
      - CLOSED 时 primary 先试; 5xx/conn/timeout 失败 -> 立即试 fallback 一次.
      - client_4xx 不 fallback(请求级错误, ms 也会 4xx).
      - fallback 成败不计 breaker(breaker 只盯 primary 健康).
    R1705: anth_body 实为原始 anthropic body (cc4101 不再做 anth→oai 转换, 透传给 nv_gw/ms_gw
    /v1/messages 端点, 转换下沉). 仅 model 字段在 _try_primary/_try_fallback 内改写做路由.
    """
    result = UpstreamResult()
    attempts = []  # for metrics
    t_start_mon = time.monotonic()  # R823: total-budget baseline across stages

    def _try_primary(stage_label):
        """One primary attempt. Returns True on success, client_4xx for
        non-retryable client errors, False for retryable failures."""
        t0 = time.monotonic()
        try:
            _hdr_to = get_primary_header_timeout(anth_body, header_timeout_override)
            # R1705: 深拷贝 anth_body 改写 model 做路由 (claude-*→glm5_2_nv), 透传其余.
            _pri_body = copy.copy(anth_body)
            _pri_body["model"] = PRIMARY_UPSTREAM_MODEL
            # R2254obs: 观测点 — 打印 _hdr_ic 实际值 + 落档 + 最终 header_timeout.
            _nm = len(anth_body.get("messages", [])) if isinstance(anth_body, dict) else 0
            _nt = len(anth_body.get("tools", [])) if isinstance(anth_body, dict) else 0
            _log("R2254-OBS", f"primary req={request_id} hdr_to={_hdr_to} msgs={_nm} tools={_nt}")
            resp, conn = _call_upstream(
                _pri_body, PRIMARY_UPSTREAM_URL, PRIMARY_UPSTREAM_MODEL,
                PRIMARY_UPSTREAM_TOKEN, request_id,
                header_timeout=_hdr_to,
                caller_tag="cc4101-primary",
            )
        except _UpstreamError as e:
            ms = int((time.monotonic() - t0) * 1000)
            attempts.append({"stage": stage_label, "kind": e.kind, "status": e.status,
                             "elapsed_ms": ms, "message": e.message})
            metrics["primary_error_type"] = e.kind
            metrics["primary_elapsed_ms"] = ms
            _log("PRIMARY-FAIL", f"primary ({PRIMARY_UPSTREAM_MODEL}) {e.kind} status={e.status} "
                f"after {ms}ms ({stage_label}): {e.message[:160]}")
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
            # R1602: 区分 cc4101 自抢超时 vs nv_gw 真坏 (见 _should_record_primary_failure)
            if _should_record_primary_failure(e.kind, ms):
                record_primary_failure()
            else:
                _log("PRIMARY-FAIL-SKIP-CIRCUIT",
                    f"primary {e.kind} after {ms}ms < chain budget, "
                    f"likely cc4101 pre-empted nv_gw retry, NOT counted toward circuit "
                    f"(req={request_id})")
            # R2417: set error_kind so downstream sees the correct kind.
            result.error_kind = e.kind
            result.error_message = e.message
            result.elapsed_ms = ms
            metrics["upstream_used"] = "primary"
            metrics["mapped_model"] = PRIMARY_UPSTREAM_MODEL
            metrics["key_cycle_details"] = attempts
            return False  # retryable: server_5xx / conn / timeout
        except Exception as e:
            ms = int((time.monotonic() - t0) * 1000)
            _log("PRIMARY-ERR", f"primary unexpected {type(e).__name__} ({stage_label}): {e}")
            _log_error_detail({
                "request_id": request_id, "stage": stage_label,
                "error": f"{type(e).__name__}: {e}", "elapsed_ms": ms,
            })
            attempts.append({"stage": stage_label, "kind": "unexpected",
                            "elapsed_ms": ms, "message": str(e)})
            metrics["primary_error_type"] = "unexpected"
            metrics["primary_elapsed_ms"] = ms
            record_primary_failure()
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
        # R849: connect 成功不再 record_primary_success. 移到 stream.py 真正流式成功完成时.
        return True

    def _try_fallback(stage_label):
        """R1643: One fallback (ms_gw glm5_2_ms) attempt. 成败都不计 breaker.
        Returns True on success, False on failure(result 已填好 error_*)."""
        if not FALLBACK_UPSTREAM_URL:
            return False  # fallback disabled (R854 行为)
        t0 = time.monotonic()
        try:
            _fb_body = copy.copy(anth_body)
            _fb_body["model"] = FALLBACK_UPSTREAM_MODEL
            _hdr_to = get_fallback_header_timeout(_fb_body, header_timeout_override)
            resp, conn = _call_upstream(
                _fb_body, FALLBACK_UPSTREAM_URL, FALLBACK_UPSTREAM_MODEL,
                FALLBACK_UPSTREAM_TOKEN, request_id,
                header_timeout=_hdr_to,
                caller_tag="cc4101-fallback",
            )
        except _UpstreamError as e:
            ms = int((time.monotonic() - t0) * 1000)
            attempts.append({"stage": stage_label, "kind": e.kind, "status": e.status,
                             "elapsed_ms": ms, "message": e.message})
            _log("FALLBACK-FAIL", f"fallback ({FALLBACK_UPSTREAM_MODEL}) {e.kind} status={e.status} "
                f"after {ms}ms: {e.message[:160]}")
            result.error_kind = e.kind
            result.error_status = e.status
            result.error_json = e.error_json
            result.error_message = e.message
            result.elapsed_ms = ms
            metrics["upstream_used"] = "fallback"
            metrics["mapped_model"] = FALLBACK_UPSTREAM_MODEL
            metrics["key_cycle_details"] = attempts
            return False
        except Exception as e:
            ms = int((time.monotonic() - t0) * 1000)
            _log("FALLBACK-ERR", f"fallback unexpected {type(e).__name__}: {e}")
            _log_error_detail({"request_id": request_id, "stage": stage_label,
                "error": f"{type(e).__name__}: {e}", "elapsed_ms": ms})
            attempts.append({"stage": stage_label, "kind": "unexpected",
                            "elapsed_ms": ms, "message": str(e)})
            result.error_kind = "unexpected"
            result.error_message = str(e)
            result.elapsed_ms = ms
            metrics["upstream_used"] = "fallback"
            metrics["mapped_model"] = FALLBACK_UPSTREAM_MODEL
            metrics["key_cycle_details"] = attempts
            return False
        # fallback success
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
        _log("FALLBACK-OK", f"fallback ({FALLBACK_UPSTREAM_MODEL}) succeeded after "
            f"{result.elapsed_ms}ms (req={request_id})")
        return True

    # -- Stage -1 (R1712-force-fb): 客户端指定 FORCE_FALLBACK_MODEL -> 跳过 primary 直走 ms_gw.
    if FORCE_FALLBACK_MODEL and anth_body.get("model") == FORCE_FALLBACK_MODEL:
        _log("FORCE-FALLBACK", f"client model={FORCE_FALLBACK_MODEL} -> skip primary, "
            f"go straight to ms_gw (req={request_id})")
        metrics["force_fallback"] = True
        if _try_fallback("fallback(forced)"):
            return result
        _log("FALLBACK-FAIL", f"forced fallback also failed ({result.error_kind}) -> "
            f"returning error, CC will retry (req={request_id})")
        return result

    # -- Stage 0: circuit OPEN? R1643 改为直走 fallback(不再 fast-fail 503) --
    if is_primary_open():
        _log("PRIMARY-BREAKER-OPEN", f"primary circuit OPEN -> go straight to fallback "
            f"ms_gw glm5_2_ms (req={request_id})")
        metrics["primary_breaker_skipped"] = True
        if _try_fallback("fallback(circuit-open)"):
            return result
        return result

    # -- Stage 1: primary nv_gw glm5_2_nv --
    r = _try_primary("primary")
    if r is True:
        return result
    if r == "client_4xx":
        return result  # client error, do not fallback

    # -- Stage 2 (R1643): primary retryable 失败 -> 立即试 fallback 一次 --
    _log("PRIMARY-FAIL", f"primary failed ({result.error_kind or 'unknown'}) -> "
        f"trying fallback ms_gw glm5_2_ms (req={request_id})")
    if _try_fallback("fallback"):
        return result
    _log("FALLBACK-FAIL", f"fallback also failed ({result.error_kind}) -> "
        f"returning error, CC will retry (req={request_id})")
    return result
