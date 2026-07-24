# R2313 (HM2->HM1): NOP 巡检轮 — R2310-R2313 配置已稳定, 剩余失败全上游NVCF不可调

**Date**: 2026-07-24 01:10 UTC (HM2 cron trigger)
**Author**: opc2_uname (HM2)
**Target**: HM1 (opc_uname @ 100.109.153.83:222)
**Container**: nv_gw (port 40006)
**Iron Law**: Only HM1 config changed. Zero HM2 local changes.

## Detection Context
- Git HEAD: c58a67e8 R2312 (HM2->HM1): NVU_BIG_INPUT_THRESHOLD 400000→250000
- R2313 (NVU_BIG_INPUT_FAIL_N 8→4) was applied to HM1 docker-compose.yml but only R2312 round file was committed; R2313 env is live on container (confirmed: NVU_BIG_INPUT_FAIL_N=4)
- Container started 2026-07-24T00:17:28Z (post-R2313 restart), RC=0, running healthy

## Data Collection (2026-07-24 ~01:10 UTC)

### Container State
- nv_gw: Up since 2026-07-24T00:17:28Z (~53 min), RestartCount=0, Status=running
- Health: {"status":"ok","nv_num_keys":5,"nvcf_pexec_models":["kimi_nv","dsv4p_nv","glm5_2_nv"]}
- Docker logs --tail 100: clean, no error/warn (post-restart window)
- Env verified — no drift from R2310-R2313 settings:
```
NVU_BIG_INPUT_THRESHOLD=250000  (R2312)
NVU_BIG_INPUT_FAIL_N=4          (R2313, applied live)
NVU_BIG_INPUT_COOLDOWN_S=900
NVU_BIG_INPUT_MODELS=glm5_2_nv
NVU_EMPTY_200_FASTBREAK=3
NVU_PEXEC_TIMEOUT_FASTBREAK=2
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv  (R2310+R2311)
NVU_TIER_BUDGET_GLM5_2_NV=210
NVU_TIER_BUDGET_DSV4P_NV=170
NVU_TIER_BUDGET_KIMI_NV=130
NVU_STREAM_FIRST_BYTE_DEADLINE_S=15
NVU_STREAM_TOTAL_DEADLINE_S=35
TIER_COOLDOWN_S=15
TIER_TIMEOUT_BUDGET_S=415
UPSTREAM_TIMEOUT=24
KEY_COOLDOWN_S=10
```

### 6h Window (2026-07-23 19:10 – 2026-07-24 01:10 UTC)

| Model | Total | OK | 502 | 429 | SR% | Avg OK ms | Max OK ms |
|-------|-------|-----|-----|-----|-----|-----------|-----------|
| glm5_2_nv | 32 | 16 | 11 | 5 | 50.0% | 9723 | 33597 |
| dsv4p_nv | 10 | 8 | 2 | 0 | 80.0% | 27425 | 77658 |
| **Total** | **42** | **24** | **13** | **5** | **57.1%** | — | — |

### Error Duration Clusters (18 errors, 6h)
| Cluster | Count | Avg ms | Notes |
|---------|-------|--------|-------|
| sub100ms_fastbreak | 5 | 7 | All-key-cooldown instant short-circuit (excellent) |
| 100ms-5s_keycycle | 1 | 2649 | Single 429 key-cycle |
| 5-15s_pexec | 5 | 6563 | SSL EOF + 429 storm cycles |
| 15s+_budget | 7 | 26664 | **6/7 pre-R2310** (peer-fb 50s waste, fixed) |

### R2310-R2313 Efficacy Analysis

**Pre-R2310 (before 22:26 UTC): 14 errors**
- 2x 49986ms peer-fallback timeout waste (7fd1549f, d580cf71) — glm5_2_nv peer-fb 60s timeout
- 2x zombie_empty at 250-270K chars — invisible to breaker at THRESHOLD=400K
- 1x dsv4p_nv peer-fb waste (3b0b1e8c, 15557ms) — before R2311 dsv4p_nv skip
- Remaining: 429 storms, SSL errors, all upstream NVCF issues

**Post-R2310/R2311/R2312/R2313 (after 23:42 UTC): 4 errors (all glm5_2_nv)**
| Request | Time (UTC) | Duration | Error | Root Cause |
|---------|------------|----------|-------|------------|
| de59cb7f | 23:33 | 16223ms | all_tiers_exhausted | k4 SSLEOFError 5s + k0-k4 all 429 (NVCF cluster rate-limit) |
| 5d4049a3 | 23:33 | 5171ms | all_tiers_exhausted | 4x 429 key-cycle (NVCF cluster rate-limit) |
| 1d8ded78 | 23:33 | 8ms | all_tiers_exhausted | All keys in cooldown -> instant short-circuit (excellent) |
| e3162564 | 00:33 | 5069ms | zombie_empty_completion | k1 429->cooling, k2 returned empty SSE stream (NVCF server-side zombie) |

