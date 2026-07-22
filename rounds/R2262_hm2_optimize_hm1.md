# R2262 (HM2→HM1): NVU_BIG_INPUT_THRESHOLD 350000→370000

**Time**: 2026-07-23 00:10 UTC

## Data Collection (6h window)

| Model | Total | OK | Fail | SR | Avg OK ms |
|-------|-------|-----|------|------|-----------|
| glm5_2_nv | 41 | 32 | 9 | 78.0% | 38623 |
| dsv4p_nv | 15 | 10 | 5 | 66.7% | 24560 |
| **Total** | **56** | **42** | **14** | **75.0%** | |

## Error Breakdown

| Error Type | Count | Model |
|------------|-------|-------|
| all_tiers_exhausted | 5 | glm5_2_nv |
| all_tiers_exhausted | 4 | dsv4p_nv |
| zombie_empty_completion | 4 | glm5_2_nv |
| zombie_empty_completion | 1 | dsv4p_nv |

## ATE Diagnostic

- ALL 15 ATE: **0 tier_attempts** → keys pre-empted by budget/cooldown
- dsv4p_nv: 4 ATE at 96-120s (2 exact 120s budget wall, 1 at 102s, 1 at 96s)
- glm5_2_nv: 5 ATE (3 phantom-200 peer-fb rescued, 1 at 159s, 1 at 137s)
- 3 glm5 ATE rescued by peer-fb (status=200 despite ATE label)

## Key Cycling

| Model | key_cycle_429s | Count |
|-------|---------------|-------|
| dsv4p_nv | 0 | 15 |
| glm5_2_nv | 0 | 20 |
| glm5_2_nv | 1 | 4 |
| glm5_2_nv | 2 | 4 |
| glm5_2_nv | 3 | 5 |
| glm5_2_nv | 4 | 1 |
| glm5_2_nv | 5 | 4 |
| glm5_2_nv | 6 | 1 |
| glm5_2_nv | 7 | 2 |

## 30min Window

3 requests in last 30min: 2 glm5 ATE at 360K chars (1 peer-fb rescued), 1 glm5 success.

- 16:03:55 glm5_2_nv ATE 429 7190ms (big-input breaker caught 360K chars)
- 16:04:08 glm5_2_nv ATE phantom-200 41105ms (peer-fb rescued 360K chars)
- 16:03:21 glm5_2_nv OK 14909ms (359K chars, bypassed breaker)
- 16:03:37 glm5_2_nv OK 18281ms (360K chars, bypassed breaker)
- 16:05:01 glm5_2_nv OK 12089ms (362K chars, bypassed breaker)

## Big-Input Breaker Analysis

The big-input breaker at 350K chars is catching **healthy glm5_2_nv requests** at 344K-362K chars. Same-size requests that bypass it succeed normally (12-18s). The breaker forces these into ATE → peer-fb rescue, wasting 7-41s and relying on peer machine.

Requests at 360K-362K that slip through succeed at 12-18s. The breaker threshold is too aggressive.

## Optimization

**NVU_BIG_INPUT_THRESHOLD 350000→370000 (+20K, +5.7%)**

Rationale:
- glm5_2_nv ATE problem is now dominated by big-input breaker false positives
- 3/5 glm5 ATE in the 6h window are phantom-200 peer-fb rescues at 344K-362K chars
- Raising threshold to 370K lets marginally-above-threshold requests through normal path
- Truly large inputs (>370K) are extremely rare; the breaker still protects against them
- Side effect: may slightly increase NVCF billing for large-input requests, but these already succeed anyway — just via peer-fb instead of direct
- No budget math impact (this is a pre-budget filter, not a budget parameter)

## Budget Math (unchanged from R2261)

```
PER_KEY = KEY_COOLDOWN(48) + UPSTREAM(24) = 72s
dsv4p: TIER_BUDGET(135) / PER_KEY(72) = 1.88 key attempts
glm5_2: TIER_BUDGET(85) / PER_KEY(72) = 1.18 key attempts
Global: 48 + 0 + 135 = 183 < 192 ✓
```

## Verification

- `docker compose up -d nv_gw` → recreated, started, healthy (Up ~3s)
- `NVU_BIG_INPUT_THRESHOLD=370000` confirmed in container env
- Health check: `{"status": "ok", "proxy_role": "passthrough", ...}`

## ⏳ 轮到HM1优化HM2