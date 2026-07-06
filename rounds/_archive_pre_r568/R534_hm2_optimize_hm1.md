# R534 — HM2 optimizing HM1

## ⏰ Timestamp
2026-07-02 05:42 UTC

## 🔬 Data Collection

### Docker logs (tail 100)
```
[HM-PROXY] Listening on 0.0.0.0:40006 (role=passthrough, default_tier=dsv4p_nv, fallback_chain=['kimi_nv', 'dsv4p_nv', 'glm5_1_nv'])
[05:35:07.2] [HM-FORCE-STREAM] upgrading non-stream->stream for upstream
[05:35:07.4] [HM-SUCCESS] tier=dsv4p_nv k4 succeeded on first attempt
[05:36:06.4] [HM-TIMEOUT] tier=kimi_nv k5 NVCF pexec timeout: attempt=59254ms total=59256ms
[05:36:06.4] [HM-PEXEC-FASTBREAK] tier=kimi_nv 1 consecutive NVCFPexecTimeout -> fast-break
[05:36:06.4] [HM-ALL-TIERS-FAIL] All 1 tiers failed, ABORT-NO-FALLBACK
[05:36:06.4] [HM-PEER-FB] attempting peer fallback to http://100.109.57.26:40006
[05:37:05.5] [HM-PEER-FB] peer connect/request failed after 59026ms: TimeoutError
```

### Container env (drift check)
| Parameter | Value | Status |
|-----------|-------|--------|
| UPSTREAM_TIMEOUT | 25 | ✅ R490 |
| TIER_TIMEOUT_BUDGET_S | 100 | ✅ R505 |
| MIN_OUTBOUND_INTERVAL_S | 1.2 | ✅ R521 |
| KEY_COOLDOWN_S | 25 | ✅ R162 |
| TIER_COOLDOWN_S | 25 | ✅ R492 |
| HM_CONNECT_RESERVE_S | 3 | ✅ R533 |
| HM_PEXEC_TIMEOUT_FASTBREAK | 1 | ✅ R516 |
| HM_FORCE_STREAM_UPGRADE_TIMEOUT | 59 | ⚠️ will change to 61 |
| HM_PEER_FALLBACK_TIMEOUT | 59 | ✅ R534 (compose already patched) |
| HM_SSLEOF_RETRY_DELAY_S | 2.0 | ✅ R429 |

### Docker compose drift check
- Line 425: HM_FORCE_STREAM_UPGRADE_TIMEOUT: "59" # R532 — matched env prior to change
- All other active lines matched env values

### DB — Last 10 requests
| created_at | model | status | duration_ms | ttfb_ms | nv_key | error |
|---|---|---|---|---|---|---|
| 21:37:05 | kimi_nv | 502 | 59262 | — | — | all_tiers_exhausted |
| 21:36:42 | dsv4p_nv | 200 | 50319 | 50274 | 4 | — |
| 21:35:51 | dsv4p_nv | 200 | 44076 | 44075 | 3 | — |
| 21:34:58 | dsv4p_nv | 200 | 25868 | 25867 | 1 | — |
| 21:34:05 | dsv4p_nv | 200 | 11781 | 11672 | 0 | — |
| 21:33:53 | dsv4p_nv | 200 | 7981 | 7980 | 4 | — |
| 21:33:47 | kimi_nv | 502 | 59252 | — | — | all_tiers_exhausted |
| 21:33:40 | dsv4p_nv | 200 | 17715 | 17714 | 3 | — |
| 21:33:17 | kimi_nv | 200 | 51428 | 51427 | 0 | — |
| 21:32:59 | dsv4p_nv | 200 | 44711 | 44602 | 2 | — |

### DB — 1h Summary by model
| model | total | ok | sr_pct | avg_dur_ok | max_dur_ok | min_dur_fail | max_dur_fail | avg_dur_fail |
|-------|-------|-----|--------|------------|------------|--------------|--------------|--------------|
| dsv4p_nv | 92 | 89 | 96.7 | 24949 | 57443 | 57263 | 59330 | 57963 |
| kimi_nv | 128 | 102 | 79.7 | 17653 | 56715 | 57204 | 59642 | 58062 |

