#!/usr/bin/env python3
"""Upstream request executor for Hermes NV proxy — R38.12.

Reng (HM1 self-change, authorized): modularized for long-term maintainability.
NVCF connection layer → gateway/nvcf_conn.py; pexec request
construction/validation → gateway/pexec.py. This file now holds the core
tier-key loop (_try_tier_keys) and three-tier fallback orchestration
(execute_request). Logic is byte-for-byte equivalent to the pre-refactor
version.

Rproxy (HM1 self-change, authorized): per-key direct/proxy routing is driven
purely by HM_NV_PROXY_URL<n> env (empty=direct, non-empty=mihomo SOCKS5).
k2/k4 direct, k1/k3/k5 via mihomo on HM1. _make_nvcf_proxy_conn (in nvcf_conn.py)
handles the empty→direct branch internally, so the unified call below routes
both paths.

R38.10: deepseek bypasses DEGRADING integrate API → NVCF pexec orion (ACTIVE).
R38.8:  Connection refused fast-break + startup retry.
R38.6:  sock.settimeout BEFORE getresponse, Connection:close.

Default tier: deepseek (primary) + kimi (fallback)
If all 5 keys fail → fallback to next tier.
If all tiers also all-fail → ABORT-NO-FALLBACK.

Chain: hm40006 → NVCF pexec (deepseek/kimi only). K1/K2 direct, K3-K5 via mihomo SOCKS5 → NV API
"""
import json
import os
import http.client
import socket
import time

from .config import (
    HM_NV_KEYS, HM_NUM_KEYS, HM_NV_PROXY_URLS,
    NV_MODEL_IDS, NV_MODEL_TIERS, DEFAULT_NV_MODEL, detect_nv_model,
    get_tier_index,
    NVCF_PEXEC_MODELS, NVCF_BASE_URL,
    UPSTREAM_TIMEOUT, TIER_TIMEOUT_BUDGET_S,
    _next_hm_nv_key,
    throttle_outbound,
    is_key_cooling, mark_key_cooling, reset_key429_count,
    TIER_COOLDOWN_S,
)
from .logger import _log, _log_metrics, _log_error_detail
from .nvcf_conn import _make_nvcf_proxy_conn
from .pexec import _build_pexec_body, _check_empty_200


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
        self.key_cycle_attempts = []
        self.upstream_type = "nvcf_pexec"
        self.tier_attempts = []
        self.fallback_tiers_used = []
        # Error fields
        self.all_keys_exhausted = False
        self.all_429 = False
        self.empty_200 = False
        self.elapsed_ms = 0
        self.final_error_json = None
        self.final_resp_status = 0


