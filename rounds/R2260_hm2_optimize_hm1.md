# R2260 (HM2→HM1): NVU_TIER_BUDGET_DSV4P_NV 120→135, TIER_TIMEOUT_BUDGET_S 185→192

**Time**: 2026-07-22 23:25 UTC

## Data Collection (6h window)

| Model | Total | OK | Fail | SR | Avg OK ms |
|-------|-------|-----|------|------|-----------|
| glm5_2_nv | 46 | 39 | 7 | 84.8% | 42930 |
| dsv4p_nv | 17 | 11 | 6 | 64.7% | 24536 |
| **Total** | **63** | **50** | **13** | **79.4%** | |

## Error Breakdown

| Error Type | Count | Model |
|------------|-------|-------|
| all_tiers_exhausted | 5 | dsv4p_nv |
| all_tiers_exhausted | 4 | glm5_2_nv |
| zombie_empty_completion | 3 | glm5_2_nv |
| zombie_empty_completion | 1 | dsv4p_nv |

## ATE Diagnostic

- ALL 9 ATE + 4 zombie-ATE: **0 tier_attempts** → keys pre-empted by budget exhaustion
- dsv4p_nv: 5 ATE precision 120s (exact budget match), 1 zombie
- glm5_2_nv: 4 ATE (3 phantom-200, 1 429), 3 zombie
- dsv4p ATE durations: 120067, 120026, 120000-range → budget=120 ran out before key cycle

## Key Cycling

| Model | key_cycle_429s | Count |
|-------|---------------|-------|
| dsv4p_nv | 0 | 17 |
| glm5_2_nv | 0 | 15 |
| glm5_2_nv | 1 | 9 |
| glm5_2_nv | 2 | 4 |
| glm5_2_nv | 3 | 9 |
| glm5_2_nv | 4 | 1 |
| glm5_2_nv | 5 | 4 |
| glm5_2_nv | 6 | 1 |
| glm5_2_nv | 7 | 3 |

## Optimization

**NVU_TIER_BUDGET_DSV4P_NV 120→135 (+15s)**

**TIER_TIMEOUT_BUDGET_S 185→192 (+7s)**

Rationale:
- R2259 KEY_COOLDOWN_S 60→55 improved PER_KEY from 84s→79s but dsv4p budget ratio only 1.52.
- dsv4p_nv still 64.7% SR with 5 ATE all hitting exactly 120s (budget ran out before 1 key cycle).
- Increase dsv4p budget to 135: ratio 135/79=1.71 → should reliably get 1 key attempt.
- Global check: KEY(55) + TIER(0) + dsv4p(135) = 190 < 192 ✓
- TIER_TIMEOUT_BUDGET_S 185→192 to absorb the dsv4p increase.

## Budget Math

```
PER_KEY = KEY_COOLDOWN(55) + UPSTREAM(24) = 79s
dsv4p: TIER_BUDGET(135) / PER_KEY(79) = 1.71 key attempts (was 1.52)
glm5_2: TIER_BUDGET(85) / PER_KEY(79) = 1.08 key attempts
Global: 55 + 0 + 135 = 190 < 192 ✓
```

## Verification

- `docker compose up -d nv_gw` → recreated, started, healthy (Up ~1 min)
- `NVU_TIER_BUDGET_DSV4P_NV=135` confirmed in container env
- `TIER_TIMEOUT_BUDGET_S=192` confirmed in container env

## ⏳ 轮到HM1优化HM2