#!/usr/bin/env python3
"""Upstream request executor for NV proxy (nv_gw) — 三 agent 通用.

Reng (HM1 self-change, authorized): modularized for long-term maintainability.
NVCF connection layer → gateway/nvcf_conn.py; pexec request
construction/validation → gateway/pexec.py. This file now holds the core
tier-key loop (_try_tier_keys) and three-tier fallback orchestration
(execute_request). Logic is byte-for-byte equivalent to the pre-refactor
version.

Rproxy (HM1 self-change, authorized): per-key direct/proxy routing is driven
purely by NVU_PROXY_URL<n> env (empty=direct, non-empty=mihomo SOCKS5).
k2/k4 direct, k1/k3/k5 via mihomo on HM1. _make_nvcf_proxy_conn (in nvcf_conn.py)
handles the empty→direct branch internally, so the unified call below routes
both paths.

R38.10: deepseek bypasses DEGRADING integrate API → NVCF pexec orion (ACTIVE).
R38.8:  Connection refused fast-break + startup retry.
R38.6:  sock.settimeout BEFORE getresponse, Connection:close.

Default tier: deepseek (primary) + kimi (fallback)
If all 5 keys fail → fallback to next tier.
If all tiers also all-fail → ABORT-NO-FALLBACK.

Chain: nv_gw → NVCF pexec (deepseek/kimi only). K1/K2 direct, K3-K5 via mihomo SOCKS5 → NV API
"""
import json
import os
import http.client
import socket
import threading
import time
import datetime

from .config import (
    NVU_KEYS, NVU_NUM_KEYS, NVU_PROXY_URLS,
    NV_MODEL_IDS, NV_MODEL_TIERS, DEFAULT_NV_MODEL, detect_nv_model,
    get_tier_index,
    NVCF_PEXEC_MODELS, NVCF_BASE_URL,
    UPSTREAM_TIMEOUT, TIER_TIMEOUT_BUDGET_S, NVU_FORCE_STREAM_UPGRADE_TIMEOUT,
    _next_nv_key,
    throttle_outbound,
    is_key_cooling, mark_key_cooling, reset_key429_count,
    KEY_COOLDOWN_S,
    TIER_COOLDOWN_S,
    is_key_auth_failed, mark_key_auth_failed,
    is_tier_degraded, mark_tier_degraded,
    NV_INTEGRATE_ENABLED, NV_INTEGRATE_HOST, NV_INTEGRATE_PATH,
    NV_INTEGRATE_KEY_COOLDOWN_S, NV_INTEGRATE_PATH_COOLDOWN_S, NV_INTEGRATE_MODELS,
    NV_INTEGRATE_PROXY_URLS,
    NV_KEY_INTEGRATE_PROXY_URLS, NV_KEY_INTEGRATE_EGRESS_IPS,
    NV_INTEGRATE_EGRESS_IPS,
    nv_key_integrate_keys_for,
    egress_info_for_integrate_key,
    egress_info_for_key,
    _peek_nv_key,
    FALLBACK_GRAPH, FALLBACK_HEALTH_THRESHOLD,
    NV_GLM52_MODE_CHAIN, NV_GLM52_SINGLE_US_PROXY, NV_GLM52_RR_US_PROXIES,
    glm52_current_mode_idx, glm52_save_mode_idx, glm52_reset_mode_idx,
)
from .logger import _log, _log_metrics, _log_error_detail
from .nvcf_conn import _make_nvcf_proxy_conn
from .pexec import _build_pexec_body, _check_empty_200
from . import func_health


class UpstreamResult:
    """Result from NVCF pexec upstream request execution."""
    def __init__(self):
        self.success = False
        # Success fields
        self.resp = None
        self.conn = None
        self.tier_model = ""
        self.nv_key_idx = 0
        self.nv_model_label = ""
        self.is_stream = False
        # R784: per-key egress info for DB long-term IP-diversity analysis
        self.egress_route = ""
        self.egress_ip = ""
        self.key_cycle_attempts = []
        self.upstream_type = "nvcf_pexec"
        self.tier_attempts = []
        self.fallback_tiers_used = []
        # R_multi: 本次 tier 选中的 function_id (用于上层 func_health.record_result)
        self.function_id = ""
        # R832f: NVCF per-request trace id (integrate 响应头 Nvcf-Reqid; pexec 同头).
        #   resp 传给上层后会被流式消费, 故在成功分支内立即抓 header 存此处.
        self.nvcf_reqid = ""
        # Error fields
        self.all_keys_exhausted = False
        self.all_429 = False
        self.empty_200 = False
        self.elapsed_ms = 0
        self.final_error_json = None
        self.final_resp_status = 0


# ─── R572: Integrate direct path (5-key 首选, pexec 降为 fallback) ──────────
# 实测 integrate.api.nvidia.com/v1/chat/completions 比 pexec 快 2-3x 且无 surge,
# 但单 key 有 ~6-12/min 的 per-key RPM 限流 (冷却 1-2min). 策略:
#   5 key 独立 rr 轮换 (不与 pexec 的 _next_nv_key 共用 counter) →
#   遇 429 标该 key 冷却 (NV_INTEGRATE_KEY_COOLDOWN_S) 立即跳下一 key →
#   全限流 → 标整条 path 冷却 (NV_INTEGRATE_PATH_COOLDOWN_S) 返回 all_keys_exhausted,
#   由 execute_request 回退到 pexec tier.
# 思考参数复用 NVCF_PEXEC_MODELS[model]["inject"] (integrate 与 pexec 74f02205 触发方式一致).
_integrate_rr_counter = 0  # 模块级独立 rr, 不持久化 (重启从 0 开始, 无害)
_integrate_rr_lock = threading.Lock()
_integrate_path_cooldown_until = 0.0  # 整条 integrate path 冷却截止 (全 key 429 时触发)

# R858/R1421 (port from HM2): rr_us 模式跨请求持久 RR 计数器. 修 BUG6: 旧 rr_us 用 per-request
# attempt_idx 致每请求首 attempt 永远取 pool[0]=7894, 7894 压倒性过载(实测 13:1)致 SSL 断流高发.
_glm52_rr_us_counter = 0
_glm52_rr_us_lock = threading.Lock()


def _integrate_is_path_cooling():
    return time.monotonic() < _integrate_path_cooldown_until


def _integrate_mark_path_cooling(duration_s):
    global _integrate_path_cooldown_until
    _integrate_path_cooldown_until = time.monotonic() + duration_s


def _integrate_tier_name(tier_model):
    """虚拟 tier 名, 隔离 cooldown 状态 (不与 pexec 同 model 的 cooldown 混)."""
    return f"{tier_model}_integrate"


