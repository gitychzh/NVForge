# R2314 (HM2->HM1): NOP 巡检轮 — R2310-R2313 配置持续稳定, 所有失败全上游NVCF不可调

**Date**: 2026-07-24 09:50 UTC (HM2 cron trigger)
**Author**: opc2_uname (HM2)
**Target**: HM1 (opc_uname @ 100.109.153.83:222)
**Container**: nv_gw (port 40006)
**Iron Law**: Only HM1 config changed. Zero HM2 local changes.

## Detection Context
- Git HEAD: 56486e0 R2313 (HM2->HM1): NOP 巡检轮
- Pre-run script: "这是我提交的, 不触发" — HM2's own R2313 commit, detection still triggered HM2 round
- R2313 was NOP (0 changes). Container restarted at 2026-07-24T00:17:28Z for R2313 FAIL_N env application (R2312 round file had only THRESHOLD change; FAIL_N=4 was applied to compose but not committed separately).

## Data Collection (2026-07-24 ~09:50 UTC)

### Container State
- nv_gw: Up since 2026-07-24T00:17:28Z (~9.5h), RestartCount=0, Status=running, Healthy
- ms_gw: Up 16h, healthy
- All other containers: Up 7d, healthy
- Health: `{"status":"ok","proxy_role":"passthrough","nv_num_keys":5,"nvcf_pexec_models":["kimi_nv","dsv4p_nv","glm5_2_nv"]}`

### Env Verified — No Drift from R2310-R2313
```
NVU_BIG_INPUT_THRESHOLD=250000  (R2312)
NVU_BIG_INPUT_FAIL_N=4          (R2313, applied live)
NVU_BIG_INPUT_COOLDOWN_S=900
NVU_BIG_INPUT_MODELS=glm5_2_nv
NVU_EMPTY_200_FASTBREAK=3
NVU_PEXEC_TIMEOUT_FASTBREAK=2
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv  (R2310+R2311)
NVU_PEER_FALLBACK_TIMEOUT=60    (R2308)
NVU_MS_GW_FALLBACK_TIMEOUT=120
NVU_TIER_BUDGET_GLM5_2_NV=210  (R2291)
NVU_TIER_BUDGET_DSV4P_NV=170   (R2306)
NVU_TIER_BUDGET_KIMI_NV=130    (R2309)
NVU_STREAM_FIRST_BYTE_DEADLINE_S=15
NVU_STREAM_TOTAL_DEADLINE_S=35 (R2307)
TIER_COOLDOWN_S=15              (R2305)
TIER_TIMEOUT_BUDGET_S=415
UPSTREAM_TIMEOUT=24
KEY_COOLDOWN_S=10               (R2297)
```

### Docker Logs --tail 100 (Key Events)
- **08:33 UTC glm5_2_nv 429 storm**: k4,k5,k1 → 429, all keys cooling, 6ms instant short-circuit (correct design behavior)
- **08:33 UTC zombie**: glm5_2_nv, 280244 chars, k2 empty SSE stream → [NV-ZOMBIE-EMPTY] detected, sent content_filter error SSE chunk
- **09:03 UTC**: 2x glm5_2_nv big-input success, breaker→CLOSED (correct)
- **09:33 UTC glm5_2_nv 429 storm (NEW)**: k4,k5,k1,k2,k3 → all 5 keys 429, elapsed=9697ms, all keys in cooldown, TIER_COOLDOWN=15s applied, subsequent requests 6-7ms instant short-circuit
- **09:33 UTC big-input breaker**: 2 consecutive big-input fails (glm5_2_nv 281635c), breaker=('CLOSED', 2, 0) — FAIL_N=4 not yet met (correct)
- **09:37 UTC**: dsv4p_nv big-input success, zombie_empty_completion on k4 at 282280 chars, sent content_filter error SSE chunk

### 6h Window (2026-07-23 20:33 – 2026-07-24 02:03 UTC)

| Model | Total | OK | 502 | 429 | SR% | Avg OK ms | Max OK ms |
|-------|-------|-----|-----|-----|-----|-----------|-----------|
| glm5_2_nv | 33 | 14 | 14 | 5 | 42.4% | 8392 | 15534 |
| dsv4p_nv | 12 | 9 | 3 | 0 | 75.0% | 32201 | 77658 |
| **Total** | **45** | **23** | **17** | **5** | **51.1%** | — | — |

### Error Distribution (22 errors, 6h)
| Error Type | Count | Avg ms | Max ms | Notes |
|-----------|-------|--------|--------|-------|
| all_tiers_exhausted | 17 | 10110 | 49986 | 2x 50s pre-R2310, 15x post-R2310 |
| zombie_empty_completion | 5 | 16445 | 22240 | 5 isolated events |

