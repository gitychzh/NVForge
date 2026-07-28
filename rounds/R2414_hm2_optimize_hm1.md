# R2414 (HM2 to HM1): NVU_EMPTY_200_FASTBREAK 1→2

## Data Before Change (HM1, 6h ending 09:00 CST)

### nv_gw health
Container nv_gw up healthy. Key params: EMPTY_200_FASTBREAK=1, PEXEC_TIMEOUT_FASTBREAK=3, UPSTREAM_TIMEOUT=32, KEY_COOLDOWN_S=25, NVU_TIER_BUDGET_KIMI_NV=370.

### DB 6h (nv_requests)

| mapped_model | total | ok | err | SR%   | avg_ok_s | avg_err_s |
|-------------|-------|----|-----|-------|----------|-----------|
| glm5_2_nv   | 31    | 23 |  8  | 74.2% |   12.0   |    26.2   |
| kimi_nv     | 25    | 11 | 14  | 44.0% |   23.9   |    98.0   |

### Error taxonomy (nv_requests, 6h)
| mapped_model | error_type              | count |
|-------------|-------------------------|-------|
| kimi_nv      | all_tiers_exhausted     |    14 |
| glm5_2_nv    | zombie_empty_completion |     6  |
| glm5_2_nv    | all_tiers_exhausted     |     2  |

### Log evidence (08:59 CST)
```
[NV-EMPTY-200] k3 (kimi_nv) → 200 Content-Length:0 (stream)
[NV-EMPTY-CYCLE] tier=kimi_nv k3 empty 200, marked cooling 25.0s, cycling
[NV-EMPTY-FASTBREAK] tier=kimi_nv 1 consecutive empty_200 ≥ threshold 1, fast-break (saved remaining keys)
[NV-ALL-TIERS-FAIL] All 1 tiers failed (ring tiers tried: ['kimi_nv']), elapsed=61869ms, ABORT-NO-FALLBACK
```

### Analysis
- kimi_nv SR crashed to 44.0% (R2413 was 62.7% pre-R2412), 14 ATE avg 98s
- ATE all tiers_tried=5, key_cycle=0 → budget-clear ATE, not pre-tier kills. Budget 370s sufficient.
- Root cause: `NVU_EMPTY_200_FASTBREAK=1` kills 2 remaining keys (k4, k5) on a single transient empty_200 at k3
- 08:59 log: one empty_200 on k3 → FASTBREAK=1 kills k4+k5 (50% remaining keys), wastes 61s total
- empty_200 is key-specific transient (historical SR 80%+), not a tier-wide signal
- FASTBREAK=1 was R2404 to avoid cascading empty_200 wasting 3 keys; now over-corrected

## Change: NVU_EMPTY_200_FASTBREAK 1→2
- +1 empty_200 threshold before fast-break triggers
- Gives k4+k5 recovery runway when only k3 is empty_200
- Still protects against true cascades (3 consecutive empty_200)
- Budget impact: +1 key × ~62s = +62s → still within 370s budget (370-3×62=184s remaining)
- Single param; iron law: only HM1

## After Change
- docker compose up -d nv_gw restarted
- NVU_EMPTY_200_FASTBREAK=2 verified in docker-compose.yml

## ⏳ 轮到HM1优化HM2