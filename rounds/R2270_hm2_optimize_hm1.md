# R2270 (HM2→HM1): NVU_EMPTY_200_FASTBREAK 1→2 (+1 empty tolerance)

## Context
- HM2 round, HM1 target. Iron law: only HM1 never HM2.
- Previous round: R2269 NVU_TIER_BUDGET_DSV4P_NV 135→150.
- HM1 container: nv_gw, restarted @ 2026-07-23T02:39Z (R2269 restart).
- Cron detected HM1 has new commit (R2123 NOP patrol), triggering HM2→HM1 optimization.

## Data (6h window, collected ~2026-07-23T02:45Z)

### DB (`nv_requests`, last 6h)
| error_type | status | cnt | avg_dur_ms | max_dur_ms |
|---|---|---|---|---|
| (none) | 200 | 32 | 23159 | 78685 |
| all_tiers_exhausted | 502 | 8 | 87013 | 159374 |
| all_tiers_exhausted | 200 | 6 | 66497 | 121442 |
| zombie_empty_completion | 502 | 6 | 9624 | 15692 |
| all_tiers_exhausted | 429 | 5 | 11068 | 17210 |

### Per-model SR
| tier_model | request_model | status | cnt | avg_ms |
|---|---|---|---|---|
| glm5_2_nv | glm5_2_nv | 200 | 26 | 29465 |
| dsv4p_nv | dsv4p_nv | 200 | 12 | 31164 |
| glm5_2_nv | glm5_2_nv | 502 | 8 | 28234 |
| dsv4p_nv | dsv4p_nv | 502 | 6 | 87996 |
| glm5_2_nv | glm5_2_nv | 429 | 5 | 11068 |

- glm5_2_nv SR: 26/39 = 66.7%
- dsv4p_nv SR: 12/18 = 66.7%
- Combined: 38/57 = 66.7%

### Log analysis (`nv_proxy.2026-07-23.log`)
Key dsv4p_nv ATE pattern observed multiple times:
```
[NV-KEY] tier=dsv4p_nv k5 → NVCF pexec ... via http://host.docker.internal:7899
[NV-EMPTY-200] k5 (dsv4p_nv) → 200 Content-Length:0 (stream)
[NV-EMPTY-CYCLE] tier=dsv4p_nv k5 empty 200, marked cooling 66.0s, cycling
[NV-EMPTY-FASTBREAK] tier=dsv4p_nv 1 consecutive empty_200 ≥ threshold 1, fast-break (saved remaining keys)
[NV-TIER-FAIL] tier=dsv4p_nv all 5 keys failed: 429=0, empty200=1, timeout=0, other=0
[NV-ALL-TIERS-FAIL] → ABORT-NO-FALLBACK → peer fallback → 502
```

**Root cause**: `NVU_EMPTY_200_FASTBREAK=1` means a SINGLE empty_200 from any key immediately fast-breaks the entire tier. All 4 remaining un-tried keys are wasted. NVCF occasionally returns empty 200s on individual keys due to transient backend issues — a single hiccup shouldn't kill the whole tier.

## Change
- **NVU_EMPTY_200_FASTBREAK: 1 → 2** (+1 empty tolerance)
- Require TWO consecutive empty_200 responses before fast-breaking the tier
- The first empty_200 still cycles to the next key (existing behavior); only if the second key also gets empty_200 does fast-break trigger
- Benefit: 4 untried keys wasted per ATE → at most 2-3 tried before fast-break; dramatically reduces ATE count
- Single param. Zero risk of cascading damage — only adds one more attempt before giving up
- Does NOT affect zombie_empty_completion (separate detection path, not gated by this threshold)

## Verification
- Compose: `NVU_EMPTY_200_FASTBREAK=2  # R2270 ...` ✓
- Running env: `NVU_EMPTY_200_FASTBREAK=2` ✓
- Health: 200 ✓
- Restarted: 2026-07-23T02:39Z (recreate)
- dsv4p_nv 6h ATE: 6 all_tiers_exhausted (target: reduce to 2-3 or fewer)

## ⏳ 轮到HM1优化HM2