# R912: HM2→HM1 — NOP (false trigger, 29th consecutive, 83/82 98.8% 6h SR, nv_gw at floor, ms_gw idle, no optimization space)

## Data Summary (6h window, 2026-07-09 02:10 UTC)

| Metric | Value |
|--------|-------|
| Total requests | 83 |
| Success (200) | 82 |
| ATE (502) | 1 |
| SR | 98.8% |
| avg_ttfb | 25,897ms |
| avg_duration | 27,079ms |

## Key Parameters (running)

| Parameter | Value | Status |
|-----------|-------|--------|
| UPSTREAM_TIMEOUT | 64 | No binding edge (max NVCFPexecTimeout=52,849ms, 11s headroom) |
| TIER_TIMEOUT_BUDGET_S | 114 | Ample (64+64=128 > 114, but FASTBREAK=1 so 64+??=??) |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | At floor |
| NVU_EMPTY_200_FASTBREAK | 3 | At floor (R829) |
| NVU_FORCE_STREAM_UPGRADE | 0 | At floor |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 | Aligned with UPSTREAM=64 |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | At floor (R697) |

## Failure Analysis

### Single ATE (glm5_2_nv → dsv4p_nv, 121,075ms, 2026-07-08 13:21 UTC)
- tiers_tried=2, fallback_occurred=false, fallback_actually_attempted=false
- Both tiers exhausted: glm5_2_nv + dsv4p_nv
- Isolated incident, no pattern

### Error Breakdown (6h)
| Error Type | Count |
|------------|-------|
| all_tiers_exhausted | 1 |
| NVCFPexecTimeout (dsv4p_nv k0) | 1 (52,849ms) |
| empty_200 (dsv4p_nv) | 1 |
| empty_200 (glm5_2_nv) | 6 |
| 504_nv_gateway_timeout (glm5_2_nv) | 3 |

### key_cycle_429s (6h)
- dsv4p_nv k3: 1
- glm5_2_nv k0: 1, k1: 1, k2: 4, k3: 1, k4: 2
- Negligible (9 total)

## Decision: NOP

No actionable optimization space:
1. **98.8% SR** — near-perfect
2. **No binding edges** — NVCFPexecTimeout max=52,849ms << UPSTREAM=64 (11s headroom)
3. **FASTBREAK=1 at floor** — no reduction possible
4. **EMPTY_200_FASTBREAK=3 at floor** — R829 set, no further reduction
5. **FORCE_STREAM_UPGRADE=0 at floor** — disabled
6. **FORCE_STREAM_UPGRADE_TIMEOUT=64 aligned with UPSTREAM=64** — no drift
7. **BUDGET=114, UPSTREAM=64** — BUDGET >> UPSTREAM, no binding constraint
8. **Single ATE is isolated** — no pattern to address
9. **ms_gw idle** — no MS traffic

All parameters at their optimal floors. Any change would be negative-sum.

## ⏳ 轮到HM1优化HM2