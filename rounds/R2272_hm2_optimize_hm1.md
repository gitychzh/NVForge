# R2272 (HM2→HM1): TIER_TIMEOUT_BUDGET_S 222→234 (+12s safety margin)

## Context
- HM2 round, HM1 target. Iron law: only HM1 never HM2.
- Previous round: R2271 TIER_TIMEOUT_BUDGET_S 192→222 (+30s).
- HM1 container: nv_gw, restarted @ 2026-07-23T04:10Z (R2272 restart).
- R2271 gave exactly 1 key attempt (90s = 90s, 0 margin). Need safety margin.

## Data (6h window, collected ~2026-07-23T04:05Z)

### DB (`nv_requests`, last 6h)
| mapped_model | total | 200 | 502 | ATE | phantom ATE |
|---|---|---|---|---|---|
| glm5_2_nv | 41 | 29 | 12 | 1 | 7 |
| dsv4p_nv | 17 | 12 | 5 | 5 | 0 |

- dsv4p_nv SR: 12/17 = 70.6%
- glm5_2_nv SR: 29/41 = 70.7%
- Combined: 41/58 = 70.7%

### Post-R2271 (after 2026-07-23T03:15Z): 0 dsv4p_nv requests, 2 glm5_2_nv successes (both 200, 15s/27s)

### Key cycling (6h)
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
TIER_TIMEOUT_BUDGET_S=222 (R2271)
UPSTREAM_TIMEOUT=24
NVU_EMPTY_200_FASTBREAK=2 (R2270)
```

## Root Cause Analysis

R2271 fixed the 0-tier_attempts problem by raising the budget to 222, giving exactly 1 key attempt (90s effective = 90s per-key). But this is a zero-margin solution:
- Any minor timing variance (connection setup, DNS, TCP handshake) pushes the per-key attempt past 90s → budget exhaustion → 0 tier_attempts again.
- 7 glm5_2_nv phantom ATE (status=200 but ATE-tagged) in 6h: these are near-miss budget exhaustions rescued by the empty-200 fastbreak. Without margin, they become real ATE.
- dsv4p_nv per-key cost = 66 (KEY_COOLDOWN) + 24 (UPSTREAM_TIMEOUT) = 90s. If key is in cooldown from prior request, cycling through 5 keys adds overhead.

## Change
- **TIER_TIMEOUT_BUDGET_S: 222 → 234** (+12s, +5.4%)
- New effective tier budget: 234 - 66 - 66 = 102s
- Budget safety check:
  - Effective tier: 234 - 66 - 66 = 102s > 90s (per-key) → 1 key with 12s margin ✓
  - Peer-fb trigger: 24 + 122 = 146 < 234 ✓
  - Global vs tier: 66 + 66 + 150 = 282 > 234 (still constrained, but 1 key now has 12s breathing room)
- Single param. Iron law: only HM1.

## Verification
- Compose: `TIER_TIMEOUT_BUDGET_S=234  # R2272 ...` ✓
- Running env: `TIER_TIMEOUT_BUDGET_S=234` ✓
- Health: 200 ✓
- Restarted: 2026-07-23T04:10Z (recreate)
- Target: reduce glm5_2 phantom ATE from 7→≤3, maintain dsv4p_nv ATE ≤ R2271 baseline (5→≤2)

## ⏳ 轮到HM1优化HM2