def _try_integrate_keys(oai_body, tier_model, request_id, metrics, t_start,
                        is_stream, prior_cycle_attempts, upstream_timeout_override=None,
                        key_filter=None):
    """Try all 5 keys via integrate.api.nvidia.com direct path, starting from independent RR.

    镜像 _try_tier_keys 结构但走 integrate /v1/chat/completions 路径.
    - 成功 (200 非空): 返回 success
    - 429: 标该 key 冷却 (NV_INTEGRATE_KEY_COOLDOWN_S), 立即跳下一 key
    - 连接错误/timeout: 跳下一 key (不 fast-break, integrate 偶发抖动)
    - 全 key 失败: 返回 all_keys_exhausted, 由 execute_request 回退 pexec
    """
    global _integrate_rr_counter
    result = UpstreamResult()
    result.is_stream = is_stream
    result.tier_model = tier_model
    result.upstream_type = "nv_integrate"
    result.function_id = "integrate"  # func_health 不追踪 integrate (无 function id)
    key_cycle_attempts = list(prior_cycle_attempts)

    nv_model_id = NV_MODEL_IDS[tier_model]
    nvcf_config = NVCF_PEXEC_MODELS[tier_model]
    integ_tier = _integrate_tier_name(tier_model)

    # 复用 _build_pexec_body: 它做 strip_params + inject (thinking:{type:enabled} 等),
    # integrate 路径接受同样的 body 格式 (已实测 200 + rc 非空).
    integ_body = _build_pexec_body(oai_body, tier_model, nvcf_config)
    integ_data = json.dumps(integ_body).encode("utf-8")

    # R838: per-key 跨链路. key_filter 指定只试这些 key(如 [4]=K5), 不做全 5 key 轮转.
    # 无 key_filter → 沿用全 key RR (NV_INTEGRATE_MODELS per-model 行为).
    if key_filter is not None:
        _iter_keys = [k for k in key_filter if 0 <= k < NVU_NUM_KEYS]
        start_key_idx = _iter_keys[0] if _iter_keys else 0
        _log("NV-INTEGRATE", f"Starting integrate tier={tier_model} model={nv_model_id} "
                             f"key_filter={[k+1 for k in _iter_keys]} path={NV_INTEGRATE_PATH}")
    else:
        with _integrate_rr_lock:
            start_key_idx = _integrate_rr_counter % NVU_NUM_KEYS
            _integrate_rr_counter += 1
        _log("NV-INTEGRATE", f"Starting integrate tier={tier_model} model={nv_model_id} "
                             f"start_key=k{start_key_idx+1} path={NV_INTEGRATE_PATH}")

    CONNECT_RESERVE_S = float(os.environ.get("NVU_CONNECT_RESERVE_S", "5"))
    MIN_ATTEMPT_TIMEOUT = 5
    consecutive_pexec_timeout = 0
    consecutive_empty_200 = 0  # R577: 连续 empty_200 计数, 触达阈值则 break
    # R830c (2026-07-09, HM1 self): integrate 专属 fastbreak 阈值, 解绑 pexec.
    # 专家评审(glm5.2+dsv4p共识): fastbreak=1 对 integrate 极不合理 — 单 key 超时大概率是 thinking 慢
    # (40-71s), 不代表 key 坏; 放弃 k3/k4/k5 等同把单点慢思考放大成全局故障. 但 NVU_PEXEC_TIMEOUT_FASTBREAK
    # 是 integrate+pexec 共用全局参数, 直接调会连累 dsv4p/kimi 的 pexec 精调. 故给 integrate 独立 env:
    # NVU_INTEGRATE_TIMEOUT_FASTBREAK (默认回退 NVU_PEXEC_TIMEOUT_FASTBREAK, 向后兼容); pexec 路径
    # (line ~501 _try_tier_keys) 仍读原 env, 不受影响.
    PEXEC_TIMEOUT_FASTBREAK = int(os.environ.get('NVU_INTEGRATE_TIMEOUT_FASTBREAK',
                                                 os.environ.get('NVU_PEXEC_TIMEOUT_FASTBREAK', '3')))
    EMPTY_200_FASTBREAK = int(os.environ.get("NVU_EMPTY_200_FASTBREAK", "1"))

    # R830b (2026-07-09): integrate 专属 thinking timeout override.
    # 背景: handlers.py 对 thinking 请求传 upstream_timeout_override=NVU_FORCE_STREAM_UPGRADE_TIMEOUT (=66s),
    # 但该 env 是 integrate + pexec 两条路径共用, 放宽它会让 pexec(dsv4p/kimi 的失败兜底)也跟着晚放弃.
    # 而实际只有 glm5_2_nv integrate 需要: 抓包+metrics 实测 glm5.2 thinking 成功请求 max=71.3s p95=62.4s,
    # 66s 上限太紧, 偶发慢一点的请求(如 67475ms)就被砍成 timeout → fastbreak=1 放弃整 tier → 切 pexec(对
    # glm5.2 全 empty200, R832d 定论)→ 级联到 ms_gw 也 56s timeout → 飞书 lane 120s 杀 → "回答一句卡住".
    # 新增 NVU_INTEGRATE_THINKING_TIMEOUT_S (默认回退到传入 override, 即不改变行为); 设置后仅 integrate 路径用.
    # pexec 路径 (line ~517) 仍用原 override, 不受影响.
    _integ_thinking_to = os.environ.get("NVU_INTEGRATE_THINKING_TIMEOUT_S")
    if _integ_thinking_to:
        try:
            upstream_timeout_override = float(_integ_thinking_to)
        except ValueError:
            pass

    tier_budget_start = time.time()
    # R835: integrate 路径 per-model tier budget override (复用 pexec line 492 模式).
    # 背景: minimax_m3_nv reasoning_effort=high 实测 ~156s, 但全局 TIER_TIMEOUT_BUDGET_S=112s
    # 会砍掉 → 502. pexec 路径早有 NVU_TIER_BUDGET_{model} override, integrate 路径之前没有 (line
    # 186/191/242 直接用全局). 给 integrate 也加上, 让 minimax 等慢思考模型能独立放宽, 不影响 glm5.2.
    _integ_tier_budget_env = os.environ.get(f"NVU_TIER_BUDGET_{tier_model.upper()}")
    tier_budget_s = float(_integ_tier_budget_env) if _integ_tier_budget_env else TIER_TIMEOUT_BUDGET_S

    _filter_keys = [k for k in (key_filter if key_filter is not None else []) if 0 <= k < NVU_NUM_KEYS]
    _n_iter = len(_filter_keys) if _filter_keys else (NVU_NUM_KEYS + 2)
    for attempt_idx in range(_n_iter):
        key_idx = (_filter_keys[attempt_idx] if _filter_keys
                   else (start_key_idx + attempt_idx) % NVU_NUM_KEYS)
        t_attempt_start = time.time()

        elapsed_in_tier = time.time() - tier_budget_start
        if elapsed_in_tier >= tier_budget_s:
            _log("NV-INTEGRATE-BUDGET", f"tier={tier_model} budget {tier_budget_s}s "
                                        f"exceeded after {elapsed_in_tier:.1f}s, breaking")
            break

        remaining_budget = tier_budget_s - elapsed_in_tier
        if remaining_budget < MIN_ATTEMPT_TIMEOUT:
            break
        per_attempt_timeout = max(MIN_ATTEMPT_TIMEOUT,
                                  min(upstream_timeout_override if upstream_timeout_override else UPSTREAM_TIMEOUT,
                                      remaining_budget - CONNECT_RESERVE_S))

        # 跳过冷却中的 key (per-key 429 冷却)
        # R764: skip if cooling (429) OR auth-failed (cross-tier per-key)
        if is_key_cooling(integ_tier, key_idx) or is_key_auth_failed(key_idx):
            _log("NV-INTEGRATE", f"tier={tier_model} k{key_idx+1} cooling/auth-failed, skipping")
            if attempt_idx >= NVU_NUM_KEYS and all(is_key_cooling(integ_tier, k) or is_key_auth_failed(k) for k in range(NVU_NUM_KEYS)):
                _log("NV-INTEGRATE", f"tier={tier_model} all integrate keys in cooldown/auth-failed, breaking")
                break
            continue

        if NVU_NUM_KEYS == 0 or key_idx >= len(NVU_KEYS):
            continue

        nv_key = NVU_KEYS[key_idx]
        # R827: integrate 走专用美国代理(per-key轮换, 地理限制), 不复用 pexec 的 NVU_PROXY_URLS.
        # R838: key_filter 模式优先用 NV_KEY_INTEGRATE_PROXY_URLS (对齐 key_filter 顺序),
        #       否则按 key_idx 轮换 NV_INTEGRATE_PROXY_URLS, 再否则回退 pexec 的 NVU_PROXY_URLS.
        if key_filter is not None and NV_KEY_INTEGRATE_PROXY_URLS:
            _ki_in_filter = _filter_keys.index(key_idx) if key_idx in _filter_keys else 0
            proxy_url = (NV_KEY_INTEGRATE_PROXY_URLS[_ki_in_filter]
                        if _ki_in_filter < len(NV_KEY_INTEGRATE_PROXY_URLS)
                        else (NV_INTEGRATE_PROXY_URLS[key_idx % len(NV_INTEGRATE_PROXY_URLS)] if NV_INTEGRATE_PROXY_URLS else ""))
        elif NV_INTEGRATE_PROXY_URLS:
            proxy_url = NV_INTEGRATE_PROXY_URLS[key_idx % len(NV_INTEGRATE_PROXY_URLS)]
        else:
            proxy_url = NVU_PROXY_URLS[key_idx] if key_idx < len(NVU_PROXY_URLS) else ""
        is_direct = (not proxy_url) or (proxy_url.strip() == "")

        # throttle: 第一次出站前节流 (复用全局 throttle, 分摊 per-key 压力)
        if attempt_idx == 0:
            throttle_outbound()

        _log("NV-INTEGRATE", f"tier={tier_model} attempt {attempt_idx+1}/{NVU_NUM_KEYS + 2}: "
                             f"k{key_idx+1} → integrate {nv_model_id} {'DIRECT' if is_direct else 'via ' + proxy_url}")

        # 复用 R295 header camouflage (与 pexec 一致, 风格统一)
        hdr_extra = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "application/json, text/plain, */*",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": "https://build.nvidia.com",
            "Referer": "https://build.nvidia.com/explore/discover",
        }
        headers_out = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {nv_key}",
            "Content-Length": str(len(integ_data)),
            "Connection": "close",
            **hdr_extra,
        }

        try:
            t_connect_start = time.time()
            conn = _make_nvcf_proxy_conn(proxy_url, nvcf_host=NV_INTEGRATE_HOST, timeout=per_attempt_timeout)
            connect_elapsed = time.time() - t_connect_start
            post_connect_remaining = tier_budget_s - (time.time() - tier_budget_start)
            if post_connect_remaining < MIN_ATTEMPT_TIMEOUT:
                _log("NV-INTEGRATE-BUDGET", f"tier={tier_model} k{key_idx+1} after connect "
                                            f"({connect_elapsed:.1f}s) remaining {post_connect_remaining:.1f}s, aborting")
                try: conn.close()
                except Exception: pass
                break
            read_timeout = min(per_attempt_timeout, post_connect_remaining)
            conn.request("POST", NV_INTEGRATE_PATH, body=integ_data, headers=headers_out)
            if conn.sock:
                conn.sock.settimeout(read_timeout)
            resp = conn.getresponse()

            if resp.status >= 400:
                error_body = resp.read()
                try: error_json = json.loads(error_body)
                except Exception: error_json = {"error": error_body.decode("utf-8", errors="replace")}
                conn.close()
                err_str = json.dumps(error_json)

                # R762: 401/403 (per-key auth failed) → cycle next key (同 pexec 修复).
                should_cycle = resp.status in (401, 403, 429, 408, 500, 502, 503, 504, 202)
                if should_cycle:
                    cycle_reason = ("400_integrate_degraded" if resp.status == 400 else
                                    "401_integrate_auth_failed" if resp.status == 401 else
                                    "403_integrate_auth_failed" if resp.status == 403 else
                                    "429_integrate_rate_limit" if resp.status == 429 else
                                    "408_integrate_timeout" if resp.status == 408 else
                                    "500_integrate_error" if resp.status == 500 else
                                    "502_integrate_error" if resp.status == 502 else
                                    "503_integrate_error" if resp.status == 503 else
                                    "504_integrate_gateway_timeout" if resp.status == 504 else "202_integrate_async_hang")
                    key_cycle_attempts.append({
                        "tier": tier_model,
                        "nv_key_idx": key_idx,
                        "litellm_model": f"integrate_{nv_model_id}_k{key_idx+1}",
                        "error_body": err_str[:500],
                        "error_type": cycle_reason,
                        "upstream_type": "nv_integrate",
                        "function_id": "integrate",
                    })
                    if resp.status in (401, 403):
                        # R764: auth-fail 是 per-key (跨 tier), 用 mark_key_auth_failed 全 tier 跳过.
                        mark_key_cooling(integ_tier, key_idx, duration_s=NV_INTEGRATE_KEY_COOLDOWN_S)
                        mark_key_auth_failed(key_idx)
                        _log("NV-INTEGRATE-AUTH-FAIL", f"tier={tier_model} k{key_idx+1} {resp.status} auth failed, "
                               f"marked cooling + auth-fail (cross-tier), cycling")
                    elif resp.status == 429:
                        mark_key_cooling(integ_tier, key_idx, duration_s=NV_INTEGRATE_KEY_COOLDOWN_S)
                        _log("NV-INTEGRATE-COOLDOWN", f"tier={tier_model} k{key_idx+1} marked cooling {NV_INTEGRATE_KEY_COOLDOWN_S}s after 429")
                    _log("NV-INTEGRATE-CYCLE", f"tier={tier_model} k{key_idx+1} → {resp.status} ({cycle_reason}), cycling")
                    consecutive_pexec_timeout = 0
                    continue

                # Non-cycling error → report (与 pexec 一致, R762 加日志)
                _log("NV-INTEGRATE-NONCYCLE-ERR", f"tier={tier_model} k{key_idx+1} resp.status={resp.status} "
                      f"non-cycling, aborting tier. body={err_str[:200]}")
                result.final_error_json = error_json
                result.final_resp_status = resp.status
                result.key_cycle_attempts = key_cycle_attempts
                result.elapsed_ms = int((time.time() - t_start) * 1000)
                return result

            # 200 — check empty
            is_empty = _check_empty_200(resp, key_idx, tier_model, is_stream)
            if is_empty:
                key_cycle_attempts.append({
                    "tier": tier_model,
                    "nv_key_idx": key_idx,
                    "litellm_model": f"integrate_{nv_model_id}_k{key_idx+1}",
                    "error_type": "empty_200",
                    "upstream_type": "nv_integrate",
                    "function_id": "integrate",
                })
                _log("NV-INTEGRATE-EMPTY", f"tier={tier_model} k{key_idx+1} empty 200, cycling")
                # R577: EMPTY_200_FASTBREAK 语义从 boolean 改为连续次数阈值.
                #   0 = 禁用 (全 cycle, 偶发 empty 可换 key 救回但 surge 期 143s 卡死)
                #   1 = 每次 empty 都 break (激进, 丢失偶发救回)
                #   N≥2 = 连续 N 次 empty 才 break (平衡: 偶发 1-2 次仍 cycle 救回, surge N+ 次快速 break)
                consecutive_empty_200 += 1
                if EMPTY_200_FASTBREAK > 0 and consecutive_empty_200 >= EMPTY_200_FASTBREAK:
                    _log("NV-INTEGRATE-EMPTY-FASTBREAK", f"tier={tier_model} {consecutive_empty_200} consecutive empty_200 ≥ threshold {EMPTY_200_FASTBREAK}, fast-break")
                    break
                consecutive_pexec_timeout = 0
                try: conn.close()
                except Exception: pass
                continue

            # Valid success
            consecutive_pexec_timeout = 0
            consecutive_empty_200 = 0  # R577: 成功重置连续 empty 计数
            result.success = True
            result.resp = resp
            result.conn = conn
            result.tier_model = tier_model
            result.nv_key_idx = key_idx
            # R838: 用实际请求的 proxy_url 算 egress (key_filter 模式下可能是 NV_KEY_INTEGRATE_PROXY_URLS).
            _eg_port = proxy_url.strip().rsplit(":", 1)[-1] if proxy_url and ":" in proxy_url else "direct"
            result.egress_route = f"integrate-mihomo-{_eg_port}" if not is_direct else "integrate-direct"
            if key_filter is not None and NV_KEY_INTEGRATE_EGRESS_IPS and key_idx in _filter_keys:
                _fi = _filter_keys.index(key_idx)
                result.egress_ip = NV_KEY_INTEGRATE_EGRESS_IPS[_fi] if _fi < len(NV_KEY_INTEGRATE_EGRESS_IPS) else ""
            else:
                _, result.egress_ip = egress_info_for_integrate_key(key_idx)
            result.nv_model_label = f"integrate_{nv_model_id}_k{key_idx+1}"
            result.key_cycle_attempts = key_cycle_attempts
            result.fallback_tiers_used = [tier_model]
            result.upstream_type = "nv_integrate"
            # R832f: 抓 Nvcf-Reqid 落库 (resp 即将被上层流式消费, 必须在此刻取)
            try:
                result.nvcf_reqid = (resp.getheader("Nvcf-Reqid") or "").strip() or ""
            except Exception:
                result.nvcf_reqid = ""
            reset_key429_count(integ_tier, key_idx)
            metrics["upstream_type"] = "nv_integrate"
            metrics["tier_model"] = tier_model
            metrics["nv_key_idx"] = key_idx
            metrics["litellm_model"] = result.nv_model_label
            if key_cycle_attempts:
                metrics["key_cycle_429s_before_success"] = len(key_cycle_attempts)
                _log("NV-INTEGRATE-SUCCESS", f"tier={tier_model} k{key_idx+1} succeeded after "
                                              f"{len(key_cycle_attempts)} cycle attempts")
            else:
                _log("NV-INTEGRATE-SUCCESS", f"tier={tier_model} k{key_idx+1} succeeded on first attempt")
            return result

        except socket.timeout as e:
            attempt_elapsed_ms = int((time.time() - t_attempt_start) * 1000)
            _log("NV-INTEGRATE-TIMEOUT", f"tier={tier_model} k{key_idx+1} integrate timeout: "
                                          f"attempt={attempt_elapsed_ms}ms")
            key_cycle_attempts.append({
                "tier": tier_model,
                "nv_key_idx": key_idx,
                "litellm_model": f"integrate_{nv_model_id}_k{key_idx+1}",
                "error_type": "IntegrateTimeout",
                "elapsed_ms": attempt_elapsed_ms,
                "upstream_type": "nv_integrate",
                "function_id": "integrate",
            })
            consecutive_pexec_timeout += 1
            if consecutive_pexec_timeout >= PEXEC_TIMEOUT_FASTBREAK:
                _log("NV-INTEGRATE-FASTBREAK", f"tier={tier_model} {consecutive_pexec_timeout} "
                                               f"consecutive timeouts -> fast-break")
                break
            continue

        except (ConnectionRefusedError, http.client.RemoteDisconnected) as e:
            attempt_elapsed_ms = int((time.time() - t_attempt_start) * 1000)
            _log("NV-INTEGRATE-CONN", f"tier={tier_model} k{key_idx+1} connection error: {e}")
            key_cycle_attempts.append({
                "tier": tier_model,
                "nv_key_idx": key_idx,
                "litellm_model": f"integrate_{nv_model_id}_k{key_idx+1}",
                "error_type": f"Integrate{type(e).__name__}",
                "elapsed_ms": attempt_elapsed_ms,
                "upstream_type": "nv_integrate",
                "function_id": "integrate",
            })
            continue

        except Exception as e:
            error_class = type(e).__name__
            elapsed_ms = int((time.time() - t_attempt_start) * 1000)
            _log("NV-INTEGRATE-ERR", f"tier={tier_model} k{key_idx+1} {error_class}: {e}")
            is_ssl_err = (error_class == "SSLEOFError" or error_class == "SSLError" or
                          error_class == "SSLZeroReturnError")
            if is_ssl_err:
                _log("NV-INTEGRATE-SSL-CYCLE", f"tier={tier_model} k{key_idx+1} SSL error ({elapsed_ms}ms) — cycle")
                continue
            key_cycle_attempts.append({
                "tier": tier_model,
                "nv_key_idx": key_idx,
                "litellm_model": f"integrate_{nv_model_id}_k{key_idx+1}",
                "error": str(e)[:200],
                "error_type": f"Integrate{error_class}",
                "elapsed_ms": elapsed_ms,
                "upstream_type": "nv_integrate",
                "function_id": "integrate",
            })
            continue

    # ─── All integrate keys exhausted ───
    tier_attempts = [a for a in key_cycle_attempts if a.get("tier") == tier_model]
    all_429 = all(a.get("error_type") == "429_integrate_rate_limit" for a in tier_attempts) if tier_attempts else False

    result.all_keys_exhausted = True
    result.all_429 = all_429
    result.empty_200 = False
    result.key_cycle_attempts = key_cycle_attempts
    result.elapsed_ms = int((time.time() - t_start) * 1000)

    fail_summary = (f"429={sum(1 for a in tier_attempts if a.get('error_type')=='429_integrate_rate_limit')}, "
                    f"empty200={sum(1 for a in tier_attempts if a.get('error_type')=='empty_200')}, "
                    f"timeout={sum(1 for a in tier_attempts if 'Timeout' in a.get('error_type',''))}, "
                    f"other={sum(1 for a in tier_attempts if a.get('error_type') not in ('429_integrate_rate_limit','empty_200') and 'Timeout' not in a.get('error_type',''))}")
    _log("NV-INTEGRATE-FAIL", f"tier={tier_model} all integrate keys failed: {fail_summary}, "
                               f"elapsed={result.elapsed_ms}ms")

    # 全 key 429 → 标整条 integrate path 冷却, 强制走 pexec
    if all_429:
        _integrate_mark_path_cooling(NV_INTEGRATE_PATH_COOLDOWN_S)
        _log("NV-INTEGRATE-PATH-COOLDOWN", f"tier={tier_model} all integrate keys 429. "
                                            f"Marking integrate path cooling {NV_INTEGRATE_PATH_COOLDOWN_S}s")

    _log_error_detail({
        "request_id": request_id,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "error_subcategory": f"integrate_{tier_model}_all_keys_failed",
        "tier_model": tier_model,
        "tier_attempts": tier_attempts,
        "all_429": all_429,
        "elapsed_ms": result.elapsed_ms,
    })

    return result