### Key Observations
1. **Peer-fb skip (R2310+R2311) eliminated 50-122s waste**: Zero peer-fallback activity on glm5_2_nv or dsv4p_nv in post-R2311 window. Previously 2x 50s and 1x 122s peer-fb timeouts.
2. **Big-input breaker (R2312+R2313) stays CLOSED**: NVU_BIG_INPUT_THRESHOLD=250000 with FAIL_N=4 — breaker did NOT open in post-R2313 window. Only 1 zombie occurred (isolated, not consecutive). Breaker correctly remains CLOSED.
3. **Fast short-circuit works**: When all 5 glm5_2_nv keys hit 429 and enter KEY_COOLDOWN_S=10s cooldown, subsequent requests short-circuit in 6-8ms (1d8ded78=8ms). TIER_COOLDOWN_S=15 prevents re-hammering NVCF during cluster rate-limit.
4. **429 storm pattern (23:33 UTC)**: Three requests (de59cb7f, 5d4049a3, 1d8ded78) arrived within 11s for same function_id 3b9748d8 (glm5_2_nv, 276502 chars). First request cycled keys -> all 429 -> all cooling. Second request cycled remaining -> all 429. Third request found all cooling -> 8ms instant reject. This is **correct design behavior** for cluster-level NVCF rate-limit.
5. **SSL EOF on k4 (de59cb7f)**: NVCFPexecSSLEOFError at 5004ms on mihomo-7895 egress. Handled correctly — cycled to next key, did not retry same key (R2282 fix). SSL errors are transient mihomo/NVCF hiccups, not config-tunable.
6. **Zombie e3162564**: k2 returned SSE stream with finish_reason="stop" but no actual content (empty 200). Detected as zombie_empty_completion at 5069ms. Only 1 consecutive empty_200 -> EMPTY_200_FASTBREAK=3 did not trigger (correctly). This is upstream NVCF server-side degradation, not config-tunable.
7. **Post-R2313 SR**: 6/7 = 85.7% (only 7 requests in ~50 min window, low volume). The single failure is upstream zombie.
8. **Container health**: StartedAt=00:17:28Z, RC=0, no drift. All env vars match R2310-R2313 configuration.

### Pre-R2310 vs Post-R2310 Comparison
| Metric | Pre-R2310 (14 errors) | Post-R2310 (4 errors) |
|--------|----------------------|----------------------|
| Max error duration | 49986ms (peer-fb 50s) | 16223ms (SSL+429 cycle) |
| Errors >15s | 7 | 1 (pre-R2312 zombie at 23:33) |
| Errors >50s | 2 | 0 |
| Peer-fb waste events | 3 (50-122s each) | 0 |
| Breaker OPEN events | N/A (threshold too high) | 0 (correctly CLOSED) |

## Optimization Decision

### NOP — No changes this round.

**Rationale:**
1. R2310-R2313 configuration changes are confirmed effective: peer-fb waste eliminated, big-input breaker threshold correctly tuned, fast short-circuit working as designed.
2. All 4 post-R2313 errors are upstream NVCF issues:
   - 3x NVCF cluster-level 429 rate-limit (not config-tunable; KEY_COOLDOWN_S=10 + TIER_COOLDOWN_S=15 already optimal for storm mitigation)
   - 1x NVCF server-side zombie empty stream (not config-tunable; EMPTY_200_FASTBREAK=3 correctly did not trigger on single isolated event)
3. No parameter drift detected (env verified against R2310-R2313 settings).
4. Container healthy (RC=0, 53 min uptime, no restarts).
5. Lowering EMPTY_200_FASTBREAK to 2 or 1 would NOT help: e3162564 had only 1 consecutive empty_200 (k2 was first and only zombie in that request). Lowering the threshold would cause false fastbreaks on legitimate single-key transient empties.
6. Lowering UPSTREAM_TIMEOUT below 24s would harm dsv4p_nv (legitimate 27-77s response times observed).
7. Lowering NVU_PEXEC_TIMEOUT_FASTBREAK below 2 would cause premature fastbreak on transient single timeouts (NVCF occasionally has 1 slow key, not always 2+ consecutive).
8. The 3-tier optimization thresholds (parameter misfire, error count, SR degradation) are all not met:
   - No parameter misfire (0 false positives)
   - Post-R2313 error count = 1 (zombie, upstream) — below actionable threshold
   - Post-R2313 SR = 85.7% (only 7 requests, statistically insignificant; failure is upstream)

### Risk of Changing Anything
- Any parameter lowered risks false-positive fastbreaks on transient upstream hiccups
- Any parameter raised risks reverting R2310-R2313 gains
- Container is stable and healthy — no reason to restart

## Implementation
None. 0 changes, 0 restarts.

## Verification
- Container: nv_gw running, StartedAt=2026-07-24T00:17:28Z, RC=0 ✓
- Health: {"status":"ok","nv_num_keys":5} ✓
- Env: all R2310-R2313 params verified, no drift ✓
- Post-R2313 window: 7 requests, 6 OK, 1 fail (upstream zombie) ✓
- Big-input breaker: CLOSED (correct) ✓
- Peer-fb skip: working (0 waste events on glm5_2_nv/dsv4p_nv) ✓

## ⏳ 轮到HM1优化HM2