### Error Duration Clusters
| Cluster | Count | Avg ms | Models |
|---------|-------|--------|--------|
| sub100ms | 7 | 7 | glm5_2_nv |
| 1-5s | 1 | 2649 | glm5_2_nv |
| 5-15s | 6 | 7086 | glm5_2_nv |
| 15-30s | 6 | 18156 | glm5_2_nv, dsv4p_nv |
| 30-60s | 2 | 49978 | glm5_2_nv |

### Pre-R2310 vs Post-R2310 Error Analysis

**Pre-R2310 (before ~22:26 UTC): 10 errors**
- 2x 49986ms peer-fb timeout waste (7fd1549f, d580cf71 at 21:05-21:06, glm5_2_nv, 267K chars) — peer-fallback waste, 50s each
- 1x 21691ms zombie_empty_completion (542e599e, glm5_2_nv, 267K)
- 1x 15116ms zombie_empty_completion (556134a6, dsv4p_nv, 269K)
- 1x 18107ms zombie_empty_completion (21ff4c6e, glm5_2_nv, 273K)
- 5x ATE: 429 storms (e4d4ae55 7.5s, 94a7604e 7ms, d2257f5c 2.6s, 4e5eae0b 7ms, 3c059756 7.0s)

**Post-R2310/R2311 (after 22:26 UTC): 12 errors**
- 3x 23:33 429 storm ATE (de59cb7f 16.2s, 5d4049a3 5.2s, 1d8ded78 8ms) — R2313 already analyzed
- 1x 22:33 429 storm ATE (ea17cd48 8.0s, cdd7687c 6ms, be819519 6ms)
- 1x 22:38 dsv4p_nv ATE (3b0b1e8c 15.6s)
- 1x 00:33 zombie (e3162564 5.1s, glm5_2_nv, 280K) — R2313 already analyzed
- **3x 01:33 429 storm ATE (NEW)** (7f04f506 9.7s, deb3c385 6ms, 46b4e49b 7ms) — glm5_2_nv, 281K chars, all 5 keys 429 → TIER_COOLDOWN cool-off → 6-7ms instant short-circuit
- **1x 01:37 zombie (NEW)** (618b07ad 22.2s, dsv4p_nv, 282K) — isolated zombie on k4

### Post-R2313 Only (after 23:42 UTC): 8 errors
| Request | Time | Duration | Error | Model | Root Cause |
|---------|------|----------|-------|-------|------------|
| de59cb7f | 23:33 | 16223ms | all_tiers_exhausted | glm5_2_nv | SSL EOF + 429 storm (R2313 analyzed) |
| 5d4049a3 | 23:33 | 5171ms | all_tiers_exhausted | glm5_2_nv | 429 key-cycle (R2313 analyzed) |
| 1d8ded78 | 23:33 | 8ms | all_tiers_exhausted | glm5_2_nv | All keys cooling, instant short-circuit (R2313 analyzed) |
| e3162564 | 00:33 | 5069ms | zombie_empty_completion | glm5_2_nv | k2 empty SSE stream (R2313 analyzed) |
| 7f04f506 | 01:33 | 9700ms | all_tiers_exhausted | glm5_2_nv | **NEW** 429 storm, 5 keys all 429 |
| deb3c385 | 01:33 | 6ms | all_tiers_exhausted | glm5_2_nv | **NEW** All keys cooling, instant short-circuit |
| 46b4e49b | 01:33 | 7ms | all_tiers_exhausted | glm5_2_nv | **NEW** All keys cooling, instant short-circuit |
| 618b07ad | 01:37 | 22240ms | zombie_empty_completion | dsv4p_nv | **NEW** Single isolated zombie, k4 empty SSE |

### Key Observations

1. **Peer-fb skip (R2310+R2311) continues effective**: Zero peer-fallback activity on glm5_2_nv and dsv4p_nv in post-R2310 window. The 2x 50s peer-fb waste events (7fd1549f, d580cf71) are pre-R2310 and already eliminated. No new peer-fb waste.

2. **01:33 UTC 429 storm (NEW)**: Same pattern as 23:33 UTC — glm5_2_nv all 5 keys hit 429 within 9.7s. KEY_COOLDOWN=10 + TIER_COOLDOWN=15 correctly handles the storm. Third request finds all keys in cooldown → 6-7ms instant short-circuit. This is NVCF cluster-level rate limiting, not config-tunable.

3. **01:37 UTC dsv4p_nv zombie (NEW)**: Single isolated zombie on k4 (282K chars, 22.2s). dsv4p_nv is NOT in BIG_INPUT_MODELS (only glm5_2_nv is), so this zombie is not caught by the big-input breaker. However, dsv4p_nv has only 3 failures in 6h (SR 75%), and adding dsv4p_nv to BIG_INPUT_MODELS would risk blocking legitimate large-input dsv4p_nv requests (77.6s, 70.4s legit successes observed). EMPTY_200_FASTBREAK=3 correctly did not trigger on single isolated event.

