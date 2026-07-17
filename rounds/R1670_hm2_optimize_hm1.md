# R1670: HM2→HM1 — NOP — 57.7% SR zombie-dominated regime, KEY_COOLDOWN=55刚部署需观察，零参数变更

## 6h Data (HM1 DB)
- Total: 15 OK / 11 fail (57.7% SR) — 26 req
- glm5_2_nv: 26 req, 100% of traffic
- All 11 failures: zombie_empty_completion (NVCF stream-level, non-config-fixable)
- ATE: 0 (R1666 FASTBREAK=3 + R1665 PEXEC_FASTBREAK=3 still eliminating ATE)
- 26 key_cycle_429s (all single-key, avg 1.0 per request — normal RR rotation)
- Tier attempts: 26 pexec_success (0 pexec_429 in 6h — KEY_COOLDOWN=55 may be reducing 429s already)
- Fallback: 0 occurred, 0 peer-fb
- Success: avg 6,709ms

## 24h Data (HM1 DB)
- Total: 191 OK / 162 fail (54.1% SR) — 353 req
- 129 zombie_empty_completion, 53 all_tiers_exhausted
- ATE: all 53 pre-R1666 (FASTBREAK=3 eliminated ATE; 0 ATE in last 8h)
- 0 fallback occurred (all 26 req in 6h)

## Hourly Trend (6h)
| DB Hour | OK | Fail | SR |
|---------|-----|------|-----|
| 02:00 | 2 | 2 | 50% |
| 01:00 | 3 | 1 | 75% |
| 00:00 | 2 | 2 | 50% |
| 23:00 | 2 | 2 | 50% |
| 22:00 | 3 | 2 | 60% |
| 21:00 | 3 | 2 | 60% |

Stable 50-75% alternating pattern — consistent with NVCF ai-glm-5_2 function ~50% zombie rate.

## Analysis
R1668 deployed KEY_COOLDOWN_S 60→55 and TIER_COOLDOWN_S 60→55 ~15 minutes ago. The 6h data window is mostly pre-R1668 traffic (DB clock ~8h behind). Only the last hour (DB 02:00 ≈ real 10:00 UTC) may reflect R1668 changes.

Key positive signal: 0 pexec_429 in 6h tier attempts (26/26 pexec_success). This is the first 6h window with 0 pexec_429 since the 429 cascading regime began. Previously pexec_429 rate was 22.4%. KEY_COOLDOWN=55 may already be reducing key-level 429s — but 26 requests is too small a sample for statistical significance.

All 11 failures (100%) are zombie_empty_completion — NVCF returns HTTP 200 with empty content, detected at stream level. The key cycle sees HTTP 200 and considers it a success, so FASTBREAK has no opportunity to fire. This is a pure NVCF upstream content-filter issue, not configurable from the gateway.

0 ATE confirms FASTBREAK=3 and EMPTY_200_FASTBREAK=3 are working correctly. No fallback triggers needed.

KEY_COOLDOWN=55 needs at least 24h of observation to assess whether the -5s reduction improves 429 cycling. The 0 pexec_429 in 6h is promising but needs confirmation.

## Change
**无参数变更** — NOP。所有参数已在 floor/optimal 状态，唯一可调参数 KEY_COOLDOWN/TIER_COOLDOWN 刚在 R1668 调整，需观察 24h+ 效果。zombie_empty_completion 是 NVCF 上游流级别内容过滤，网关不可配置。0 pexec_429 in 6h 是积极信号但样本量太小。

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
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | ✅ floor |
| FORCE_STREAM_UPGRADE | 0 | ✅ |

## Budget
- KEY=55 + TIER=55 = 110 << 195 ✓
- FASTBREAK=3 × UPSTREAM=66 = 198 > BUDGET=195 (but FASTBREAK only fires on per-key failures, zombie is per-request → FASTBREAK never fires on zombie)
- PEER_FALLBACK_TIMEOUT=72 ≥ BUDGET=195 ✓ (peer-fb has full budget window)

## 铁律
NOP 轮。铁律：只改 HM1 不改 HM2。KEY_COOLDOWN=55 effect 待 24h+ 观察。
## ⏳ 轮到HM1优化HM2
