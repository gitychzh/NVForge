# R1504: HM2→HM1 — NOP (zero ATE in 3h post-restart, zombie-only, all params floor/optimal)

## Data Collection

### SSH HM1
- SSH: `ssh -p 222 opc_uname@100.109.153.83` — connected
- nv_gw health: `{"status": "ok"}`, 5 keys, 4 models active
- nv_gw uptime: 3 hours (healthy)
- compose md5: `ba4f2871` (unchanged from R1498-R1503)

### DB (6h window — stale, last record 8h ago)
- DB write path broken — last record 2026-07-15 21:06 UTC, 8+ hours of zero new data
- 61 total, 38 OK (62.3%), 23 fail
- 20 zombie_empty_completion (87% of failures)
- 3 all_tiers_exhausted (dsv4p_nv, 13% of failures)
- ms_gw: 16/15 (93.8%) — healthy

### Live Logs (tail 100, 3h post-restart window)
| Signal | Count | Notes |
|--------|-------|-------|
| NV-INTEGRATE-SUCCESS | 7 | All first-attempt, glm5_2_nv |
| NV-ZOMBIE-EMPTY | 4 | NVCF content-filter, code-level |
| NV-THINKING-TIMEOUT | 4 | thinking requests, extended to 66s |
| NV-TIER-FAIL | 0 | ✅ |
| NV-CYCLE | 0 | ✅ |
| NV-PEER-FB | 0 | ✅ |
| NV-MS-FB | 0 | ✅ |
| NV-ALL-TIERS-FAIL | 0 | ✅ |
| 504 | 0 | ✅ |
| NV-NONCYCLE | 0 | ✅ |

### Environment (all 16 params)
| Parameter | Value | Status |
|-----------|-------|--------|
| UPSTREAM_TIMEOUT | 66 | Floor |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | Floor (=UPSTREAM) |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | Floor |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | Floor |
| TIER_TIMEOUT_BUDGET_S | 205 | Optimal |
| TIER_COOLDOWN_S | 15 | Floor |
| KEY_COOLDOWN_S | 25 | Floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | Floor |
| NVU_EMPTY_200_FASTBREAK | 2 | Optimal (code-level no-op per R1039/R1489) |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | Floor |
| NVU_PEER_FALLBACK_ENABLED | 1 | Optimal |
| NVU_PEER_FB_SKIP_MODELS | (empty) | Optimal |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | Optimal |
| NVU_CONNECT_RESERVE_S | 0 | Floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | Floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | Floor |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | Optimal |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | Optimal |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | Optimal |
| NVU_FORCE_STREAM_UPGRADE | 0 | Optimal |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | Optimal |

**All 16 params at floor/optimal. Compose md5 ba4f2871 unchanged.**

## Decision: NOP

### Failure Root Cause
1. **zombie_empty_completion (87% failures)**: NVCF returns finish_reason=stop but content_chars=12 < 50, input ~221K chars. Gateway correctly detects and aborts with zombie error chunk. Code-level NVCF content-filter issue, not config-fixable.
2. **all_tiers_exhausted (13% failures)**: dsv4p_nv 3× ATE in 6h DB window (all stale, pre-restart). 0 ATE in 3h post-restart live logs.

### Zero Config-Fixable Issues
- 0 NV-TIER-FAIL / NV-CYCLE / NV-PEER-FB / NV-MS-FB / 504 / NV-NONCYCLE in 3h post-restart
- 0 ATE in 3h post-restart (BUDGET=66 floor pattern working)
- All integrate requests succeed on first attempt (glm5_2_nv, 7/7)
- ms_gw 16/15 (93.8%) — reliable fallback
- Compose md5 unchanged across R1498-R1504

### Comparison with R1503
Identical NOP pattern. Same compose md5, same env, same zombie-only post-restart profile. 0 ATE in post-restart window for 2 consecutive rounds. All params at floor/optimal.

## Iron Rule
- ✅ Only modify HM1, never HM2 — no config changes this round
- ✅ compose md5 ba4f2871 unchanged
- ✅ 铁律:只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