def _try_tier_keys(oai_body, tier_model, request_id, metrics, t_start,
                   is_stream, prior_cycle_attempts, upstream_timeout_override=None):
    """Try all 5 keys within one tier via NVCF pexec, starting from current RR position.

    R38.12: ALL models use NVCF pexec. No LiteLLM branch.
    On 429/500/502: cycle to next key within same tier.
    On empty 200: cycle to next key within same tier.
    On other error: report immediately (no cycling).
    Connection refused fast-break: 2+ consecutive → break to next tier.
    Tier timeout budget: stop if cumulative time exceeds budget.

    Returns: UpstreamResult
    """
    result = UpstreamResult()
    result.is_stream = is_stream
    result.tier_model = tier_model
    # R_multi: 记录本次选中的 function_id, 供上层 func_health.record_result 使用
    result.function_id = ""
    key_cycle_attempts = list(prior_cycle_attempts)


    nv_model_id = NV_MODEL_IDS[tier_model]
    nvcf_config = NVCF_PEXEC_MODELS[tier_model]
    nvcf_host = NVCF_BASE_URL
    # R_multi: 从候选列表 function_ids 中按健康度选首选. surge 中的 function 自动跳过.
    _candidates = nvcf_config.get("function_ids") or [nvcf_config.get("function_id")]
    function_id = func_health.select_healthy_function(tier_model, _candidates)
    result.function_id = function_id
    nvcf_path = f"/v2/nvcf/pexec/functions/{function_id}"

    _log("NV-TIER", f"Starting tier={tier_model} model={nv_model_id} "
                    f"func={function_id[:12]}... (position from rr_counter)")

    # Build request body with per-model param stripping
    pexec_body = _build_pexec_body(oai_body, tier_model, nvcf_config)

    # Get starting key from per-tier persistent counter
    start_key_idx = _next_nv_key(tier_model)

    # R797: per-tier budget override. NVCF ai-glm-5_2 (3b9748d8) DEGRADING — 全 key
    # 直连 504/400 ~62s, 全局 TIER_TIMEOUT_BUDGET_S=180 让 glm5_2_nv 烧满 3 key 才 fail,
    # 把 cc4101/cx4102/opclaw4103 卡死 ~180s. 给 glm5_2_nv 短 budget (env, 默认 70s) 让它
    # 1-2 key 后即 all_tiers_exhausted → agent 尽快落 ms_gw. dsv4p_nv/kimi_nv 不受影响
    # (无 env 覆盖 → 用全局 TIER_TIMEOUT_BUDGET_S). NVCF 恢复后删 env 即回滚.
    _tier_budget_env = os.environ.get(f"NVU_TIER_BUDGET_{tier_model.upper()}")
    tier_budget_s = float(_tier_budget_env) if _tier_budget_env else TIER_TIMEOUT_BUDGET_S

    tier_budget_start = time.time()
    consecutive_conn_err = 0
    CONN_ERR_FAST_BREAK = 2
    # R347 (HM1-C): consecutive NVCFPexecTimeout fast-fail. After N consecutive pexec
    # timeouts in the same tier, break early instead of cycling remaining keys — saves
    # ~30-50s on doomed ATE requests. Default N=3 (per CC directive: front-3 keys all
    # NVCFPexecTimeout). Env-tunable for rollback. Rescue cases (k4/k5 save after 3+ timeouts)
    # are rare (2/231=0.87% in R347 baseline) — accepted per stability>success tradeoff eval.
    consecutive_pexec_timeout = 0
    PEXEC_TIMEOUT_FASTBREAK = int(os.environ.get('NVU_PEXEC_TIMEOUT_FASTBREAK', '3'))

    EMPTY_200_FASTBREAK = int(os.environ.get("NVU_EMPTY_200_FASTBREAK", "1"))
    consecutive_empty_200 = 0  # R577: 连续 empty_200 计数 (同 _try_integrate_keys)
    for attempt_idx in range(NVU_NUM_KEYS + 2):
        key_idx = (start_key_idx + attempt_idx) % NVU_NUM_KEYS
        t_attempt_start = time.time()  # R38.14: per-attempt start time for accurate logging

        # Tier timeout budget check (before each attempt)
        elapsed_in_tier = time.time() - tier_budget_start
        if elapsed_in_tier >= tier_budget_s:
            _log("NV-TIER-BUDGET", f"tier={tier_model} budget {tier_budget_s}s "
                                    f"exceeded after {elapsed_in_tier:.1f}s, breaking")
            break

        # R38.14: per-attempt timeout respects remaining budget
        # R40 A2: reserve CONNECT_RESERVE_S for SOCKS5 connect+SSL handshake (2-5s observed).
        #   Pre-R40 bug: per_attempt_timeout = min(45, remaining) ignored connect time, so
        #   attempt 1 spent 45s(read)+3s(connect)=48s but budget thought only 45s elapsed;
        #   attempt 2 then got remaining=15s, spent 3s(connect)+15s(read)=18s → total 66s,
        #   ~74s with throttle/overhead, blowing past the 60s budget and showing as 74.2s
        #   in the 502 error. Reserve keeps the read timeout within true remaining budget.
        CONNECT_RESERVE_S = float(os.environ.get("NVU_CONNECT_RESERVE_S", "5"))
        remaining_budget = tier_budget_s - elapsed_in_tier
        MIN_ATTEMPT_TIMEOUT = 5  # R45: 10→5 — 10s 下限在 budget 被前次 timeout 吃掉后误杀后续 key (NVCF 实测 p50=3s); 5s 仍保留 dooming-attempt 保护 # Don't attempt if less than 10s budget remains (doomed attempt)
        if remaining_budget < MIN_ATTEMPT_TIMEOUT:
            _log("NV-TIER-BUDGET", f"tier={tier_model} budget {tier_budget_s}s "
                                    f"remaining {remaining_budget:.1f}s < {MIN_ATTEMPT_TIMEOUT}s minimum, breaking")
            break
        # Read timeout = min(UPSTREAM_TIMEOUT, remaining - CONNECT_RESERVE) so connect+read together stay in budget
        per_attempt_timeout = max(MIN_ATTEMPT_TIMEOUT,
                                  min(upstream_timeout_override if upstream_timeout_override else UPSTREAM_TIMEOUT, remaining_budget - CONNECT_RESERVE_S))

        # Skip keys in 429 cooldown OR auth-failed (R764: per-key cross-tier)
        if is_key_cooling(tier_model, key_idx) or is_key_auth_failed(key_idx):
            _log("NV-KEY", f"tier={tier_model} k{key_idx+1} is in cooldown/auth-failed, skipping")
            if attempt_idx >= NVU_NUM_KEYS and all(is_key_cooling(tier_model, k) or is_key_auth_failed(k) for k in range(NVU_NUM_KEYS)):
                _log("NV-TIER", f"tier={tier_model} all keys in cooldown/auth-failed, breaking")
                break
            continue

        # ─── NVCF pexec request ───
        if NVU_NUM_KEYS == 0 or key_idx >= len(NVU_KEYS):
            _log("NV-PEXEC-ERR", f"tier={tier_model} k{key_idx+1} no NV key/proxy configured")
            key_cycle_attempts.append({
                "tier": tier_model,
                "nv_key_idx": key_idx,
                "error_type": "nvcf_pexec_no_key",
                "upstream_type": "nvcf_pexec",
                "function_id": function_id,
            })
            continue

        nv_key = NVU_KEYS[key_idx]
        # ─ Rproxy: per-key proxy strategy driven by NVU_PROXY_URL<n> env ─
        # empty proxy_url → DIRECT (k2/k4 on HM1); non-empty → mihomo SOCKS5 (k1/k3/k5).
        # _make_nvcf_proxy_conn handles the empty→direct branch internally.
        proxy_url = NVU_PROXY_URLS[key_idx] if key_idx < len(NVU_PROXY_URLS) else ""
        is_direct = (not proxy_url) or (proxy_url.strip() == "")

        # Build per-attempt request (model field already set in pexec_body)
        pexec_data = json.dumps(pexec_body).encode("utf-8")

        _log("NV-KEY", f"tier={tier_model} attempt {attempt_idx+1}/{NVU_NUM_KEYS + 2}: "
                       f"k{key_idx+1} → NVCF pexec {function_id[:12]}... {'DIRECT' if is_direct else 'via ' + proxy_url}")

        # R295-port (HM1 self-change, authorized): HTTP header camouflage for NVCF
        # fingerprint bypass. Ported from HM2 R295. HM2 applies it to key_idx in (0,4)
        # (k1/k5, which are the mihomo-proxied keys on HM2). On HM1 the user elected to
        # apply camouflage to ALL keys (k1-k5) for maximum disguise — so this is
        # unconditional, no key_idx guard. Mirrors HM2's exact 6 headers:
        # User-Agent (browser), Origin/Referer (build.nvidia.com source),
        # X-Requested-With, Accept-Language, Accept.
        hdr_extra = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "application/json, text/plain, */*",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": "https://build.nvidia.com",
            "Referer": "https://build.nvidia.com/explore/discover",
        }
        headers_out = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {nv_key}",
            "Content-Length": str(len(pexec_data)),
            "Connection": "close",
            **hdr_extra,
        }

        try:
            # Throttle before making connection (SOCKS5 connect is a real outbound)
            if attempt_idx == 0:
                throttle_outbound()
            t_connect_start = time.time()
            # Rproxy: _make_nvcf_proxy_conn routes DIRECT when proxy_url empty, else mihomo.
            conn = _make_nvcf_proxy_conn(proxy_url, nvcf_host=nvcf_host, timeout=per_attempt_timeout)
            connect_elapsed = time.time() - t_connect_start
            # R40 A2: re-check budget AFTER connect — connect time wasn't counted when
            # computing per_attempt_timeout above, so a slow connect may have eaten the budget.
            post_connect_remaining = tier_budget_s - (time.time() - tier_budget_start)
            if post_connect_remaining < MIN_ATTEMPT_TIMEOUT:
                _log("NV-TIER-BUDGET", f"tier={tier_model} k{key_idx+1} after connect "
                                        f"({connect_elapsed:.1f}s) remaining {post_connect_remaining:.1f}s "
                                        f"< {MIN_ATTEMPT_TIMEOUT}s, aborting attempt")
                try:
                    conn.close()
                except Exception:
                    pass
                key_cycle_attempts.append({
                    "tier": tier_model,
                    "nv_key_idx": key_idx,
                    "litellm_model": f"nvcf_{NV_MODEL_IDS[tier_model]}_k{key_idx+1}",
                    "error_type": "budget_exhausted_after_connect",
                    "elapsed_ms": int(connect_elapsed * 1000),
                    "upstream_type": "nvcf_pexec",
                    "function_id": function_id,
                })
                break
            # Read timeout = whatever remains in the budget, capped by per_attempt_timeout
            read_timeout = min(per_attempt_timeout, post_connect_remaining)
            conn.request("POST", nvcf_path, body=pexec_data, headers=headers_out)
            # R38.6 CRITICAL FIX: sock.settimeout() BEFORE getresponse()
            # R40 A2: use read_timeout (post-connect remaining) instead of per_attempt_timeout
            if conn.sock:
                conn.sock.settimeout(read_timeout)
            resp = conn.getresponse()

            if resp.status >= 400:
                error_body = resp.read()
                try:
                    error_json = json.loads(error_body)
                except Exception:
                    error_json = {"error": error_body.decode("utf-8", errors="replace")}
                conn.close()
                err_str = json.dumps(error_json)

                consecutive_conn_err = 0

                # R762: 401/403 (per-key auth failed) → cycle next key (NOT abort).
                #   根因: k3 NVAPI key 失效返回 403 Forbidden, 命中 Non-cycling 分支直接 return,
                #   放弃整 request, 不 cycle k4/k5 (它们 200 OK). 1 key 失效=整 502, peer-fb 兜底.
                #   401/403 是 per-key 授权问题, 不是 request 问题, 应 cycle 到下一 key.
                #   标 KEY_COOLDOWN_S 避免反复试失效 key (浪费 ~1s/次).
                should_cycle = resp.status in (401, 403, 429, 408, 500, 502, 503, 504, 202)
                if should_cycle:
                    cycle_reason = "400_nvcf_degraded" if resp.status == 400 else \
                                   "401_nv_auth_failed" if resp.status == 401 else \
                                   "403_nv_auth_failed" if resp.status == 403 else \
                                   "429_nv_rate_limit" if resp.status == 429 else \
                                   "408_nvcf_timeout" if resp.status == 408 else \
                                   "500_nv_error" if resp.status == 500 else \
                                   "502_nv_error" if resp.status == 502 else \
                                   "503_nv_error" if resp.status == 503 else \
                                   "504_nv_gateway_timeout" if resp.status == 504 else "202_nv_async_hang"
                    key_cycle_attempts.append({
                        "tier": tier_model,
                        "nv_key_idx": key_idx,
                        "litellm_model": f"nvcf_{NV_MODEL_IDS[tier_model]}_k{key_idx+1}",
                        "error_body": err_str[:500],
                        "error_type": cycle_reason,
                        "upstream_type": "nvcf_pexec",
                        "function_id": function_id,
                    })
                    if resp.status in (401, 403):
                        # R764: auth-fail 是 per-key (跨 tier), 用 mark_key_auth_failed 全 tier 跳过.
                        mark_key_cooling(tier_model, key_idx)
                        mark_key_auth_failed(key_idx)
                        _log("NV-AUTH-FAIL", f"tier={tier_model} k{key_idx+1} {resp.status} auth failed, "
                                              f"marked cooling + auth-fail (cross-tier), cycling to next key")
                    elif resp.status == 429:
                        mark_key_cooling(tier_model, key_idx)
                        _log("NV-COOLDOWN", f"tier={tier_model} k{key_idx+1} marked cooling after 429")
                    _log("NV-CYCLE", f"tier={tier_model} k{key_idx+1} \u2192 "
                                     f"{resp.status} ({cycle_reason}), cycling to next key")
                    consecutive_pexec_timeout = 0  # R347: reset (429/500/502/401/403 != timeout)
                    continue

                # Non-cycling error → report (R762: 加日志, 避免静默失败)
                _log("NV-NONCYCLE-ERR", f"tier={tier_model} k{key_idx+1} resp.status={resp.status} "
                                          f"non-cycling, aborting tier (no key cycle). body={err_str[:200]}")
                result.final_error_json = error_json
                result.final_resp_status = resp.status
                result.key_cycle_attempts = key_cycle_attempts
                result.elapsed_ms = int((time.time() - t_start) * 1000)
                return result

            # ─── 200 response — check for empty ───
            is_empty = _check_empty_200(resp, key_idx, tier_model, is_stream)

            if is_empty:
                key_cycle_attempts.append({
                    "tier": tier_model,
                    "nv_key_idx": key_idx,
                    "litellm_model": f"nvcf_{NV_MODEL_IDS[tier_model]}_k{key_idx+1}",
                    "error_type": "empty_200",
                    "upstream_type": "nvcf_pexec",
                    "function_id": function_id,
                })
                # R832: empty200 按 429 语义处理 — 标 key 冷却, 下次 RR 跳过, 不让空响应上浮到 agent.
                # 对称行 648 (429 mark_key_cooling). 复用 429 计数器 (指数退避封顶30s 或 KEY_COOLDOWN_S).
                mark_key_cooling(tier_model, key_idx)
                _log("NV-EMPTY-CYCLE", f"tier={tier_model} k{key_idx+1} empty 200, marked cooling + cycling")
                # R577: 同 _try_integrate_keys, EMPTY_200_FASTBREAK 语义改为连续次数阈值
                consecutive_empty_200 += 1
                if EMPTY_200_FASTBREAK > 0 and consecutive_empty_200 >= EMPTY_200_FASTBREAK:
                    _log("NV-EMPTY-FASTBREAK", f"tier={tier_model} {consecutive_empty_200} consecutive empty_200 ≥ threshold {EMPTY_200_FASTBREAK}, fast-break (saved remaining keys)")
                    break
                consecutive_pexec_timeout = 0  # R347: reset (empty_200 != timeout)
                try:
                    conn.close()
                except Exception:
                    pass
                continue

            # ─── Valid success response ───
            consecutive_conn_err = 0
            consecutive_pexec_timeout = 0  # R347: reset on success
            consecutive_empty_200 = 0  # R577: reset on success
            result.success = True
            result.resp = resp
            result.conn = conn
            result.tier_model = tier_model
            result.nv_key_idx = key_idx
            result.egress_route, result.egress_ip = egress_info_for_key(key_idx)
            result.nv_model_label = f"nvcf_{NV_MODEL_IDS[tier_model]}_k{key_idx+1}"
            result.key_cycle_attempts = key_cycle_attempts
            result.fallback_tiers_used = [tier_model]
            result.upstream_type = "nvcf_pexec"
            # R832f: 抓 Nvcf-Reqid 落库 (pexec 响应同样带此头)
            try:
                result.nvcf_reqid = (resp.getheader("Nvcf-Reqid") or "").strip() or ""
            except Exception:
                result.nvcf_reqid = ""
            reset_key429_count(tier_model, key_idx)
            metrics["upstream_type"] = "nvcf_pexec"
            metrics["tier_model"] = tier_model
            metrics["nv_key_idx"] = key_idx
            metrics["litellm_model"] = result.nv_model_label
            if key_cycle_attempts:
                metrics["key_cycle_429s_before_success"] = len(key_cycle_attempts)
                metrics["key_cycle_details"] = key_cycle_attempts
                _log("NV-SUCCESS", f"tier={tier_model} k{key_idx+1} succeeded after "
                                    f"{len(key_cycle_attempts)} cycle attempts")
            else:
                _log("NV-SUCCESS", f"tier={tier_model} k{key_idx+1} succeeded on first attempt")
            return result

        except socket.timeout as e:
            # R38.14: use per-attempt elapsed, not request-level t_start
            attempt_elapsed_ms = int((time.time() - t_attempt_start) * 1000)
            total_elapsed_ms = int((time.time() - t_start) * 1000)
            _log("NV-TIMEOUT", f"tier={tier_model} k{key_idx+1} NVCF pexec timeout: "
                               f"attempt={attempt_elapsed_ms}ms total={total_elapsed_ms}ms")
            key_cycle_attempts.append({
                "tier": tier_model,
                "nv_key_idx": key_idx,
                "litellm_model": f"nvcf_{NV_MODEL_IDS[tier_model]}_k{key_idx+1}",
                "error_type": "NVCFPexecTimeout",
                "elapsed_ms": attempt_elapsed_ms,  # R38.14: per-attempt elapsed, not total
                "upstream_type": "nvcf_pexec",
                "function_id": function_id,
            })
            consecutive_pexec_timeout += 1  # R347 (HM1-C): track consecutive pexec timeouts
            if consecutive_pexec_timeout >= PEXEC_TIMEOUT_FASTBREAK:
                _log("NV-PEXEC-FASTBREAK", f"tier={tier_model} {consecutive_pexec_timeout} consecutive "
                                          f"NVCFPexecTimeout -> fast-break (saved remaining keys)")
                break
            continue

        except (ConnectionRefusedError, http.client.RemoteDisconnected) as e:
            attempt_elapsed_ms = int((time.time() - t_attempt_start) * 1000)  # R38.14
            _log("NV-CONN", f"tier={tier_model} k{key_idx+1} connection error: {e}")
            consecutive_conn_err += 1
            key_cycle_attempts.append({
                "tier": tier_model,
                "nv_key_idx": key_idx,
                "litellm_model": f"nvcf_{NV_MODEL_IDS[tier_model]}_k{key_idx+1}",
                "error_type": f"NVCFPexec{type(e).__name__}",
                "elapsed_ms": attempt_elapsed_ms,
                "upstream_type": "nvcf_pexec",
                "function_id": function_id,
            })
            if consecutive_conn_err >= CONN_ERR_FAST_BREAK:
                _log("NV-CONN-BREAK", f"tier={tier_model} {consecutive_conn_err} consecutive "
                                       f"connection errors → fast-break")
                break
            continue

        except Exception as e:
            error_class = type(e).__name__
            elapsed_ms = int((time.time() - t_attempt_start) * 1000)  # R38.14: per-attempt
            _log("NV-ERR", f"tier={tier_model} k{key_idx+1} {error_class}: {e}")

            # R1: SSLEOFError/SSLError/SSLZeroReturnError — mihomo/NVCF SSL hiccup (read-stage EOF
            # after NVCF侧 reset, 已观测单次吃 31s budget).
            # F-fix (2026-07-01, cc2 三轮仲裁): 不重试同 key, 直接 cycle 下一 key.
            #   原逻辑 sleep 3s + continue (注释"retry SAME key"实为下一 key, 注释错误).
            #   sleep 3s 纯浪费 tier budget; 同 mihomo 出口(k3/k4 都走 7896)持续 SSL error,
            #   重试同出口必败还倒贴 sleep. 切 DIRECT key(k2/k5)可能秒成功, 既省 sleep 又换出口.
            #   把 budget 留给后续 key, 也顺带给单 tier 内更多 key 重试机会.
            is_ssl_err = (error_class == "SSLEOFError" or error_class == "SSLError" or
                         error_class == "SSLZeroReturnError")
            if is_ssl_err:
                _log("NV-SSL-CYCLE", f"tier={tier_model} k{key_idx+1} SSL error ({elapsed_ms}ms) — "
                                     f"cycle to next key (no same-key retry, F-fix saves budget)")
                continue  # cycle to next key — 不 sleep, 不重试同 key

            if "gaierror" in error_class.lower() or "socket" in error_class.lower():
                consecutive_conn_err += 1
                if consecutive_conn_err >= CONN_ERR_FAST_BREAK:
                    _log("NV-CONN-BREAK", f"tier={tier_model} {consecutive_conn_err} consecutive "
                                           f"DNS/socket errors → fast-break")
                    key_cycle_attempts.append({
                        "tier": tier_model,
                        "nv_key_idx": key_idx,
                        "litellm_model": f"nvcf_{NV_MODEL_IDS[tier_model]}_k{key_idx+1}",
                        "error": str(e)[:200],
                        "error_type": f"NVCFPexec{error_class}",
                        "elapsed_ms": elapsed_ms,
                        "upstream_type": "nvcf_pexec",
                        "function_id": function_id,
                    })
                    break
            key_cycle_attempts.append({
                "tier": tier_model,
                "nv_key_idx": key_idx,
                "litellm_model": f"nvcf_{NV_MODEL_IDS[tier_model]}_k{key_idx+1}",
                "error": str(e)[:200],
                "error_type": f"NVCFPexec{error_class}",
                "elapsed_ms": elapsed_ms,
                "upstream_type": "nvcf_pexec",
                "function_id": function_id,
            })
            continue

    # ─── All keys in this tier exhausted ───
    tier_attempts = [a for a in key_cycle_attempts if a.get("tier") == tier_model]
    all_429 = all(a.get("error_type") == "429_nv_rate_limit" for a in tier_attempts)
    all_empty = all(a.get("error_type") == "empty_200" for a in tier_attempts)

    result.all_keys_exhausted = True
    result.all_429 = all_429
    result.empty_200 = all_empty
    result.key_cycle_attempts = key_cycle_attempts
    result.elapsed_ms = int((time.time() - t_start) * 1000)

    fail_summary = f"429={sum(1 for a in tier_attempts if a.get('error_type')=='429_nv_rate_limit')}, " \
                   f"empty200={sum(1 for a in tier_attempts if a.get('error_type')=='empty_200')}, " \
                   f"timeout={sum(1 for a in tier_attempts if 'Timeout' in a.get('error_type',''))}, " \
                   f"other={sum(1 for a in tier_attempts if a.get('error_type') not in ('429_nv_rate_limit','empty_200') and 'Timeout' not in a.get('error_type',''))}"
    _log("NV-TIER-FAIL", f"tier={tier_model} all {NVU_NUM_KEYS} keys failed: {fail_summary}, "
                          f"elapsed={result.elapsed_ms}ms")

    if all_429:
        for k in range(NVU_NUM_KEYS):
            mark_key_cooling(tier_model, k, duration_s=int(TIER_COOLDOWN_S))
        _log("NV-GLOBAL-COOLDOWN", f"tier={tier_model} all keys 429. Marking all cooling {TIER_COOLDOWN_S:.0f}s (TIER_COOLDOWN)")
    # R832: all_empty 也按 all_429 语义标 tier 冷却, 触发 tier 级 fallback (glm5_2_nv→ms_gw 同模型).
    # 空响应不上浮到 agent, 在 nv_gw 就吸收掉.
    elif all_empty:
        for k in range(NVU_NUM_KEYS):
            mark_key_cooling(tier_model, k, duration_s=int(TIER_COOLDOWN_S))
        _log("NV-GLOBAL-COOLDOWN", f"tier={tier_model} all keys empty_200. Marking all cooling {TIER_COOLDOWN_S:.0f}s (R832 EMPTY200=TIER_COOLDOWN)")

    _log_error_detail({
        "request_id": request_id,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "error_subcategory": f"tier_{tier_model}_all_keys_failed",
        "tier_model": tier_model,
        "tier_attempts": tier_attempts,
        "all_429": all_429,
        "all_empty_200": all_empty,
        "elapsed_ms": result.elapsed_ms,
    })

    return result