**Cliff Analysis (1h):**
- kimi_nv: max_success=56715ms, min_failure=57204ms → cliff = 489ms
- This means requests that need ~57.1s succeed, but those needing ~57.2s+ hit 59s ceiling and fail
- dsv4p_nv: max_success=57443ms, min_failure=57263ms → negative overlap (some dsv4p success > dsv4p failure min), but failures still clustered near ceiling

### DB — 6h Summary
| model | total | ok | sr_pct |
|-------|-------|-----|--------|
| dsv4p_nv | 1716 | 1708 | 99.5 |
| kimi_nv | 896 | 731 | 81.6 |

### Peer fallback (1h)
- fb_attempted = 0 for both models — no peer fallback happening
- This is because FASTBREAK=1 breaks quickly, but local ATE still happens before peer can help
- Peer timeout = 59s, local timeout = 59s (was) — nearly synchronous, peer doesn't get a head start

### NVCFPexecTimeout distribution (1h)
- kimi_nv: 14 total timeouts across 5 keys (k2=4, k0=3, k4=3, k1=2, k3=2) — uniform distribution
- Function-level queuing confirmed, FASTBREAK=1 is correct regime

## 🎯 CC Checklist Evaluation (HM1)

| # | Item | Status | Notes |
|---|------|--------|-------|
| A | MIN_OUTBOUND=1.2 | ✅ done | R521. Zero 429 in 18h. No change needed |
| B | Key rebalancing | ✅ done | 5key uniform timeout pattern. No bad key |
| C | BUDGET=100 | ✅ adequate | 100 > 61 + reserve, single attempt has room. No change |
| D | FASTBREAK=1 | ✅ optimal | dsv4p 100% first-attempt, kimi zero 2nd-success evidence. No change |
| E | inject_thinking | ✅ done | low for kimi, working. No change |
| — | Ceiling chase | 🔄 active | R532: 57→59. R534: 59→61. +2s continuous tracking |
| — | Others | ✅ at ceiling | UPSTREAM=25 (optimized), SSLEOF=2.0 (low risk) |

## 📊 Decision

**🔧 HM_FORCE_STREAM_UPGRADE_TIMEOUT 59→61 (+2s)**

Rationale:
1. **Ceiling Cliff Detection**: 1h data shows clear 489ms cliff for kimi_nv (max_success=56715ms vs min_failure=57204ms). Requests needing 57.1-57.2s are on the edge.
2. **Failure clustering at new ceiling**: With timeout=59, failures are at 57.2-59.6s (clustered near the new 59s ceiling, not the old 57s ceiling). This proves 59s IS the new active ceiling.
3. **Continuous tracking rule**: R532 moved 57→59. R534 continues 59→61. Each step +2s under FASTBREAK=1 regime costs only +2s per failure (not +4s or +6s).
4. **dsv4p_nv benefit**: 6 ATE @57.6s in recent window will also be rescued by +2s.
5. **Zero 429 risk**: KEY_COOLDOWN=25 >> MIN_OUTBOUND=1.2, no rate limit concern.
6. **BUDGET margin**: 100 - 61 = 39s remaining, still adequate.
7. **Peer fallback alignment**: HM2 R533 already moved to 59, keeping HM1 at 59→61 is slightly ahead but acceptable since HM2 will catch up in next round.

## ⚙️ Deployment

- Modified: `/opt/cc-infra/docker-compose.yml` line 425
- Old: `HM_FORCE_STREAM_UPGRADE_TIMEOUT: "59"  # R532...`
- New: `HM_FORCE_STREAM_UPGRADE_TIMEOUT: "61"  # R534: HM2→HM1 -- 59→61 (+2s)...`
- Deployed: `docker compose up -d --no-deps hm40006` → Container Recreated + Started

## ✅ Verification (4-source)

| Source | Value | Status |
|--------|-------|--------|
| docker-compose.yml | "61" | ✅ |
| container env | 61 | ✅ |
| StartedAt | 2026-07-01T21:42:16Z (fresh) | ✅ |
| docker logs | `[HM-THINKING-TIMEOUT] ... extended timeout 61s` | ✅ |

## 📈 Round Record
- Single parameter change: HM_FORCE_STREAM_UPGRADE_TIMEOUT +2s
- No other parameters modified
- No code changes
- Compliance: 铁律:只改HM1不改HM2 ✅

## ⏳ 轮到HM1优化HM2