def _try_tier_keys(oai_body, tier_model, request_id, metrics, t_start,
                   is_stream, prior_cycle_attempts):
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
    key_cycle_attempts = list(prior_cycle_attempts)


    nv_model_id = NV_MODEL_IDS[tier_model]
    nvcf_config = NVCF_PEXEC_MODELS[tier_model]
    nvcf_host = NVCF_BASE_URL
    function_id = nvcf_config["function_id"]
    nvcf_path = f"/v2/nvcf/pexec/functions/{function_id}"

    _log("HM-TIER", f"Starting tier={tier_model} model={nv_model_id} "
                    f"func={function_id[:12]}... (position from rr_counter)")

    # Build request body with per-model param stripping
    pexec_body = _build_pexec_body(oai_body, tier_model, nvcf_config)

    # Get starting key from per-tier persistent counter
    start_key_idx = _next_hm_nv_key(tier_model)

    tier_budget_start = time.time()
    consecutive_conn_err = 0
    CONN_ERR_FAST_BREAK = 2

    for attempt_idx in range(HM_NUM_KEYS + 2):
        key_idx = (start_key_idx + attempt_idx) % HM_NUM_KEYS
        t_attempt_start = time.time()  # R38.14: per-attempt start time for accurate logging

        # Tier timeout budget check (before each attempt)
        elapsed_in_tier = time.time() - tier_budget_start
        if elapsed_in_tier >= TIER_TIMEOUT_BUDGET_S:
            _log("HM-TIER-BUDGET", f"tier={tier_model} budget {TIER_TIMEOUT_BUDGET_S}s "
                                    f"exceeded after {elapsed_in_tier:.1f}s, breaking")
            break

        # R38.14: per-attempt timeout respects remaining budget
        # R40 A2: reserve CONNECT_RESERVE_S for SOCKS5 connect+SSL handshake (2-5s observed).
        #   Pre-R40 bug: per_attempt_timeout = min(45, remaining) ignored connect time, so
        #   attempt 1 spent 45s(read)+3s(connect)=48s but budget thought only 45s elapsed;
        #   attempt 2 then got remaining=15s, spent 3s(connect)+15s(read)=18s → total 66s,
        #   ~74s with throttle/overhead, blowing past the 60s budget and showing as 74.2s
        #   in the 502 error. Reserve keeps the read timeout within true remaining budget.
        CONNECT_RESERVE_S = float(os.environ.get("HM_CONNECT_RESERVE_S", "5"))
        remaining_budget = TIER_TIMEOUT_BUDGET_S - elapsed_in_tier
        MIN_ATTEMPT_TIMEOUT = 5  # R45: 10→5 — 10s 下限在 budget 被前次 timeout 吃掉后误杀后续 key (NVCF 实测 p50=3s); 5s 仍保留 dooming-attempt 保护 # Don't attempt if less than 10s budget remains (doomed attempt)
        if remaining_budget < MIN_ATTEMPT_TIMEOUT:
            _log("HM-TIER-BUDGET", f"tier={tier_model} budget {TIER_TIMEOUT_BUDGET_S}s "
                                    f"remaining {remaining_budget:.1f}s < {MIN_ATTEMPT_TIMEOUT}s minimum, breaking")
            break
        # Read timeout = min(UPSTREAM_TIMEOUT, remaining - CONNECT_RESERVE) so connect+read together stay in budget
        per_attempt_timeout = max(MIN_ATTEMPT_TIMEOUT,
                                  min(UPSTREAM_TIMEOUT, remaining_budget - CONNECT_RESERVE_S))

        # Skip keys in 429 cooldown
        if is_key_cooling(tier_model, key_idx):
            _log("HM-KEY", f"tier={tier_model} k{key_idx+1} is in cooldown (429), skipping")
            if attempt_idx >= HM_NUM_KEYS and all(is_key_cooling(tier_model, k) for k in range(HM_NUM_KEYS)):
                _log("HM-TIER", f"tier={tier_model} all keys in cooldown, breaking")
                break
            continue

        # ─── NVCF pexec request ───
        if HM_NUM_KEYS == 0 or key_idx >= len(HM_NV_KEYS):
            _log("HM-PEXEC-ERR", f"tier={tier_model} k{key_idx+1} no NV key/proxy configured")
            key_cycle_attempts.append({
                "tier": tier_model,
                "nv_key_idx": key_idx,
                "error_type": "nvcf_pexec_no_key",
                "upstream_type": "nvcf_pexec",
            })
            continue

        nv_key = HM_NV_KEYS[key_idx]
        # ─ Rproxy: per-key proxy strategy driven by HM_NV_PROXY_URL<n> env ─
        # empty proxy_url → DIRECT (k2/k4 on HM1); non-empty → mihomo SOCKS5 (k1/k3/k5).
        # _make_nvcf_proxy_conn handles the empty→direct branch internally.
        proxy_url = HM_NV_PROXY_URLS[key_idx] if key_idx < len(HM_NV_PROXY_URLS) else ""
        is_direct = (not proxy_url) or (proxy_url.strip() == "")

        # Build per-attempt request (model field already set in pexec_body)
        pexec_data = json.dumps(pexec_body).encode("utf-8")

        _log("HM-KEY", f"tier={tier_model} attempt {attempt_idx+1}/{HM_NUM_KEYS + 2}: "
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
            post_connect_remaining = TIER_TIMEOUT_BUDGET_S - (time.time() - tier_budget_start)
            if post_connect_remaining < MIN_ATTEMPT_TIMEOUT:
                _log("HM-TIER-BUDGET", f"tier={tier_model} k{key_idx+1} after connect "
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

                should_cycle = resp.status in (429, 408, 500, 502)
                if should_cycle:
                    cycle_reason = "429_nv_rate_limit" if resp.status == 429 else \
                                   "408_nvcf_timeout" if resp.status == 408 else \
                                   "500_nv_error" if resp.status == 500 else "502_nv_error"
                    key_cycle_attempts.append({
                        "tier": tier_model,
                        "nv_key_idx": key_idx,
                        "litellm_model": f"nvcf_{NV_MODEL_IDS[tier_model]}_k{key_idx+1}",
                        "error_body": err_str[:500],
                        "error_type": cycle_reason,
                        "upstream_type": "nvcf_pexec",
                    })
                    if resp.status == 429:
                        mark_key_cooling(tier_model, key_idx)
                        _log("HM-COOLDOWN", f"tier={tier_model} k{key_idx+1} marked cooling after 429")
                    _log("HM-CYCLE", f"tier={tier_model} k{key_idx+1} → "
                                     f"{resp.status} ({cycle_reason}), cycling to next key")
                    continue

                # Non-cycling error → report
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
                })
                _log("HM-EMPTY-CYCLE", f"tier={tier_model} k{key_idx+1} empty 200, cycling")
                try:
                    conn.close()
                except Exception:
                    pass
                continue

            # ─── Valid success response ───
            consecutive_conn_err = 0
            result.success = True
            result.resp = resp
            result.conn = conn
            result.tier_model = tier_model
            result.nv_key_idx = key_idx
            result.nv_model_label = f"nvcf_{NV_MODEL_IDS[tier_model]}_k{key_idx+1}"
            result.key_cycle_attempts = key_cycle_attempts
            result.fallback_tiers_used = [tier_model]
            result.upstream_type = "nvcf_pexec"
            reset_key429_count(tier_model, key_idx)
            metrics["upstream_type"] = "nvcf_pexec"
            metrics["tier_model"] = tier_model
            metrics["nv_key_idx"] = key_idx
            metrics["litellm_model"] = result.nv_model_label
            if key_cycle_attempts:
                metrics["key_cycle_429s_before_success"] = len(key_cycle_attempts)
                metrics["key_cycle_details"] = key_cycle_attempts
                _log("HM-SUCCESS", f"tier={tier_model} k{key_idx+1} succeeded after "
                                    f"{len(key_cycle_attempts)} cycle attempts")
            else:
                _log("HM-SUCCESS", f"tier={tier_model} k{key_idx+1} succeeded on first attempt")
            return result

        except socket.timeout as e:
            # R38.14: use per-attempt elapsed, not request-level t_start
            attempt_elapsed_ms = int((time.time() - t_attempt_start) * 1000)
            total_elapsed_ms = int((time.time() - t_start) * 1000)
            _log("HM-TIMEOUT", f"tier={tier_model} k{key_idx+1} NVCF pexec timeout: "
                               f"attempt={attempt_elapsed_ms}ms total={total_elapsed_ms}ms")
            key_cycle_attempts.append({
                "tier": tier_model,
                "nv_key_idx": key_idx,
                "litellm_model": f"nvcf_{NV_MODEL_IDS[tier_model]}_k{key_idx+1}",
                "error_type": "NVCFPexecTimeout",
                "elapsed_ms": attempt_elapsed_ms,  # R38.14: per-attempt elapsed, not total
                "upstream_type": "nvcf_pexec",
            })
            continue

        except (ConnectionRefusedError, http.client.RemoteDisconnected) as e:
            attempt_elapsed_ms = int((time.time() - t_attempt_start) * 1000)  # R38.14
            _log("HM-CONN", f"tier={tier_model} k{key_idx+1} connection error: {e}")
            consecutive_conn_err += 1
            key_cycle_attempts.append({
                "tier": tier_model,
                "nv_key_idx": key_idx,
                "litellm_model": f"nvcf_{NV_MODEL_IDS[tier_model]}_k{key_idx+1}",
                "error_type": f"NVCFPexec{type(e).__name__}",
                "elapsed_ms": attempt_elapsed_ms,
                "upstream_type": "nvcf_pexec",
            })
            if consecutive_conn_err >= CONN_ERR_FAST_BREAK:
                _log("HM-CONN-BREAK", f"tier={tier_model} {consecutive_conn_err} consecutive "
                                       f"connection errors → fast-break")
                break
            continue

        except Exception as e:
            error_class = type(e).__name__
            elapsed_ms = int((time.time() - t_attempt_start) * 1000)  # R38.14: per-attempt
            _log("HM-ERR", f"tier={tier_model} k{key_idx+1} {error_class}: {e}")

            # R1: SSLEOFError/SSLError/SSLZeroReturnError is transient — mihomo/NVCF SSL hiccup.
            # Removed 'not is_stream' restriction — SSL errors affect both stream and non-stream equally.
            # Retrying SAME key once (3s backoff) has high success probability.
            # Without this, every SSLEOFError wastes a key slot → forced fallback.
            is_ssl_err = (error_class == "SSLEOFError" or error_class == "SSLError" or
                         error_class == "SSLZeroReturnError")
            if is_ssl_err:
                _log("HM-SSL-RETRY", f"tier={tier_model} k{key_idx+1} SSL error — "
                                    f"retrying same key after 3s backoff")
                time.sleep(3)
                continue  # retry SAME key — don't cycle

            if "gaierror" in error_class.lower() or "socket" in error_class.lower():
                consecutive_conn_err += 1
                if consecutive_conn_err >= CONN_ERR_FAST_BREAK:
                    _log("HM-CONN-BREAK", f"tier={tier_model} {consecutive_conn_err} consecutive "
                                           f"DNS/socket errors → fast-break")
                    key_cycle_attempts.append({
                        "tier": tier_model,
                        "nv_key_idx": key_idx,
                        "litellm_model": f"nvcf_{NV_MODEL_IDS[tier_model]}_k{key_idx+1}",
                        "error": str(e)[:200],
                        "error_type": f"NVCFPexec{error_class}",
                        "elapsed_ms": elapsed_ms,
                        "upstream_type": "nvcf_pexec",
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
    _log("HM-TIER-FAIL", f"tier={tier_model} all {HM_NUM_KEYS} keys failed: {fail_summary}, "
                          f"elapsed={result.elapsed_ms}ms")

    if all_429:
        for k in range(HM_NUM_KEYS):
            mark_key_cooling(tier_model, k, duration_s=int(TIER_COOLDOWN_S))
        _log("HM-GLOBAL-COOLDOWN", f"tier={tier_model} all keys 429. Marking all cooling {TIER_COOLDOWN_S:.0f}s (TIER_COOLDOWN)")

    _log_error_detail({
        "request_id": request_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "error_subcategory": f"tier_{tier_model}_all_keys_failed",
        "tier_model": tier_model,
        "tier_attempts": tier_attempts,
        "all_429": all_429,
        "all_empty_200": all_empty,
        "elapsed_ms": result.elapsed_ms,
    })

    return result


def execute_request(handler, oai_body, mapped_model, request_id, metrics, t_start):
    """Execute NVCF pexec request with three-tier fallback (R38.12, R40 ring fallback).

    ALL models use NVCF pexec direct path. No LiteLLM routing.
    - mapped_model determines starting tier (default: deepseek_hm_nv)
    - R40 CRITICAL FIX: ring fallback — tier_order = TIERS[start:] + TIERS[:start]
      This guarantees ANY tier (including the last) has 2 fallback tiers.
      Pre-R40 bug: TIERS[start_idx:] slice — when start_tier was the LAST tier
      (e.g. glm5.1 in R38.9 order [..., glm5.1]), the slice had only 1 element,
      so a failure at that tier returned 502 with NO fallback attempted.
      Symptom: "Tiers tried: [glm5.1_hm_nv: 2×mixed]" 74.2s, Hermes stuck.
    - Each tier tries 5 keys with per-tier persistent RR counter
    - On tier all-fail: fallback to next tier in ring order (wraps around)
    - All tiers fail: ABORT-NO-FALLBACK
    - R38.8: If all tiers fail with ONLY connection errors, wait 5s and retry once.
    """
    start_tier_idx = get_tier_index(mapped_model)
    is_stream = oai_body.get("stream", False)

    # R40: ring order — start_tier first, then the rest in original order, wrapping.
    # Example: TIERS=[A,B,C], start=B → ring=[B,C,A]. Last-tier C now has A as fallback.
    tier_order = NV_MODEL_TIERS[start_tier_idx:] + NV_MODEL_TIERS[:start_tier_idx]

    _log("HM-REQ", f"mapped_model={mapped_model} start_tier={NV_MODEL_TIERS[start_tier_idx]} "
                   f"stream={is_stream} tier_chain={tier_order} (ring fallback, R40)")

    for retry_idx in range(2):
        all_attempts = []
        all_tier_summaries = []
        fallback_tiers_used = []

        for tier_idx, tier_model in enumerate(tier_order):
            is_first_tier = (tier_idx == 0)
            prev_tier = tier_order[tier_idx - 1] if not is_first_tier else None

            # Skip tier if all keys in cooldown
            all_cooling = all(is_key_cooling(tier_model, k) for k in range(HM_NUM_KEYS))
            if all_cooling:
                _log("HM-TIER-SKIP", f"tier={tier_model} all keys in cooldown, skipping")
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
                    _log("HM-FALLBACK", f"Tier {prev_tier} all-failed → "
                                        f"falling back to {tier_model} (skipped, cooldown)")
                continue

            if not is_first_tier:
                _log("HM-FALLBACK", f"Tier {prev_tier} all-failed → "
                                    f"falling back to {tier_model}")

            tier_result = _try_tier_keys(oai_body, tier_model, request_id, metrics, t_start,
                                         is_stream, all_attempts)

            if tier_result.success and not tier_result.empty_200:
                tier_result.fallback_tiers_used = tier_order[:tier_idx + 1]
                if not is_first_tier:
                    _log("HM-FALLBACK-SUCCESS", f"Success on fallback tier {tier_model} "
                                                f"after primary {tier_order[0]} failed")
                    metrics["fallback_from"] = prev_tier
                    metrics["fallback_to"] = tier_model
                metrics["tier_model"] = tier_result.tier_model
                metrics["fallback_tiers_used"] = tier_result.fallback_tiers_used
                if retry_idx > 0:
                    _log("HM-STARTUP-RETRY-SUCCESS", f"Startup retry #{retry_idx} succeeded")
                    metrics["startup_retry"] = retry_idx
                return tier_result

            # Tier all-failed: record and try next
            # R40 A4: simplified — single condition, no `or a not in all_attempts` dead code.
            tier_attempts = [a for a in tier_result.key_cycle_attempts
                             if a.get("tier") == tier_model]
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
        _log("HM-ALL-TIERS-FAIL", f"All {len(tier_order)} tiers failed "
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
            _log("HM-STARTUP-RETRY", f"All tiers failed with only connection errors. Waiting 5s...")
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
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
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
    # whole batch INSERT fail and rollback → hermes_logs.hm_requests stayed empty
    # (~96 rows on 06-24, only 6 landed). error_detail file above is unaffected.
    # Removing this duplicate restores DB persistence without losing event signal.

    return final_result