# ─── R839/R1421: glm5_2_nv mode chain (port from HM2, 3 funcs) ────────
def _glm52_resolve_proxy(ip_strategy, attempt_idx):
    """Resolve proxy_url for a given ip_strategy. R839."""
    if ip_strategy == "direct":
        return ""
    if ip_strategy == "single_us":
        single = NV_GLM52_SINGLE_US_PROXY
        if single:
            return single
        # fallback: first of NV_INTEGRATE_PROXY_URLS (7894→193 on both hosts)
        return NV_INTEGRATE_PROXY_URLS[0] if NV_INTEGRATE_PROXY_URLS else ""
    if ip_strategy == "rr_us":
        pool = NV_GLM52_RR_US_PROXIES if NV_GLM52_RR_US_PROXIES else NV_INTEGRATE_PROXY_URLS
        if not pool:
            return ""
        # R858 BUG6: 跨请求持久 RR(分散负载, 不集中 7894) + 同请求内 fault 重试偏移(attempt_idx).
        # 旧代码 pool[attempt_idx % len] 用 per-request 序号, 每请求从 0 起, 首次 attempt 永远 7894.
        global _glm52_rr_us_counter
        with _glm52_rr_us_lock:
            _rr_idx = _glm52_rr_us_counter
            _glm52_rr_us_counter += 1
        return pool[(_rr_idx + attempt_idx) % len(pool)]
    return ""