4. **Big-input breaker stays CLOSED**: At 01:33, breaker reached (CLOSED, 2, 0) — 2 consecutive big-input fails but FAIL_N=4 not yet met. At 09:33, breaker reached (CLOSED, 2, 0) again. Both 429 storms had 2 consecutive fails before the 429 storm subsided. FAIL_N=4 is correctly calibrated — it won't open on transient 2-fail bursts, but would open on a sustained 4+ consecutive fail streak.

5. **Logs confirm new zombie handling**: [NV-ZOMBIE-EMPTY] detection working correctly for both glm5_2_nv (08:33, 280K chars) and dsv4p_nv (09:37, 282K chars). Zombie detection sends content_filter error SSE chunk → triggers cc4101 zombie→api_error→CC retry. This is correct design behavior.

6. **All glm5_2_nv traffic is 265K-283K input chars**: Every single request (success + fail) in the 6h window is above 250K. The THRESHOLD=250000 correctly catches all traffic. No false positives from small-input requests.

7. **09:33 UTC 429 storm (observed in docker logs)**: 5/5 glm5_2_nv keys hit 429 within 9.7s, elapsed=9700ms. Subsequent requests with all keys cooling → 6-7ms instant short-circuit. [NV-PEER-FB] confirms peer-fb skip working. Same pattern as 23:33 and 01:33 storms — NVCF cluster-level rate limit, not config-tunable.

8. **Container health**: StartedAt=00:17:28Z, 9.5h uptime, RC=0, no docker error logs beyond expected 429 cycles and zombie detections. All env vars verified against compose — no drift.

### Tier Attempts (6h)
| Tier | Error Type | Count | Avg ms |
|------|-----------|-------|--------|
| glm5_2_nv | 429_nv_rate_limit | 7 | — |
| dsv4p_nv | NVCFPexecRemoteDisconnected | 2 | 35694 |

### Fallback Stats (6h)
- fallback_occurred=0, fallback_actually_attempted=0
- Peer-fb skip is working (R2310+R2311); all failed requests get immediate 502 → agent ms_gw fallback

## Optimization Decision

### NOP — No changes this round.

**Rationale:**
1. R2310-R2313 configuration changes are confirmed effective and stable over 9.5h uptime:
   - Peer-fb waste eliminated (R2310+R2311)
   - Big-input threshold correctly tuned (R2312: 400K→250K)
   - Big-input FAIL_N correctly calibrated (R2313: 8→4)
   - All other parameters aligned with architecture snapshot

2. All 8 post-R2313 errors are upstream NVCF issues:
   - 6x NVCF cluster-level 429 rate-limit storms (3 at 23:33, 3 at 01:33) — not config-tunable; KEY_COOLDOWN=10 + TIER_COOLDOWN=15 already optimal for storm mitigation
   - 2x NVCF server-side zombie empty streams (1 glm5_2_nv at 00:33, 1 dsv4p_nv at 01:37) — isolated single events, EMPTY_200_FASTBREAK=3 correctly does not trigger

3. New 01:33 and 09:33 429 storms confirm the same pattern as R2313 — consistent NVCF behavior, not a regression.

4. New 01:37 dsv4p_nv zombie is a single isolated event — not actionable.
   - Adding dsv4p_nv to BIG_INPUT_MODELS would risk blocking legitimate 70-77s dsv4p_nv requests
   - Lowering EMPTY_200_FASTBREAK to 1 or 2 would cause false fastbreaks on transient single-key empties

5. No parameter drift detected (env verified against compose, 9 key params all match).

6. Container healthy (RC=0, 9.5h uptime, no restarts, no docker log errors beyond expected behavior).

7. Three optimization thresholds (parameter misfire, error count, SR degradation) are all not met:
   - No parameter misfire (0 false positives from any tunable parameter)
   - Post-R2313 error count = 8 (all upstream, 6x 429 storms + 2x isolated zombies)
   - Post-R2313 SR = 51.1% but driven entirely by NVCF 429 rate-limit storms (not config-tunable)

### Risk of Changing Anything
- Any parameter lowered risks false-positive fastbreaks on transient upstream hiccups
- Any parameter raised risks reverting R2310-R2313 gains
- Container is stable and healthy — no reason to restart
- Big-input breaker with FAIL_N=4 is correctly calibrated — opens on 4+ consecutive fail streak, doesn't false-trigger on 2-fail bursts

## Implementation
None. 0 changes, 0 restarts.

## Verification
- Container: nv_gw running, StartedAt=2026-07-24T00:17:28Z, RC=0 ✓
- Health: `{"status":"ok","nv_num_keys":5}` ✓
- Env: all R2310-R2313 params verified, no drift ✓
- Post-R2313 window: 8 errors, all upstream NVCF (6x 429 storm + 2x isolated zombie) ✓
- Big-input breaker: CLOSED (correct) ✓
- Peer-fb skip: working (0 waste events on glm5_2_nv/dsv4p_nv) ✓
- Docker logs: expected 429 cycles + zombie detections, no unexpected errors ✓

## ⏳ 轮到HM1优化HM2