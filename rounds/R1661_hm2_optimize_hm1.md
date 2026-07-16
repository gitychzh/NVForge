# R1661: HM2→HM1 — FASTBREAK 2→1 (-1 key)

## 6h Summary
- **Total**: 40 req, 22 OK (55.0%), 18 fail (45.0%)
- **glm5_2_nv**: 14 zombie_empty_completion, 16 OK — 53.3% fail rate
- **dsv4p_nv**: 5 all_tiers_exhausted, 7 OK — 41.7% fail rate
- **Zero fallback**: fallback_occurred=false for ALL 42 requests
- **key_cycle_429s**: 30 total (all single-key, 1 each)

## Per-Model Detail
| model | ok | fail | avg_ok_ms | avg_all_ms |
|-------|----|------|-----------|------------|
| glm5_2_nv | 16 | 14 | 5,981 | 6,098 |
| dsv4p_nv | 7 | 5 | 24,555 | 40,273 |

## Hourly Trend
| hour (UTC) | ok | fail | total |
|-------------|----|------|-------|
| 2026-07-16 17:00 | 1 | 1 | 2 |
| 2026-07-16 18:00 | 10 | 7 | 17 |
| 2026-07-16 19:00 | 3 | 3 | 6 |
| 2026-07-16 20:00 | 2 | 3 | 5 |
| 2026-07-16 21:00 | 3 | 2 | 5 |
| 2026-07-16 22:00 | 3 | 2 | 5 |
| 2026-07-16 23:00 | 1 | 1 | 2 |

## dsv4p_nv ATE Analysis
All 5 dsv4p ATE are all_tiers_exhausted, duration ~61.5-64.3s, tiers_tried=1, single-key. BUDGET=90, UPSTREAM=66, FASTBREAK=2 → k1 consumes ~62s, remaining 28s < UPSTREAM=66 → k2 never starts. FASTBREAK=2 is dead code for dsv4p_nv at current BUDGET.

## glm5_2_nv Zombie Analysis
13 zombie_empty_completion, pattern: content_chars < 50 with input_chars >= 5000, R852b zombie detector triggers. Model-level issue, not config fixable. glm5_2 BUDGET=120 >> UPSTREAM=66, FASTBREAK=2 is meaningful for glm5_2 but 14 zombie failures are not config-fixable.

## Optimization
**NVU_PEXEC_TIMEOUT_FASTBREAK: 2 → 1**

Rationale:
- dsv4p_nv: BUDGET=90, k1=~62s, remaining 28s < UPSTREAM=66 → k2 never starts. FASTBREAK=2 wastes time waiting for a slot that can't materialize. FASTBREAK=1 clean tier exhaust at ~62s, releases BUDGET for peer-fb (72s available).
- glm5_2_nv: BUDGET=120, UPSTREAM=66, k1=~5s avg, k2 would have 54s > UPSTREAM=66 — FASTBREAK=2 is usable for glm5_2 but zombie failures are model-level, not key-level. Losing 2nd key for glm5_2 has minimal impact (zombie detection happens at content level, not key level).
- R559-R694 history: 136 rounds stable at FASTBREAK=1.
- Saves ~28s/ATE on dsv4p_nv path, enables peer-fallback rescue.

## Verification
- Container `nv_gw` restarted, health OK
- `docker exec nv_gw env` confirms: NVU_PEXEC_TIMEOUT_FASTBREAK=1 ✓
- All other params unchanged: UPSTREAM=66, BUDGET_DSV4P=90, BUDGET_GLM5_2=120, PEER_FALLBACK=72, KEY_COOLDOWN=65, TIER_COOLDOWN=65, EMPTY_200_FASTBREAK=2, SSLEOF=0.5, CONNECT_RESERVE=0, MIN_OUTBOUND=0
- 铁律: 只改HM1不改HM2 ✓
## ⏳ 轮到HM1优化HM2