def _glm52_single_attempt(oai_body, tier_model, request_id, metrics, t_start,
                           is_stream, key_idx, mode_name, channel, proxy_url,
                           all_attempts, upstream_timeout_override):
    """Issue ONE NVCF request: fixed key_idx + fixed mode-driven proxy_url. R839.

    Mirrors the per-attempt block of _try_tier_keys / _try_integrate_keys but:
      - key_idx is FIXED (caller controls which key via RR + mode progression)
      - proxy_url is driven by the current mode (direct / single_us / rr_us)
      - channel in {pexec, integrate} picks endpoint (NVCF pexec vs integrate.api)
    Returns UpstreamResult (success=True + resp/conn on 200-non-empty; else
    failure with key_cycle_attempts appended + appropriate cooldown marking).
    """
    result = UpstreamResult()
    result.is_stream = is_stream
    result.tier_model = tier_model
    result.upstream_type = "nvcf_pexec" if channel == "pexec" else "nv_integrate"
    result.function_id = "integrate" if channel == "integrate" else ""

    nv_model_id = NV_MODEL_IDS[tier_model]
    nvcf_config = NVCF_PEXEC_MODELS[tier_model]
    nv_key = NVU_KEYS[key_idx]

    # Body: reuse _build_pexec_body (strip + inject). Same body for pexec/integrate (R572 已验).
    req_body = _build_pexec_body(oai_body, tier_model, nvcf_config)
    req_data = json.dumps(req_body).encode("utf-8")

    is_direct = (not proxy_url) or (proxy_url.strip() == "")
    if channel == "pexec":
        # func_health 选首选 function (intra-model), surge 的自动跳过.
        _candidates = nvcf_config.get("function_ids") or [nvcf_config.get("function_id")]
        function_id = func_health.select_healthy_function(tier_model, _candidates)
        result.function_id = function_id
        nvcf_host = NVCF_BASE_URL
        nvcf_path = f"/v2/nvcf/pexec/functions/{function_id}"
    else:
        nvcf_host = NV_INTEGRATE_HOST
        nvcf_path = NV_INTEGRATE_PATH
        function_id = "integrate"

    # R839 per-mode budget: 每个 mode 单次 attempt 有自己的 budget, 避免一个慢 mode 吃光整链.
    # 用 NVU_TIER_BUDGET_GLM5_2_NV (env, 当前 70s) 作为整链上限, 单 attempt timeout 复用
    # UPSTREAM_TIMEOUT / override. CONNECT_RESERVE_S 预留 connect+SSL 时间.
    chain_budget_s = float(os.environ.get(f"NVU_TIER_BUDGET_{tier_model.upper()}", "70"))
    # R1418: chain budget 按 input 缩放. 实测 353K 请求单次 timeout 67s, 4 档容错需 ~270s,
    # 固定 120s 在第 2 档就耗尽 -> all_tiers_exhausted (16:09:26 353K 请求 240s 全跑穿仍失败).
    # 大请求给 300s 容 4 档容错; 小请求仍用 env 值 (120s) 不变.
    _chain_ic = len(json.dumps(oai_body)) if oai_body else 0
    if _chain_ic > 350000:
        chain_budget_s = max(chain_budget_s, 300.0)
    elif _chain_ic > 200000:
        chain_budget_s = max(chain_budget_s, 240.0)
    elapsed_in_chain = time.time() - t_start
    remaining_budget = chain_budget_s - elapsed_in_chain
    CONNECT_RESERVE_S = float(os.environ.get("NVU_CONNECT_RESERVE_S", "5"))
    MIN_ATTEMPT_TIMEOUT = 5
    if remaining_budget < MIN_ATTEMPT_TIMEOUT:
        _log("NV-GLM52-BUDGET", f"tier={tier_model} mode={mode_name} k{key_idx+1} chain budget "
                                 f"{chain_budget_s}s remaining {remaining_budget:.1f}s < {MIN_ATTEMPT_TIMEOUT}s, abort chain")
        result.all_keys_exhausted = True
        result.final_error_json = {"error": {"type": "glm52_chain_budget_exhausted",
                                              "message": f"chain budget {chain_budget_s}s exhausted",
                                              "mode": mode_name}}
        result.final_resp_status = 408
        result.key_cycle_attempts = all_attempts
        result.elapsed_ms = int((time.time() - t_start) * 1000)
        return result
    per_attempt_timeout = max(MIN_ATTEMPT_TIMEOUT,
                             min(upstream_timeout_override if upstream_timeout_override else UPSTREAM_TIMEOUT,
                                 remaining_budget - CONNECT_RESERVE_S))

    # R295 header camouflage (与 _try_tier_keys/_try_integrate_keys 完全一致)
    hdr_extra = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "application/json, text/plain, */*",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://build.nvidia.com",
        "Referer": "https://build.nvidia.com/explore/discover",
    }
    headers_out = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {nv_key}",
        "Content-Length": str(len(req_data)),
        "Connection": "close",
        **hdr_extra,
    }

    _log("NV-GLM52-ATTEMPT", f"tier={tier_model} mode={mode_name} k{key_idx+1} channel={channel} "
                             f"{'DIRECT' if is_direct else 'via ' + proxy_url} timeout={per_attempt_timeout:.0f}s")

    attempt = {
        "tier": tier_model,
        "nv_key_idx": key_idx,
        "litellm_model": f"{channel}_{nv_model_id}_k{key_idx+1}",
        "mode": mode_name,
        "channel": channel,
        "proxy": proxy_url if proxy_url else "direct",
        "upstream_type": result.upstream_type,
        "function_id": function_id,
    }

    try:
        throttle_outbound()
        t_attempt_start = time.time()
        conn = _make_nvcf_proxy_conn(proxy_url, nvcf_host=nvcf_host, timeout=per_attempt_timeout)
        connect_elapsed = time.time() - t_attempt_start
        post_connect_remaining = chain_budget_s - (time.time() - t_start)
        if post_connect_remaining < MIN_ATTEMPT_TIMEOUT:
            _log("NV-GLM52-BUDGET", f"tier={tier_model} mode={mode_name} k{key_idx+1} after connect "
                                    f"({connect_elapsed:.1f}s) remaining {post_connect_remaining:.1f}s, abort")
            try: conn.close()
            except Exception: pass
            attempt["error_type"] = "budget_exhausted_after_connect"
            attempt["elapsed_ms"] = int(connect_elapsed * 1000)
            all_attempts.append(attempt)
            result.all_keys_exhausted = True
            result.key_cycle_attempts = all_attempts
            result.elapsed_ms = int((time.time() - t_start) * 1000)
            return result
        read_timeout = min(per_attempt_timeout, post_connect_remaining)
        conn.request("POST", nvcf_path, body=req_data, headers=headers_out)
        if conn.sock:
            conn.sock.settimeout(read_timeout)
        resp = conn.getresponse()

        if resp.status >= 400:
            error_body = resp.read()
            try: error_json = json.loads(error_body)
            except Exception: error_json = {"error": error_body.decode("utf-8", errors="replace")}
            conn.close()
            err_str = json.dumps(error_json)
            should_cycle = resp.status in (401, 403, 429, 408, 500, 502, 503, 504, 202)
            attempt["error_body"] = err_str[:500]
            if resp.status in (401, 403):
                integ_tier = _integrate_tier_name(tier_model) if channel == "integrate" else tier_model
                mark_key_cooling(integ_tier if channel == "integrate" else tier_model, key_idx,
                                 duration_s=NV_INTEGRATE_KEY_COOLDOWN_S if channel == "integrate" else KEY_COOLDOWN_S)
                mark_key_auth_failed(key_idx)
                attempt["error_type"] = f"{channel}_auth_failed_{resp.status}"
                _log("NV-GLM52-AUTH-FAIL", f"tier={tier_model} mode={mode_name} k{key_idx+1} {resp.status} auth failed, cycling")
            elif resp.status == 429:
                integ_tier = _integrate_tier_name(tier_model) if channel == "integrate" else tier_model
                mark_key_cooling(integ_tier if channel == "integrate" else tier_model, key_idx,
                                 duration_s=NV_INTEGRATE_KEY_COOLDOWN_S if channel == "integrate" else KEY_COOLDOWN_S)
                attempt["error_type"] = f"{channel}_429"
                _log("NV-GLM52-COOLDOWN", f"tier={tier_model} mode={mode_name} k{key_idx+1} 429, cooling")
            elif should_cycle:
                attempt["error_type"] = f"{channel}_{resp.status}"
            else:
                # Non-cycling (e.g. 400 DEGRADED) — tier-level, mark degraded
                if resp.status == 400 and "DEGRADED" in err_str.upper():
                    _cd = mark_tier_degraded(tier_model)
                    _log("NV-GLM52-TIER-DEGRADED", f"tier={tier_model} marked DEGRADED cooldown {_cd:.0f}s")
                attempt["error_type"] = f"{channel}_noncycle_{resp.status}"
                all_attempts.append(attempt)
                result.final_error_json = error_json
                result.final_resp_status = resp.status
                result.key_cycle_attempts = all_attempts
                result.elapsed_ms = int((time.time() - t_start) * 1000)
                # Non-cycling = 不换 key 也不递进 mode? 还是递进? 用户: 故障即递进 mode.
                # DEGRADED 是 tier 级故障 (同 model 全 key 都会 400), 递进 mode 也无效但符合
                # "故障即递进" 规则且 all_attempts 已记录, 上层会落 _try_tier_keys 兜底.
                return result  # 故障 → 上层递进 mode
            all_attempts.append(attempt)
            result.key_cycle_attempts = all_attempts
            result.elapsed_ms = int((time.time() - t_start) * 1000)
            return result  # 故障 → 上层递进 mode + 换 key

        # 200 — check empty
        is_empty = _check_empty_200(resp, key_idx, tier_model, is_stream)
        if is_empty:
            attempt["error_type"] = f"{channel}_empty_200"
            all_attempts.append(attempt)
            integ_tier = _integrate_tier_name(tier_model) if channel == "integrate" else tier_model
            mark_key_cooling(integ_tier if channel == "integrate" else tier_model, key_idx,
                             duration_s=NV_INTEGRATE_KEY_COOLDOWN_S if channel == "integrate" else KEY_COOLDOWN_S)
            _log("NV-GLM52-EMPTY", f"tier={tier_model} mode={mode_name} k{key_idx+1} empty 200, cooling, mode→advance")
            try: conn.close()
            except Exception: pass
            result.key_cycle_attempts = all_attempts
            result.elapsed_ms = int((time.time() - t_start) * 1000)
            return result  # empty = 故障 → 上层递进 mode

        # ─── Valid success ───
        result.success = True
        result.resp = resp
        result.conn = conn
        result.nv_key_idx = key_idx
        result.nv_model_label = f"{channel}_{nv_model_id}_k{key_idx+1}"
        # R839: 记录成功 attempt (含 mode) 到 key_cycle_attempts, 供 DB key_cycle_details 查 mode.
        _succ_attempt = dict(attempt)
        _succ_attempt["error_type"] = f"{channel}_success"
        _succ_attempt["elapsed_ms"] = int((time.time() - t_attempt_start) * 1000)
        all_attempts.append(_succ_attempt)
        result.key_cycle_attempts = all_attempts
        result.fallback_tiers_used = [tier_model]
        # egress info: pexec direct/mihomo 用 egress_info_for_key; integrate 用实际 proxy_url 算.
        if channel == "pexec":
            result.egress_route, result.egress_ip = egress_info_for_key(key_idx)
            # 但 mode 驱动的 proxy 可能与 NVU_PROXY_URLS[key_idx] 不同 (R839 新增美国代理出口),
            # 覆盖: mode 非 direct 时用 proxy_url 推导 route + NV_INTEGRATE_EGRESS_IPS 兜底.
            if not is_direct:
                _port = proxy_url.strip().rsplit(":", 1)[-1] if ":" in proxy_url else "?"
                result.egress_route = f"glm52-mihomo-{_port}"
                # 查 NV_INTEGRATE_EGRESS_IPS (与 NV_INTEGRATE_PROXY_URLS 顺序对齐)
                if NV_INTEGRATE_PROXY_URLS:
                    try:
                        _pi = NV_INTEGRATE_PROXY_URLS.index(proxy_url)
                        result.egress_ip = NV_INTEGRATE_EGRESS_IPS[_pi] if _pi < len(NV_INTEGRATE_EGRESS_IPS) else ""
                    except ValueError:
                        result.egress_ip = ""
        else:
            _port = proxy_url.strip().rsplit(":", 1)[-1] if proxy_url and ":" in proxy_url else "direct"
            result.egress_route = f"glm52-integrate-mihomo-{_port}" if not is_direct else "glm52-integrate-direct"
            if not is_direct and NV_INTEGRATE_PROXY_URLS:
                try:
                    _pi = NV_INTEGRATE_PROXY_URLS.index(proxy_url)
                    result.egress_ip = NV_INTEGRATE_EGRESS_IPS[_pi] if _pi < len(NV_INTEGRATE_EGRESS_IPS) else ""
                except ValueError:
                    result.egress_ip = ""
            elif is_direct:
                _, result.egress_ip = egress_info_for_integrate_key(key_idx)
        reset_key429_count(_integrate_tier_name(tier_model) if channel == "integrate" else tier_model, key_idx)
        metrics["upstream_type"] = result.upstream_type
        metrics["tier_model"] = tier_model
        metrics["nv_key_idx"] = key_idx
        metrics["litellm_model"] = result.nv_model_label
        metrics["glm52_mode"] = mode_name
        metrics["egress_route"] = result.egress_route
        metrics["egress_ip"] = result.egress_ip
        if all_attempts:
            metrics["key_cycle_429s_before_success"] = len(all_attempts)
            metrics["key_cycle_details"] = all_attempts
        _log("NV-GLM52-SUCCESS", f"tier={tier_model} mode={mode_name} k{key_idx+1} succeeded "
                                  f"(mode stabilized, next req keeps this mode)")
        return result

    except socket.timeout as e:
        attempt_elapsed_ms = int((time.time() - t_attempt_start) * 1000)
        attempt["error_type"] = f"{channel}_timeout"
        attempt["elapsed_ms"] = attempt_elapsed_ms
        all_attempts.append(attempt)
        _log("NV-GLM52-TIMEOUT", f"tier={tier_model} mode={mode_name} k{key_idx+1} timeout: {attempt_elapsed_ms}ms → mode→advance")
        result.key_cycle_attempts = all_attempts
        result.elapsed_ms = int((time.time() - t_start) * 1000)
        return result
    except (ConnectionRefusedError, http.client.RemoteDisconnected) as e:
        attempt_elapsed_ms = int((time.time() - t_attempt_start) * 1000)
        attempt["error_type"] = f"{channel}_conn_{type(e).__name__}"
        attempt["elapsed_ms"] = attempt_elapsed_ms
        all_attempts.append(attempt)
        _log("NV-GLM52-CONN", f"tier={tier_model} mode={mode_name} k{key_idx+1} conn err: {e} → mode→advance")
        result.key_cycle_attempts = all_attempts
        result.elapsed_ms = int((time.time() - t_start) * 1000)
        return result
    except Exception as e:
        error_class = type(e).__name__
        elapsed_ms = int((time.time() - t_attempt_start) * 1000)
        attempt["error_type"] = f"{channel}_{error_class}"
        attempt["error"] = str(e)[:200]
        attempt["elapsed_ms"] = elapsed_ms
        all_attempts.append(attempt)
        is_ssl = error_class in ("SSLEOFError", "SSLError", "SSLZeroReturnError")
        _log("NV-GLM52-ERR", f"tier={tier_model} mode={mode_name} k{key_idx+1} {error_class}: {e} → mode→advance")
        result.key_cycle_attempts = all_attempts
        result.elapsed_ms = int((time.time() - t_start) * 1000)
        return result


