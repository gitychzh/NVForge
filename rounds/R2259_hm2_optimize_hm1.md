# R2259 (HM2→HM1): KEY_COOLDOWN_S 60→55

**Time**: 2026-07-22 23:09 UTC

## Data Collection (6h window)

| Model | Total | OK | Fail | SR | Avg ms |
|-------|-------|-----|------|------|--------|
| glm5_2_nv | 46 | 39 | 7 | 84.8% | 47652 |
| dsv4p_nv | 16 | 11 | 5 | 68.8% | 41804 |
| **Total** | **62** | **50** | **12** | **80.6%** | |

## Error Breakdown

| Error Type | Count | Model |
|------------|-------|-------|
| all_tiers_exhausted | 8 | glm5(6), dsv4p(2) |
| zombie_empty_completion | 4 | glm5(3), dsv4p(1) |

## ATE Diagnostic

- ALL 8 ATE: **0 tier_attempts** → keys pre-empted by cooldown
- 3 glm5 ATE phantom-200 (status=200 despite ATE), 1 glm5 ATE status=429
- 2 dsv4p ATE 502 from NVCF upstream timeout
- 2 glm5 ATE 502 from NVCF upstream timeout

## Key Cycling

- glm5_2_nv: 31/46 (67%) with key_cycle_429s, avg 3 cycles
- dsv4p_nv: 0 key cycling

## Tier Attempts

| tier | error_type | count |
|------|------------|-------|
| glm5_2_nv | pexec_timeout | 29 |
| glm5_2_nv | 429_nv_rate_limit | 26 |
| glm5_2_nv | pexec_success | 24 |
| glm5_2_nv | pexec_429 | 14 |

## 30min Window

0 real errors. 3 requests: 1 dsv4p ATE (peer-fb rescued), 1 glm5 ATE phantom-200 (peer-fb rescued), 1 glm5 success.

## Optimization

**KEY_COOLDOWN_S 60→55 (-5s)**

Rationale:
- PER_KEY=60+24=84s was too high. dsv4p budget 120/84=1.43 key attempts → only 1 usable key before budget exhausted.
- At 55s: PER_KEY=55+24=79s. dsv4p: 120/79=1.52 key attempts. Still tight but better.
- Global check: KEY(55)+TIER(0)+dsv4p(120)=175 < 185 TIER_TIMEOUT_BUDGET ✓
- Small step, reversible. If 429 storm returns, can revert.

## Verification

- `docker compose up -d nv_gw` → recreated, started, healthy (Up 8s)
- `KEY_COOLDOWN_S=55` confirmed in container env

## Budget Math

```
PER_KEY = KEY_COOLDOWN(55) + UPSTREAM(24) = 79s
dsv4p: TIER_BUDGET(120) / PER_KEY(79) = 1.52 key attempts
glm5_2: TIER_BUDGET(85) / PER_KEY(79) = 1.08 key attempts
Global: 55 + 0 + 120 = 175 < 185 ✓
```

## ⏳ 轮到HM1优化HM2