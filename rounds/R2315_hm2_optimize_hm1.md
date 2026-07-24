# R2315 (HM2→HM1): Raise kimi_nv tier budget 130→170 — SR=36.4% worst, success p99=123s only 7s margin

**Date**: 2026-07-24 02:55 UTC (HM2 cron trigger)
**Author**: opc2_uname (HM2)
**Target**: HM1 (opc_uname @ 100.109.153.83:222)

## Context

R2314 was a NOP inspection round. R2310-R2313 config remained stable. This round finds a data-backed optimization opportunity on kimi_nv — the worst-performing model by success rate.

## Data Collected (24h window, nv_requests DB on HM1)

### 24h Model Summary

| Model | Total | OK | 502 | 429 | SR | Avg Duration | Max Duration |
|-------|-------|-----|-----|-----|-----|-------------|-------------|
| glm5_2_nv | 120 | 64 | 33 | 23 | 53.3% | 19687ms | 90939ms |
| kimi_nv | 55 | 20 | 35 | 0 | 36.4% | 119092ms | 370299ms |
| dsv4p_nv | 49 | 34 | 15 | 0 | 69.4% | 33177ms | 160041ms |

### 24h Error Breakdown

| Model | Error Type | Count | Avg Duration |
|-------|-----------|-------|-------------|
| glm5_2_nv | all_tiers_exhausted | 47 | 18134ms |
| kimi_nv | all_tiers_exhausted | 26 | 193765ms |
| glm5_2_nv | zombie_empty_completion | 9 | 16168ms |
| dsv4p_nv | all_tiers_exhausted | 8 | 40934ms |
| kimi_nv | zombie_empty_completion | 8 | 74004ms |
| dsv4p_nv | zombie_empty_completion | 7 | 31526ms |
| kimi_nv | NVStream_IncompleteRead | 1 | 75832ms |

### kimi_nv ATE Duration Distribution (24h, 26 all_tiers_exhausted)

| Duration Range | Count | Analysis |
|---------------|-------|----------|
| 124-127s | 7 | Budget-limited (130s budget barely exceeded) — wasted keys |
| 148-167s | 6 | Multiple key timeouts, budget exhausted mid-cycle |
| 370s | 4 | Full TIER_TIMEOUT_BUDGET=415 exhaustion (pre-R2309 behavior) |
| 89-114s | 5 | Zombie cascades eating into budget |
| <90s | 4 | Various fast-fails |

### kimi_nv Success Latency (24h, 20 successes)

- p50 ≈ 30s, p95 ≈ 85s, p99 = 123s (max 123145ms)
- R2309 set budget=130 based on p99=116.5s → **only 7s margin** (116.5→123s drift)
- At 130s/5keys=26s/key, UPSTREAM_TIMEOUT=24s → **2s per-key margin** (razor-thin)

## Analysis

kimi_nv SR=36.4% is the worst of all three models. The root cause is that R2309's budget=130 was set when success p99 was 116.5s. Since then, p99 has drifted to 123s — only 7s margin. With 5 keys at 26s/key and UPSTREAM_TIMEOUT=24s, each key has only 2s margin. Any NVCF latency fluctuation pushes a key over budget, causing premature ATE.

**The 124-127s ATE cluster (7 events)** is the smoking gun: these failures barely exceed the 130s budget. With budget=170, these would have room for 1-2 more key attempts, potentially converting some to successes.

**Safety check**: 170s < 415s TIER_TIMEOUT_BUDGET_S (safe). Other models unaffected (separate budget params). Peer-fb skip for kimi_nv not set (kimi uses independent function), so peer-fb remains available.

## Change

**Single parameter**: `NVU_TIER_BUDGET_KIMI_NV` 130→170

- 170s/5keys = 34s/key → 10s per-key UPSTREAM_TIMEOUT margin (5x improvement from 2s)
- Success p99=123s → 47s margin (from 7s)
- 124-127s ATE cluster gets 1+ extra key attempt
- 148-167s ATE cluster gets 2+ extra key attempts

## Verification

```
# Config applied
docker exec nv_gw env | grep NVU_TIER_BUDGET_KIMI_NV
→ NVU_TIER_BUDGET_KIMI_NV=170 ✓

# Container health
curl -s http://localhost:40006/health
→ {"status": "ok", ...} ✓

# Container restart
docker inspect --format '{{.State.StartedAt}} RC={{.State.ExitCode}}' nv_gw
→ 2026-07-24T02:54:10Z RC=0 ✓
```

## Risk Assessment

- **Low risk**: Only affects kimi_nv tier budget. Other models have separate budgets.
- 170s < 415s TIER_TIMEOUT_BUDGET_S (global ceiling) — safe.
- Peer-fb (60s R2308) + 502→caller ms_gw fallback unaffected.
- EMPTY_200_FASTBREAK=3 (R2303) still limits zombie cascades to 3 empty_200 before fastbreak.
- Worst case: kimi_nv ATE duration increases from ~130s to ~170s for budget-limited failures (extra 40s wait per ATE). But if 2-3 of the 7 budget-limited ATEs convert to successes, net user time saved.

## What Was NOT Changed (NOP Confirmation)

- **glm5_2_nv**: Peer-fb skip (R2310) working correctly. 429 storm cooldown (KEY_COOLDOWN=10, TIER_COOLDOWN=15) correctly fast-short-circuits in 6-8ms. No action needed.
- **dsv4p_nv**: Peer-fb skip (R2311) working correctly. Zombies at 252K-284K not in BIG_INPUT_MODELS (correct — model filter R2286 working). No action needed.
- **Big-input breaker**: THRESHOLD=250K (R2312), FAIL_N=4 (R2313). 2 consecutive zombies observed but <4 threshold → breaker CLOSED (correct, not yet triggered). No action needed.
- **All other params**: Stable, no env drift.

## Round History (kimi_nv budget)

- R2303: EMPTY_200_FASTBREAK 2→3 (paired with budget=200)
- R2309: Budget 200→130 (success p99=116.5s, 13.5s margin, cut 3rd key attempt)
- **R2315**: Budget 130→170 (success p99=123s, 7s margin → 47s margin, restore key attempts)

## ⏳ 轮到HM1优化HM2