def _try_glm52_mode_chain(oai_body, tier_model, request_id, metrics, t_start,
                          is_stream, all_attempts, upstream_timeout_override):
    """R839: glm5_2_nv per-key-mode 动态递进. mode 是持久化指针, 故障→递进, 稳住→保持.

    modes = NV_GLM52_MODE_CHAIN (list of (mode_name, channel, ip_strategy), len 5).
    最多试 NVU_NUM_KEYS + 2 轮 (5 key + 容错). 每 attempt: 当前 key + 当前 mode.
      - success → 持久化 mode_idx (保持, 不递进) + return success
      - fault → mode_idx = min(idx+1, len-1) + 换下一个 key
    全 key+全 mode 失败 → all_keys_exhausted, 持久化最后 mode_idx (下次从最后 mode 起步).
    """
    modes = NV_GLM52_MODE_CHAIN
    result = UpstreamResult()
    result.is_stream = is_stream
    result.tier_model = tier_model
    if not modes:
        result.all_keys_exhausted = True
        result.final_error_json = {"error": {"type": "glm52_mode_chain_empty",
                                              "message": "NV_GLM52_MODE_CHAIN not configured"}}
        result.key_cycle_attempts = all_attempts
        result.elapsed_ms = int((time.time() - t_start) * 1000)
        return result

    mode_idx = glm52_current_mode_idx()
    if mode_idx >= len(modes):
        mode_idx = 0  # 持久化值越界 (config 变了) → 回到 mode1
    start_key = _next_nv_key(tier_model)  # RR 起始 key
    _log("NV-GLM52-CHAIN", f"tier={tier_model} start_mode_idx={mode_idx} (={modes[mode_idx][0]}) "
                           f"start_key=k{start_key+1} modes={[m[0] for m in modes]}")

    for attempt in range(NVU_NUM_KEYS + 2):
        key_idx = (start_key + attempt) % NVU_NUM_KEYS
        mode_name, channel, ip_strategy = modes[mode_idx]
        # 跳过冷却/auth-fail 的 key (仍递进 mode? 不: key 冷却 ≠ mode 故障, 换 key 不递进 mode)
        _integ_tier = _integrate_tier_name(tier_model) if channel == "integrate" else None
        _ck_tier = _integ_tier if channel == "integrate" else tier_model
        if is_key_cooling(_ck_tier, key_idx) or is_key_auth_failed(key_idx):
            _log("NV-GLM52-KEY-SKIP", f"tier={tier_model} mode={mode_name} k{key_idx+1} cooling/auth-failed, next key (no mode advance)")
            # 不递进 mode, 继续下一个 key (key 冷却不是 mode 的错)
            continue

        proxy_url = _glm52_resolve_proxy(ip_strategy, attempt)
        r = _glm52_single_attempt(oai_body, tier_model, request_id, metrics, t_start,
                                   is_stream, key_idx, mode_name, channel, proxy_url,
                                   list(all_attempts), upstream_timeout_override)
        all_attempts = r.key_cycle_attempts

        if r.success and not r.empty_200:
            # 稳住 → 保持当前 mode (不递进), 持久化供下次请求起步
            glm52_save_mode_idx(mode_idx)
            r.fallback_tiers_used = [tier_model]
            metrics["tier_model"] = r.tier_model
            metrics["fallback_tiers_used"] = r.fallback_tiers_used
            metrics["glm52_mode"] = mode_name
            metrics["nv_key_idx"] = key_idx
            if r.function_id:
                metrics["function_id"] = r.function_id
            func_health.record_result(r.function_id, True)
            # advance RR (与 pexec 对齐, 保持轮转均匀)
            _next_nv_key(tier_model)
            return r

        # budget-abort (chain 预算耗尽): 不递进, 直接全链失败
        if r.all_keys_exhausted and r.final_error_json and \
           r.final_error_json.get("error", {}).get("type") == "glm52_chain_budget_exhausted":
            result.all_keys_exhausted = True
            result.final_error_json = r.final_error_json
            result.final_resp_status = r.final_resp_status
            result.key_cycle_attempts = all_attempts
            result.elapsed_ms = int((time.time() - t_start) * 1000)
            glm52_save_mode_idx(mode_idx)  # 下次从当前 mode 起步
            return result

        # 故障 → mode 递进到下一档 + 换下一个 key
        func_health.record_result(r.function_id, False)
        new_mode_idx = min(mode_idx + 1, len(modes) - 1)
        _log("NV-GLM52-MODE-ADVANCE", f"tier={tier_model} k{key_idx+1} mode={mode_name} fault → "
                                      f"next key + mode {mode_idx}→{new_mode_idx} (={modes[new_mode_idx][0]})")
        if new_mode_idx == mode_idx:
            # R857: advance 停滞(已到末尾 mode, min(idx+1,len-1)=idx). 不卡末尾单IP,
            # reset 到 mode0(多IP轮换最稳). 修 R843/R856: idx=3 stuck 致 43次 3→3 死循环撞同一坏IP.
            mode_idx = 0
            glm52_save_mode_idx(0)
            _log("NV-GLM52-MODE-STALL-RESET", f"tier={tier_model} mode={mode_name} at chain end → "
                                               f"reset mode_idx to 0 (={modes[0][0]}), next attempt restarts from mode0")
        else:
            mode_idx = new_mode_idx

    # 全 key+全 mode 失败
    _log("NV-GLM52-CHAIN-FAIL", f"tier={tier_model} all {NVU_NUM_KEYS} keys + modes exhausted, "
                                f"last_mode={modes[mode_idx][0]}")
    result.all_keys_exhausted = True
    result.final_error_json = {"error": {"type": "glm52_chain_all_keys_exhausted",
                                          "message": f"all keys + all modes failed for {tier_model}",
                                          "last_mode": modes[mode_idx][0]}}
    result.final_resp_status = 502
    result.key_cycle_attempts = all_attempts
    result.elapsed_ms = int((time.time() - t_start) * 1000)
    # R844: 全 key+全 mode 失败 → 复位 idx=0 (而非保持最后失败 mode).
    # 之前保持最后 mode (如 idx=3 integrate_us_single) 致下个请求继续撞同一坏 mode/IP
    # (7894 坏 IP, 76 次 zombie). mode0=pexec_us_rr 多 IP 轮换更可能分散命中好 IP.
    # 后端整体恢复由 speedtest cron 重排 chain 实现软重置; 硬故障期复位 0 是逃逸阀.
    glm52_reset_mode_idx()
    _log("NV-GLM52-CHAIN-RESET", f"tier={tier_model} all modes failed → reset mode_idx to 0 (next req from {modes[0][0]})")
    return result




