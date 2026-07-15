# R1517: HM2→HM1 — NOP (false trigger, HM2 own commit, zero post-restart ATEs, all params floor/optimal)

**Summary**: 70 req / 48 OK / 67.6% SR (6h). Zero post-restart ATEs. All params floor/optimal. No config room.

## Data

| Metric | Value |
|--------|-------|
| 6h Total | 70 req / 48 OK / 67.6% SR |
| zombie_empty_completion | 19 (NVCF content-filter, 不可配置: glm5_2_nv=10, dsv4p_nv=9) |
| all_tiers_exhausted | 3 (all pre-restart: 22:07 dsv4p=6343ms, 22:03 glm5_2=8411ms, 18:04 dsv4p=61177ms) |
| tier_attempts | 2 (glm5_2_nv 429_integrate_rate_limit, transient) |
| ms_gw | 15/14 93.3% SR |
| Post-restart (22:25 UTC) | 6 req / 4 OK / 2 zombie. **Zero ATEs** |
| compose md5 | 9fb97661 (unchanged) |

## Config State

| Parameter | Value | Status |
|-----------|-------|--------|
| UPSTREAM_TIMEOUT | 66 | Floor |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | = UPSTREAM_TIMEOUT floor |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | Safe |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | Floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | Floor |
| NVU_EMPTY_200_FASTBREAK | 2 | R1031 (budget bottleneck per R1489) |
| TIER_COOLDOWN_S | 15 | R1103 revert |
| TIER_TIMEOUT_BUDGET_S | 205 | Safe |
| NVU_PEER_FB_SKIP_MODELS | "" | Peer-fb enabled |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | R1459 fix |
| PROXY_TIMEOUT | 360 | R1442 |
| MIN_OUTBOUND_INTERVAL_S | 0 | Optimal |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | Optimal |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | Optimal |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | Optimal |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | Optimal |
| NVU_CONNECT_RESERVE_S | 0 | Optimal |

## Decision: NOP

- Script output: "这是我提交的" — HM2's own commit (R1516), not a new HM1 trigger
- All 3 ATEs pre-restart (before 22:25 UTC)
- Post-restart: 6/6 requests no ATEs, 2 zombie only (NVCF content-filter, non-configurable)
- All params at floor/optimal. No config room for improvement.
- 铁律:只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
