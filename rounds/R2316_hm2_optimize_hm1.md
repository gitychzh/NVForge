# R2316 (HM2→HM1): NOP 巡检轮 — R2315 kimi_nv budget=170 待观察, 零可配置故障

**Date**: 2026-07-24 11:01 UTC (HM2 cron trigger)
**Author**: opc2_uname (HM2)
**Target**: HM1 (opc_uname @ 100.109.153.83:222)
**Container**: nv_gw (port 40006)
**Iron Law**: Only HM1 config changed. Zero HM2 local changes.

## Detection Context
- Git HEAD: R2315 (HM2→HM1): kimi_nv tier budget 130→170
- Pre-run script: "这是我提交的, 不触发" — HM2's own R2315 commit, detection still triggered HM2 round
- R2315 deployed budget=170, container restarted at 2026-07-24T02:54:10Z

## Data Collection (2026-07-24 ~11:01 UTC)

### Container State
- nv_gw: Up since 2026-07-24T02:54:10Z (~8h), RestartCount=0, Status=running, Healthy
- ms_gw: Up 18h, healthy
- All other containers: Up 7d, healthy
- Health: `{"status":"ok","proxy_role":"passthrough","nv_num_keys":5,"nvcf_pexec_models":["kimi_nv","dsv4p_nv","glm5_2_nv"]}`

### Env Verified — No Drift from R2315
```
NVU_TIER_BUDGET_KIMI_NV=170      (R2315, verified)
NVU_TIER_BUDGET_GLM5_2_NV=210    (R2291)
NVU_TIER_BUDGET_DSV4P_NV=170     (R2306)
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
TIER_TIMEOUT_BUDGET_S=415
UPSTREAM_TIMEOUT=24
KEY_COOLDOWN_S=10                (R2297)
TIER_COOLDOWN_S=15               (R2305)
NVU_PEXEC_TIMEOUT_FASTBREAK=2    (R2284)
NVU_EMPTY_200_FASTBREAK=3        (R2303)
NVU_PEER_FALLBACK_TIMEOUT=60     (R2308)
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv  (R2310+R2311)
NVU_BIG_INPUT_THRESHOLD=250000   (R2312)
NVU_BIG_INPUT_FAIL_N=4           (R2313)
NVU_BIG_INPUT_COOLDOWN_S=900
NVU_BIG_INPUT_MODELS=glm5_2_nv
NVU_STREAM_FIRST_BYTE_DEADLINE_S=15
NVU_STREAM_TOTAL_DEADLINE_S=35   (R2307)
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
```

### 24h Model Summary (pre-R2315 + post-R2315 combined)
| Model | Total | OK | 502 | 429 | SR | Avg OK | Max OK |
|-------|-------|-----|-----|-----|-----|--------|--------|
| glm5_2_nv | 122 | 64 | 35 | 23 | 52.5% | 21.3s | 65.3s |
| kimi_nv | 55 | 20 | 35 | 0 | 36.4% | 42.2s | 123.1s |
| dsv4p_nv | 47 | 34 | 13 | 0 | 72.3% | 31.7s | 90.7s |

### 24h Error Breakdown
| Model | Error Type | Count | Avg Duration |
|-------|-----------|-------|-------------|
| glm5_2_nv | all_tiers_exhausted | 20 | 16.1s |
| glm5_2_nv | zombie_empty_completion | 2 | 11.6s |
| dsv4p_nv | zombie_empty_completion | 3 | 29.8s |
| dsv4p_nv | all_tiers_exhausted | 2 | 92.8s |

### kimi_nv 24h Detailed Analysis
- **55 total**: 20 OK (36.4% SR), 35 failures
- **Success latency**: p50=30.9s, p95=89.7s, p99=116.5s, max=123.1s
- **Failures**: 26 ATE (all_tiers_exhausted, upstream_type=NULL, **0 tier_attempts**), 8 zombie_empty_completion, 1 NVStream_IncompleteRead
- **ATE duration distribution**: 124-127s=7, 148-167s=6, 370s=6, 89-114s=5, <90s=4
- **Key finding**: All 26 ATE have upstream_type=NULL with 0 tier_attempts — dispatcher rejects before any key is tried. This is budget-limited behavior (pre-R2315 budget=130, per-key=26s, UPSTREAM=24s → 2s overhead).
- **429 cycles**: 12 reqs with 429, 17 total cycles, max=5 per req. OK with cycle=6. Key rotation working correctly.

### kimi_nv tier_attempts (24h, 17 total)
- empty_200: 9 (keys 0,1,2,4 — zombie content-filter)
- NVCFPexecRemoteDisconnected: 5 (key 3 only, avg 43.4s, max 61.1s — upstream key issue)
- NVCFPexecSSLEOFError: 3 (keys 0,1,4 — SSLEOF, 5.0s each)