def execute_request(handler, oai_body, mapped_model, request_id, metrics, t_start, upstream_timeout_override=None):
    """Execute NVCF pexec request with three-tier fallback (R38.12, R40 ring fallback).

    ALL models use NVCF pexec direct path. No LiteLLM routing.
    - mapped_model determines starting tier (default: dsv4p_nv)
    - R40 CRITICAL FIX: ring fallback — tier_order = TIERS[start:] + TIERS[:start]
      This guarantees ANY tier (including the last) has 2 fallback tiers.
      Pre-R40 bug: TIERS[start_idx:] slice — when start_tier was the LAST tier
      (e.g. the last model in R38.9 tier order), the slice had only 1 element,
      so a failure at that tier returned 502 with NO fallback attempted.
      Symptom: "Tiers tried: [dsv4p_nv: 2×mixed]" 74.2s, agent stuck.
    - Each tier tries 5 keys with per-tier persistent RR counter
    - On tier all-fail: fallback to next tier in ring order (wraps around)
    - All tiers fail: ABORT-NO-FALLBACK
    - R38.8: If all tiers fail with ONLY connection errors, wait 5s and retry once.
    """
    start_tier_idx = get_tier_index(mapped_model)
    is_stream = oai_body.get("stream", False)

    # R551/R_multi: dynamic surge fallback. tier_order = [mapped_model] + healthy alternatives.
    # Cross-model fallback controlled by FALLBACK_GRAPH whitelist.
    # Health check per-function: check alt model's primary function health.
    tier_order = [mapped_model]
    for alt in FALLBACK_GRAPH.get(mapped_model, []):
        alt_cfg = NVCF_PEXEC_MODELS.get(alt, {})
        alt_cands = alt_cfg.get("function_ids") or [alt_cfg.get("function_id")]
        alt_primary = alt_cands[0] if alt_cands else None
        if alt_primary and func_health.is_healthy(alt_primary):
            tier_order.append(alt)
    if len(tier_order) > 1:
        _log("NV-REQ", f"mapped_model={mapped_model} start_tier={mapped_model} stream={is_stream} tier_chain={tier_order} (dynamic fallback, health={{...}})")
    else:
        _log("NV-REQ", f"mapped_model={mapped_model} start_tier={mapped_model} stream={is_stream} tier_chain={tier_order} (no fallback, 3model)")

    for retry_idx in range(2):
        all_attempts = []
        all_tier_summaries = []
        fallback_tiers_used = []

        for tier_idx, tier_model in enumerate(tier_order):
            is_first_tier = (tier_idx == 0)
            prev_tier = tier_order[tier_idx - 1] if not is_first_tier else None

            # Skip tier if all keys in cooldown
            all_cooling = all(is_key_cooling(tier_model, k) for k in range(NVU_NUM_KEYS))
            if all_cooling:
                _log("NV-TIER-SKIP", f"tier={tier_model} all keys in cooldown, skipping")
                # R40 A3: cooldown is neither 429 nor empty-200 — don't misclassify.
                all_tier_summaries.append({
                    "tier": tier_model,
                    "all_429": False,
                    "all_empty_200": False,
                    "all_cooldown": True,
                    "num_attempts": 0,
                    "elapsed_ms": 0,
                    "skipped": True,
                })
                if not is_first_tier:
                    _log("NV-FALLBACK", f"Tier {prev_tier} all-failed → "
                                        f"falling back to {tier_model} (skipped, cooldown)")
                continue

            if not is_first_tier:
                _log("NV-FALLBACK", f"Tier {prev_tier} all-failed → "
                                    f"falling back to {tier_model}")

            # R839/R1421: glm5_2_nv per-key-mode 动态切换链 (port from HM2). mode 是持久化指针,
            # 故障→递进+换key, 稳住→保持. 与 R838b/R572 互斥: 仅 glm5_2_nv + 配置了
            # NV_GLM52_MODE_CHAIN 时触发, 命中即 return, 不命中落到 R838b/R572/pexec 原逻辑.
            # NV-GLM52-R839-BRANCH
            if (is_first_tier and tier_model == "glm5_2_nv" and NV_GLM52_MODE_CHAIN
                    and not _integrate_is_path_cooling()):
                chain_result = _try_glm52_mode_chain(oai_body, tier_model, request_id, metrics, t_start,
                                                       is_stream, all_attempts, upstream_timeout_override)
                if chain_result.success and not chain_result.empty_200:
                    chain_result.fallback_tiers_used = [tier_model]
                    metrics["tier_model"] = chain_result.tier_model
                    metrics["fallback_tiers_used"] = chain_result.fallback_tiers_used
                    metrics["glm52_mode"] = chain_result.nv_model_label  # placeholder, _try 内已写 mode
                    if chain_result.function_id:
                        metrics["function_id"] = chain_result.function_id
                    if retry_idx > 0:
                        _log("NV-STARTUP-RETRY-SUCCESS", f"Startup retry #{retry_idx} succeeded (glm52 mode chain)")
                        metrics["startup_retry"] = retry_idx
                    return chain_result
                # mode chain 全失败 → 落 R838b/R572/pexec 兜底 (现 _try_tier_keys 全 key pexec).
                _log("NV-GLM52-CHAIN-FALLBACK", f"tier={tier_model} mode chain all-failed → falling back to R838b/R572/pexec")
                all_attempts = list(chain_result.key_cycle_attempts)

            # R838b: per-key 跨链路 — RR 自然分散. peek 当前 RR key (不 advance), 若该 key 在
            # NV_KEY_INTEGRATE_KEYS 则走 integrate (只试该 key), 否则走 pexec (RR 到该 key 起).
            # 这样 K1-4 pexec 与 K5 integrate 按 RR 比例自然分担流量, 实现数据多样性.
            # 与 R572 互斥: model 在 NV_INTEGRATE_MODELS 走全 key integrate; 否则走 per-key 分支.
            _r838_keys = nv_key_integrate_keys_for(tier_model)
            _peek_key = _peek_nv_key(tier_model) if (is_first_tier and _r838_keys) else -1
            if (is_first_tier and NV_INTEGRATE_ENABLED
                    and tier_model not in NV_INTEGRATE_MODELS
                    and _r838_keys and _peek_key in _r838_keys
                    and not _integrate_is_path_cooling()):
                _log("NV-R838B-LANE", f"tier={tier_model} RR peek=k{_peek_key+1} → integrate (per-key)")
                integ_result = _try_integrate_keys(oai_body, tier_model, request_id, metrics, t_start,
                                                    is_stream, all_attempts, upstream_timeout_override,
                                                    key_filter=[_peek_key])
                if integ_result.success and not integ_result.empty_200:
                    _next_nv_key(tier_model)
                    integ_result.fallback_tiers_used = [tier_model]
                    metrics["tier_model"] = integ_result.tier_model
                    metrics["fallback_tiers_used"] = integ_result.fallback_tiers_used
                    if retry_idx > 0:
                        _log("NV-STARTUP-RETRY-SUCCESS", f"Startup retry #{retry_idx} succeeded (integrate per-key)")
                        metrics["startup_retry"] = retry_idx
                    return integ_result
                _log("NV-INTEGRATE-PERKEY-FALLBACK", f"tier={tier_model} k{_peek_key+1} integrate failed → falling back to pexec")
                all_attempts = list(integ_result.key_cycle_attempts)
                _next_nv_key(tier_model)
            # R572: 首选 integrate 直连路径 (仅 first tier + NV_INTEGRATE_MODELS + path 未冷却).
            # integrate 全 key 失败/全 429 → 回退下方 pexec _try_tier_keys (同一 tier_model).
            elif (is_first_tier and NV_INTEGRATE_ENABLED and tier_model in NV_INTEGRATE_MODELS
                    and not _integrate_is_path_cooling()):
                integ_result = _try_integrate_keys(oai_body, tier_model, request_id, metrics, t_start,
                                                    is_stream, all_attempts, upstream_timeout_override)
                if integ_result.success and not integ_result.empty_200:
                    integ_result.fallback_tiers_used = [tier_model]
                    metrics["tier_model"] = integ_result.tier_model
                    metrics["fallback_tiers_used"] = integ_result.fallback_tiers_used
                    if retry_idx > 0:
                        _log("NV-STARTUP-RETRY-SUCCESS", f"Startup retry #{retry_idx} succeeded (integrate)")
                        metrics["startup_retry"] = retry_idx
                    # integrate 无 function_id, 不记 func_health (它只追踪 pexec function).
                    return integ_result
                # integrate 失败 → 累积 attempts, 落到 pexec _try_tier_keys 重试同一 model.
                _log("NV-INTEGRATE-FALLBACK", f"tier={tier_model} integrate all-failed → "
                                               f"falling back to pexec same model")
                all_attempts = list(integ_result.key_cycle_attempts)
                all_tier_summaries.append({
                    "tier": tier_model,
                    "path": "nv_integrate",
                    "all_429": integ_result.all_429,
                    "all_empty_200": integ_result.empty_200,
                    "num_attempts": len([a for a in integ_result.key_cycle_attempts
                                         if a.get("tier") == tier_model]),
                    "elapsed_ms": integ_result.elapsed_ms,
                    "fell_back_to_pexec": True,
                })

            tier_result = _try_tier_keys(oai_body, tier_model, request_id, metrics, t_start,
                                         is_stream, all_attempts, upstream_timeout_override)

            if tier_result.success and not tier_result.empty_200:
                tier_result.fallback_tiers_used = tier_order[:tier_idx + 1]
                if not is_first_tier:
                    _log("NV-FALLBACK-SUCCESS", f"Success on fallback tier {tier_model} "
                                                f"after primary {tier_order[0]} failed")
                    metrics["fallback_from"] = prev_tier
                    metrics["fallback_to"] = tier_model
                metrics["tier_model"] = tier_result.tier_model
                metrics["fallback_tiers_used"] = tier_result.fallback_tiers_used
                # R794: 透传 function_id 到 metrics 供 DB request 级记录 (验证 NVCF per-key/IP/functionID 限速)
                if tier_result.function_id:
                    metrics["function_id"] = tier_result.function_id
                if retry_idx > 0:
                    _log("NV-STARTUP-RETRY-SUCCESS", f"Startup retry #{retry_idx} succeeded")
                    metrics["startup_retry"] = retry_idx
                # R_multi: 按本次选中的 function_id 记录健康度 (不是按 model)
                func_health.record_result(tier_result.function_id, True)
                return tier_result

            # Tier all-failed: record and try next
            # R40 A4: simplified — single condition, no `or a not in all_attempts` dead code.
            tier_attempts = [a for a in tier_result.key_cycle_attempts
                             if a.get("tier") == tier_model]
            # R_multi: 按本次选中的 function_id 记录失败. all_keys_exhausted=该function本轮surge.
            func_health.record_result(tier_result.function_id, False)
            # R794: 失败也透传 function_id (验证限速需看失败 attempt 的 function_id)
            if tier_result.function_id:
                metrics["function_id"] = tier_result.function_id
            all_tier_summaries.append({
                "tier": tier_model,
                "all_429": tier_result.all_429,
                "all_empty_200": tier_result.empty_200,
                "all_cooldown": False,
                "num_attempts": len(tier_attempts),
                "elapsed_ms": tier_result.elapsed_ms,
            })
            all_attempts = list(tier_result.key_cycle_attempts)

            if tier_result.conn:
                try:
                    tier_result.conn.close()
                except Exception:
                    pass

        # ─── All tiers exhausted ───
        _log("NV-ALL-TIERS-FAIL", f"All {len(tier_order)} tiers failed "
                                   f"(ring tiers tried: {tier_order}), "
                                   f"elapsed={int((time.time() - t_start) * 1000)}ms, ABORT-NO-FALLBACK")

        has_429 = any(s.get("all_429") for s in all_tier_summaries)
        has_empty = any(s.get("all_empty_200") for s in all_tier_summaries)

        # Check if ALL failures were connection errors only
        all_conn_err = not has_429 and not has_empty and all(
            ("Conn" in a.get("error_type", "") or "gai" in a.get("error_type", "").lower() or
             "socket" in a.get("error_type", "").lower())
            for a in all_attempts
        ) and len(all_attempts) > 0

        if all_conn_err and retry_idx == 0:
            _log("NV-STARTUP-RETRY", f"All tiers failed with only connection errors. Waiting 5s...")
            time.sleep(5)
            continue

        break

    # Build final result
    has_429 = any(s.get("all_429") for s in all_tier_summaries)
    has_empty = any(s.get("all_empty_200") for s in all_tier_summaries)

    final_result = UpstreamResult()
    final_result.success = False
    final_result.all_keys_exhausted = True
    final_result.all_429 = has_429 and not has_empty
    final_result.empty_200 = has_empty
    final_result.key_cycle_attempts = all_attempts
    final_result.tier_attempts = all_tier_summaries
    final_result.fallback_tiers_used = tier_order
    final_result.elapsed_ms = int((time.time() - t_start) * 1000)
    final_result.final_resp_status = 429 if has_429 else 502

    _log_error_detail({
        "request_id": request_id,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "error_subcategory": "all_tiers_failed",
        "start_tier": tier_order[0],
        "tiers_tried": tier_order,
        "tier_summaries": all_tier_summaries,
        "total_attempts": len(all_attempts),
        "elapsed_ms": final_result.elapsed_ms,
        "startup_retry_attempted": retry_idx > 0,
    })

    # R41: Do NOT call _log_metrics() here. The metrics dict passed into this
    # function (from handlers._handle_openai_nv) is written by handlers.py in
    # the `all_keys_exhausted` branch (handlers.py ~L142) with full DB-compatible
    # fields (request_id, timestamp, duration_ms, status, fallback_tiers_used...).
    # A second _log_metrics here previously emitted a *sparse* dict (only
    # request_id/error_subcategory/start_tier/tiers_tried/elapsed_ms) missing the
    # NOT NULL `ts`/`timestamp` and the `duration_ms`/`fallback_tiers_used` keys
    # that db._build_request_row reads. One sparse dict in a flush batch made the
    # whole batch INSERT fail and rollback → hermes_logs.nv_requests stayed empty
    # (~96 rows on 06-24, only 6 landed). error_detail file above is unaffected.
    # Removing this duplicate restores DB persistence without losing event signal.

    return final_result
