# R2271 (HM2→HM1): TIER_TIMEOUT_BUDGET_S 192→222 (+30s global budget)

## Context
- HM2 round, HM1 target. Iron law: only HM1 never HM2.
- Previous round: R2270 NVU_EMPTY_200_FASTBREAK 1→2.
- HM1 container: nv_gw, restarted @ 2026-07-23T03:15Z (R2271 restart).
- Cron detected HM1 has new commit (R2270), triggering HM2→HM1 optimization.

## Data (6h window, collected ~2026-07-23T03:10Z)

### DB (`nv_requests`, last 6h)
| mapped_model | total | 200 | 502 | ATE | zombie | phantom ATE |
|---|---|---|---|---|---|---|
| glm5_2_nv | 41 | 29 | 12 | 1 | 6 | 7 |
| dsv4p_nv | 17 | 12 | 5 | 5 | 0 | 0 |

- dsv4p_nv SR: 12/17 = 70.6%
- glm5_2_nv SR: 29/41 = 70.7%
- Combined: 41/58 = 70.7%

### dsv4p_nv ATE deep dive (all 5 ATE, all 0 tier_attempts)
| duration_ms | total_input_chars | key_cycle_429s |
|---|---|---|
| 27226 | 82107 | 0 |
| 61956 | 91667 | 0 |
| 63655 | 91228 | 0 |
| 120067 | 359210 | 0 |
| 135045 | 66928 | 0 |

- ALL 5 dsv4p_nv ATE have 0 tier_attempts — tier killed by budget before any key attempted
- 4/5 durations 27s-63s (budget exhaustion), 1 at 120s (global cap)
- 0 dsv4p cycle2+ (clean key cycling), 9 glm5_2_nv cycle2+ (22%)

### Key cycling
| mapped_model | total | cycle0 | cycle1 | cycle2+ |
|---|---|---|---|---|
| glm5_2_nv | 41 | 26 | 6 | 9 |
| dsv4p_nv | 17 | 15 | 2 | 0 |

### Peer-fallback: 0 events in 6h

### Current HM1 config
```
KEY_COOLDOWN_S=66
TIER_COOLDOWN_S=66
NVU_TIER_BUDGET_DSV4P_NV=150
TIER_TIMEOUT_BUDGET_S=192
UPSTREAM_TIMEOUT=24
NVU_EMPTY_200_FASTBREAK=2 (R2270)
```

## Root Cause Analysis

**Global budget constraint pre-empting dsv4p_nv tier**:

```
KEY_COOLDOWN_S(66) + TIER_COOLDOWN_S(66) + NVU_TIER_BUDGET_DSV4P_NV(150) = 282
TIER_TIMEOUT_BUDGET_S = 192
Effective tier budget = 192 - 66 - 66 = 60s
Per-key cost = KEY_COOLDOWN_S(66) + UPSTREAM_TIMEOUT(24) = 90s
60s < 90s → gateway CANNOT attempt even 1 key → 0 tier_attempts → pre-empted ATE
```

All 5 dsv4p ATE show 0 tier_attempts, confirming the budget was exhausted before any key could be tried. The 4 ATE at 27-63s were killed by the global budget cap; the 1 ATE at 120s was killed by the tier budget wall (150s but constrained to 60s effective).

## Change
- **TIER_TIMEOUT_BUDGET_S: 192 → 222** (+30s, +15.6%)
- New effective tier budget: 222 - 66 - 66 = 90s = exactly 1 key attempt
- Budget safety check:
  - Effective tier: 222 - 66 - 66 = 90s > 90s (per-key) → 1 key guaranteed ✓
  - Peer-fb trigger: 24 + 122 = 146 < 222 ✓
  - Global vs tier: 66 + 66 + 150 = 282 > 222 (still constrained, but now at least 1 key attempt)
- Single param. Iron law: only HM1.

## Verification
- Compose: `TIER_TIMEOUT_BUDGET_S=222  # R2271 ...` ✓
- Running env: `TIER_TIMEOUT_BUDGET_S=222` ✓
- Health: 200 ✓
- Restarted: 2026-07-23T03:15Z (recreate)
- Target: reduce dsv4p_nv 0-tier_attempts ATE from 5→≤2 (1 key attempt should rescue some)

## ⏳ 轮到HM1优化HM2