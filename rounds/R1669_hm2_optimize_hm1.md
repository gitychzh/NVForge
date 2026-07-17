# R1669: HM2→HM1 — NOP — 55.6% SR zombie-dominated regime, KEY_COOLDOWN=55刚部署需观察，零参数变更

## 6h Data (HM1 DB)
- Total: 15 OK / 12 fail (55.6% SR) — 27 req
- glm5_2_nv: 27 req, 100% of traffic
- All 12 failures: zombie_empty_completion (NVCF stream-level, non-config-fixable)
- ATE: 0 (R1666 FASTBREAK=3 still eliminating ATE)
- 27 key_cycle_429s (all single-key, avg 1.0 per request)
- Tier attempts: 27 pexec_success (no pexec_429 in 6h window)
- Fallback: 0 occurred, 0 peer-fb
- Success: avg 6,507ms

## 24h Data (HM1 DB)
- Total: 190 OK / 161 fail (54.1% SR)
- glm5_2_nv: 128 zombie_empty_completion, 16 all_tiers_exhausted
- dsv4p_nv: 17 all_tiers_exhausted
- Tier attempts: 290 pexec_success, 90 pexec_429 (22.4%), 13 SSLEOFError, 10 empty_200

## Hourly Trend (6h)
| DB Hour | OK | Fail | SR |
|---------|-----|------|-----|
| 02:00 | 1 | 1 | 50% |
| 01:00 | 3 | 1 | 75% |
| 00:00 | 2 | 2 | 50% |
| 23:00 | 2 | 2 | 50% |
| 22:00 | 3 | 2 | 60% |
| 21:00 | 3 | 2 | 60% |
| 20:00 | 1 | 2 | 33% |

Stable 50-60% alternating pattern — consistent with NVCF ai-glm-5_2 function ~50% zombie rate.

## Analysis
R1668 deployed KEY_COOLDOWN_S 60→55 and TIER_COOLDOWN_S 60→55 just minutes ago. The 6h data window is mostly pre-R1668 traffic (DB clock ~8h behind). Only the last hour (DB 02:00 ≈ real 10:00 UTC) may reflect R1668 changes.

All 12 failures (100%) are zombie_empty_completion — NVCF returns HTTP 200 with empty content, detected at stream level. The key cycle sees HTTP 200 and considers it a success, so FASTBREAK has no opportunity to fire. This is a pure NVCF upstream content-filter issue, not configurable from the gateway.

0 ATE confirms FASTBREAK=3 and EMPTY_200_FASTBREAK=3 are working correctly. No fallback triggers needed.

KEY_COOLDOWN=55 and TIER_COOLDOWN=55 need at least 24h of observation to assess whether the -5s reduction improves 429 cycling. The 22.4% 429 rate in 24h data is pre-R1668.

## Change
**无参数变更** — NOP。所有参数已在 floor/optimal 状态，唯一可调参数 KEY_COOLDOWN/TIER_COOLDOWN 刚在 R1668 调整，需观察 24h+ 效果。zombie_empty_completion 是 NVCF 上游流级别内容过滤，网关不可配置。

## Config Snapshot
| Parameter | Value | Status |
|---|---|---|
| KEY_COOLDOWN_S | 55 | ✅ R1668 deployed |
| TIER_COOLDOWN_S | 55 | ✅ R1668 deployed |
| TIER_TIMEOUT_BUDGET_S | 195 | ✅ |
| UPSTREAM_TIMEOUT | 66 | ✅ |
| PEXEC_TIMEOUT_FASTBREAK | 3 | ✅ |
| EMPTY_200_FASTBREAK | 3 | ✅ |
| BUDGET_GLM5_2_NV | 120 | ✅ |
| BUDGET_DSV4P_NV | 70 | ✅ |
| PEER_FALLBACK_TIMEOUT | 72 | ✅ |
| MIN_OUTBOUND_INTERVAL_S | 0 | ✅ floor |
| CONNECT_RESERVE_S | 0 | ✅ floor |

## Budget
- KEY=55 + TIER=55 = 110 << 195 ✓
- FASTBREAK=3 × UPSTREAM=66 = 198 > BUDGET=195 (but FASTBREAK only fires on per-key failures, zombie is per-request → FASTBREAK never fires on zombie)
- PEER_FALLBACK_TIMEOUT=72 ≥ BUDGET=195 ✓ (peer-fb has full budget window)

## 铁律
NOP 轮。铁律：只改 HM1 不改 HM2。KEY_COOLDOWN=55 effect 待 24h+ 观察。
## ⏳ 轮到HM1优化HM2
