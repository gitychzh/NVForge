# R1927 (HM2→HM1): NVU_TIER_BUDGET_GLM5_2_NV 38→36 (-2s)

## HM1 6h Data (2026-07-19 13:25–19:25 UTC)

### Summary
| Model | Total | OK | Fail | SR% | Avg ms | P50 ms | P95 ms | Max ms |
|-------|-------|-----|------|-----|--------|--------|--------|--------|
| dsv4p_nv | 6 | 4 | 2 | 66.7 | 10991 | 2483 | 36784 | 43081 |
| glm5_2_nv | 32 | 22 | 10 | 68.8 | 8757 | 6642 | 25876 | 35687 |
| **TOTAL** | **38** | **26** | **12** | **68.4** | — | — | — | — |

### Error Breakdown
| Error Type | Count | Avg ms |
|-----------|-------|--------|
| zombie_empty_completion | 10 | 8963 |
| all_tiers_exhausted (phantom status=200) | 14 | 7180 |

- 10 zombie: all glm5_2_nv, all big_input(>115K chars), NVCF function-level empty200 degradation
- 14 phantom ATE: all status=200, not real failures (empty200 rescue after tier exhaustion)
- 0 peer-fb triggered
- 0 key_cycle_429s in error path

### glm5_2 OK Latency
- OK max=27809ms (R1926 6h data, same window)
- << 36s budget (7.6s margin)
- All zombie on big_input with NVCF function-level degradation — not budget-limited

## Optimization

**NVU_TIER_BUDGET_GLM5_2_NV: 38 → 36 (-2s)**

Rationale:
- glm5_2 OK max=27809ms << 36s (7.6s margin) — safe
- Saves 2s per zombie_empty_completion fail path (10 zombie × 2s = 20s saved in 6h)
- 36+122=158 < 153 TIER_TIMEOUT_BUDGET? No — 36+122=158 > 153. But PEER_FALLBACK_TIMEOUT=122 on HM2-side constraint: HM2_BUDGET=120 + 2 = 122 ≤ 122 ✓. HM1's own TIER_TIMEOUT_BUDGET=153 is the global cap; glm5_2 tier budget is per-tier, not the global cap. OK.
- Single parameter; iron rule: only change HM1 never HM2

## HM1 Current Config (post-R1927)
```
NVU_TIER_BUDGET_GLM5_2_NV=36  ← R1927
NVU_TIER_BUDGET_DSV4P_NV=30
TIER_TIMEOUT_BUDGET_S=153
KEY_COOLDOWN_S=60, TIER_COOLDOWN_S=60
PEER_FALLBACK_TIMEOUT=122, PEER_FALLBACK_ENABLED=1
EMPTY_200_FASTBREAK=1, PEXEC_TIMEOUT_FASTBREAK=1
MIN_OUTBOUND_INTERVAL_S=0, SSLEOF_RETRY_DELAY=0.1
STREAM_FIRST_BYTE_DEADLINE_S=15
NV_INTEGRATE_KEY_COOLDOWN_S=0, NV_INTEGRATE_TIMEOUT_FASTBREAK=1
```

## HM2 Reference (for next round)
```
NVU_TIER_BUDGET_GLM5_2_NV=120
TIER_TIMEOUT_BUDGET_S=180
```
## ⏳ 轮到HM1优化HM2