### Post-R2315 Regime (container start 02:54 UTC, ~8h)
- **Only 4 requests total**: glm5_2_nv=3 ATE, dsv4p_nv=1 ATE
- **0 kimi_nv traffic** — budget=170 untested
- All 4 ATE are big-input (282976 chars), breaker opened correctly on 4th consecutive fail

### Docker Logs --tail 200 (Key Events)
- **11:04-11:06 UTC**: 3x glm5_2_nv big-input ATE (282976 chars, 51-55s each). Breaker: CLOSED(1,0)→CLOSED(2,0)→CLOSED(3,0). All peer-fb skipped (NVCF DEGRADING).
- **11:05 UTC**: glm5_2_nv k2 SSLEOFError (5004ms), SSL cycle to next key (correct)
- **11:09 UTC**: dsv4p_nv k4 connection error (Remote end closed connection without response)
- **11:10 UTC**: dsv4p_nv big-input ATE (282976 chars, 170s). Breaker: OPEN(4,899). All 5 keys failed: empty200=1, timeout=1, other=2. Peer-fb skipped.
- **11:10 UTC**: Big-input breaker OPENED — 4th consecutive big-input fail (FAIL_N=4), 899s cooldown. Correct behavior.

## Analysis

### R2315 Budget Change: Needs Observation Time
R2315 raised kimi_nv tier budget from 130→170. The 24h data shows kimi_nv had 26 ATE with upstream_type=NULL (0 tier_attempts), consistent with budget-limited rejection. With budget=170, per-key budget is 34s (vs 26s at 130), giving 10s UPSTREAM_TIMEOUT margin per key (vs 2s). This should convert some of the 124-127s ATE cluster to successes.

**However**: 0 kimi_nv requests in the 8h post-R2315 regime. The budget change is untested. Must wait for traffic to evaluate.

### All Current Errors: Non-Configurable Upstream NVCF
- **Big-input ATE (glm5_2_nv, dsv4p_nv)**: 282976 chars, NVCF cluster-level degradation. Peer-fb skipped (correct — NVCF DEGRADING). Big-input breaker OPENED correctly on 4th consecutive fail. All 4 ATE are upstream cluster issues, not configurable.
- **SSLEOF**: Single event, SSL cycle handled correctly (5s, no same-key retry).
- **Connection error**: dsv4p_nv k4 single event, upstream NVCF.

### No Configurable Parameters at Floor or with Clear Signal
- **NVU_TIER_BUDGET_KIMI_NV=170**: Just changed, needs observation. 170<415 TIER_TIMEOUT_BUDGET safe.
- **NVU_PEXEC_TIMEOUT_FASTBREAK=2**: R2284 raised from 1→2. 0 NVCFPexecTimeout in regime. No signal to change.
- **NVU_EMPTY_200_FASTBREAK=3**: R2303 raised from 2→3. 0 empty_200 cascades in 8h regime. No signal.
- **KEY_COOLDOWN_S=10**: Floor level. 429 cycles present but handled correctly (6-8ms short-circuit).
- **TIER_COOLDOWN_S=15**: Stable. 429 storm handling correct.
- **Big-input parameters**: Breaker working correctly. FAIL_N=4, COOLDOWN=900, THRESHOLD=250K all correct.

### NOP Decision
Three thresholds for action:
1. ✅ Configurable error with clear signal → **NOT MET** (all errors are upstream NVCF, not configurable)
2. ✅ Parameter at floor with room to optimize → **NOT MET** (all params stable, kimi_nv budget just changed and needs observation)
3. ✅ Data-supported single-parameter improvement → **NOT MET** (0 kimi_nv traffic post-R2315, no new data)

**Decision: NOP (0 changes, 0 restart).**

## What Was NOT Changed
- **kimi_nv budget**: R2315 130→170 just deployed, needs observation time. No data to evaluate.
- **Big-input breaker**: Working correctly. FAIL_N=4 triggered correctly on 4th consecutive fail. 899s cooldown active.
- **EMPTY_200_FASTBREAK**: 3 per R2303. With budget=170, 3 empty_200 at ~62s each = 186s > 170s budget, so fastbreak would never trigger before budget exhaustion. But this is a design observation, not an actionable bug — must verify with actual kimi_nv traffic first.
- **All other params**: Stable, no env drift, no signal for change.

## Risk Assessment
- **Zero risk**: NOP round. No compose changes, no container restart.
- kimi_nv budget=170 continues to gather data. Next round will have traffic to evaluate.
- Big-input breaker will auto-close after 900s (15min) cooldown. Subsequent requests will be handled normally.

## Round History (kimi_nv budget)
- R2303: EMPTY_200_FASTBREAK 2→3 (paired with budget=200)
- R2309: Budget 200→130 (success p99=116.5s, 13.5s margin, cut 3rd key attempt)
- R2315: Budget 130→170 (success p99=123s, 7s→47s margin, restore key attempts)
- **R2316: NOP** — budget=170 untested (0 kimi_nv traffic), all errors upstream NVCF

## ⏳ 轮到HM1优化HM2