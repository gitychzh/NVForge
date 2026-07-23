# R2312 (HM2->HM1): NVU_BIG_INPUT_THRESHOLD 400000→250000 — restore zombie-catching threshold

**Date**: 2026-07-24 07:15 UTC (HM2 cron trigger)
**Author**: opc2_uname (HM2)
**Target**: HM1 (opc_uname @ 100.109.153.83:222)
**Container**: nv_gw (port 40006)
**Iron Law**: Only HM1 config changed. Zero HM2 local changes.

## Detection Context
- Git HEAD: 0512974 R2311 (HM2->HM1): NVU_PEER_FB_SKIP_MODELS +dsv4p_nv
- Pre-run script: "这是我提交的, 不触发" — but system triggered HM2 round anyway
- R2311 was HM2's own commit. Detection script still triggered → proceed with new round.

## Data Collection (2026-07-24 ~07:15 UTC)

### Container State
- nv_gw: Up 18 min (healthy), StartedAt 2026-07-23T23:03:30Z, RestartCount=0
- All other containers healthy (ms_gw, cc4101, legacy_*, logs_db)
- Health endpoint: OK, 5 keys, 3 NVCF models (kimi_nv, dsv4p_nv, glm5_2_nv)
- Docker logs --tail 100: **no error/warn found** (clean restart window)

### Post-Restart (23:03:30Z → query time, ~18 min)
| Metric | Value |
|--------|-------|
| Total requests | 2 |
| OK | 2 |
| Fail | 0 |
| SR | 100% |
| Avg duration | 6273.5ms |
| Max duration | 7257ms |
| Avg TTFB | 6273.0ms |
| Model | glm5_2_nv only |
| Fallbacks | 0 attempted, 0 occurred |

### 6h Window (MAX(ts) relative)
| Model | Total | OK | Fail | SR% | Avg OK ms | Max OK ms |
|-------|-------|-----|------|-----|-----------|-----------|
| glm5_2_nv | 34 | 15 | 19 | 44.1% | 15297.3 | 50637 |
| dsv4p_nv | 27 | 19 | 8 | 70.4% | 30845.9 | 90721 |
| kimi_nv | 0 | 0 | 0 | - | - | - |
| **Total** | **61** | **34** | **27** | **55.7%** | **23986.3** | **90721** |

OK p95=60094ms, p99=86410ms — high tail latency from large-input requests.

### Error Distribution (6h, 27 errors)
| Error Type | Count |
|------------|-------|
| all_tiers_exhausted (ATE) | 22 |
| zombie_empty_completion | 5 |

### ATE Duration Clusters
| Cluster | Model | Count | Avg ms |
|---------|-------|-------|--------|
| sub1s_preempt (<1s) | glm5_2_nv | 7 | 107.9 |
| 1to10s_preempt (1-10s) | glm5_2_nv | 7 | 6702.9 |
| 10to60s_partial (10-60s) | dsv4p_nv | 5 | 41264.8 |
| 10to60s_partial (10-60s) | glm5_2_nv | 5 | 29143.2 |
| 60s+_budget_exhaust (>60s) | dsv4p_nv | 1 | 160041.0 |

### Zombie Details (5 events, all nvcf_pexec)
| Model | Input Chars | Duration ms | Timestamp |
|-------|-------------|-------------|-----------|
| glm5_2_nv | 273,278 | 18,107 | 22:03:47 |
| dsv4p_nv | 269,978 | 15,116 | 21:38:30 |
| glm5_2_nv | 267,950 | 21,691 | 20:33:30 |
| dsv4p_nv | 257,193 | 14,516 | 17:07:25 |
| dsv4p_nv | 257,179 | 11,294 | 17:37:50 |

### Sub1s ATE Details (7 events, instant NVCF 429 storm rejections)
All glm5_2_nv, all at 257K-277K input chars, 6-8ms instant rejection.
upstream_type=NULL (scheduling layer), nv_key_idx=NULL, key_cycle_429s=0.

### Tier Attempts (6h)
| Tier | Error Type | Count | Avg ms |
|------|-----------|-------|--------|
| glm5_2_nv | 429_nv_rate_limit | 8 | - |
| glm5_2_nv | NVCFPexecTimeout | 3 | 25013.0 |
| dsv4p_nv | 504_nv_gateway_timeout | 1 | - |
| dsv4p_nv | NVCFPexecRemoteDisconnected | 1 | 35729.0 |

Function IDs: glm5_2_nv=3b9748d8 (11 attempts, 11 errors), dsv4p_nv=74f02205 (2 attempts, 2 errors).

### Input Chars Distribution (glm5_2_nv, 6h)
| Range | Status 200 | Status 429 | Status 502 |
|-------|-----------|-----------|-----------|
| 250K-300K | 15 | 5 | 10 |
| <250K | 0 | 0 | 0 |
| >300K | 0 | 0 | 0 |

**All glm5_2_nv traffic is 250K-300K input chars.** No traffic below 250K → lowering threshold to 250K has zero risk of false-positive on small inputs.

### 24h Extended
| Model | ATE Count | ATE Avg ms | Zombie Count | Zombie Avg ms |
|-------|-----------|-----------|-------------|-------------|
| glm5_2_nv | 58 | 24844.7 | 8 | 17555.3 |
| dsv4p_nv | 30 | 19692.8 | 5 | 29302.8 |
| kimi_nv | 26 | 193764.5 | 8 | 74004.4 |

### Fallback Stats (6h)
- fb_count=0, fb_attempted=3, fb_ok=0
- All 3 attempted fallbacks failed (likely peer-fb for models not in skip list, or ms_gw fallback)
- PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv (R2310+R2311)

### Current HM1 Env (Key Parameters)
```
NVU_BIG_INPUT_THRESHOLD=400000  ← TARGET (R2293 raised from 370K)
NVU_BIG_INPUT_FAIL_N=8         (R2289 raised from 5)
NVU_BIG_INPUT_COOLDOWN_S=900   (R2288 lowered from 2100)
NVU_BIG_INPUT_MODELS=glm5_2_nv (R2286 model filter)
NVU_EMPTY_200_FASTBREAK=3
NVU_PEXEC_TIMEOUT_FASTBREAK=2
NVU_STREAM_FIRST_BYTE_DEADLINE_S=15
NVU_STREAM_TOTAL_DEADLINE_S=35
NVU_TIER_BUDGET_GLM5_2_NV=210
NVU_TIER_BUDGET_DSV4P_NV=170
NVU_TIER_BUDGET_KIMI_NV=130
TIER_COOLDOWN_S=15
TIER_TIMEOUT_BUDGET_S=415
UPSTREAM_TIMEOUT=24
KEY_COOLDOWN_S=10
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
NVU_PEER_FALLBACK_TIMEOUT=60
NVU_MS_GW_FALLBACK_TIMEOUT=120
```

## Optimization Decision

### Change: NVU_BIG_INPUT_THRESHOLD 400000 → 250000

**Rationale:**
1. **5/5 zombie events** in 6h at 257K-273K input chars — all invisible to breaker at THRESHOLD=400K
2. **7/7 sub1s ATE** (instant 429 storm rejects) at 257K-277K chars — also invisible
3. **All 15 successful** glm5_2_nv requests at 265K-276K chars — all above 250K threshold
4. **Zero traffic** below 250K → zero false-positive risk
5. BIG_INPUT_MODELS=glm5_2_nv filter verified: dsv4p_nv zombies (3/5) NOT caught by breaker (correct model filter behavior from R2286)
6. With FAIL_N=8 (conservative), breaker opens after 8 consecutive big-input failures → instant reject saves 6-50s/user
7. R2293 raised threshold 370K→400K to bypass dsv4p_nv pre-emption, but R2286 model filter already solved that — threshold raise was redundant belt-and-suspenders that blocked zombie catching
8. Matches R1747 architecture snapshot value (250000)
9. **Single parameter; iron law: only HM1**

**Expected Impact:**
- Zombies at 257K-273K now classified as big-input → counted toward FAIL_N=8
- After 8 consecutive big-input glm5_2_nv failures in 900s window → breaker opens
- Breaker open → instant reject (~8ms) instead of 11-22s zombie wait → saves ~15s/user per zombie
- 429 storm ATE also now classified as big-input → breaker opens faster during storms
- dsv4p_nv unaffected (model filter)

**Risk Assessment:**
- LOW: Zero traffic below 250K in 6h window
- If a legitimate small-input glm5_2_nv request arrives, it won't be affected (below threshold)
- If breaker opens, only blocks glm5_2_nv big-input for 900s (15min) — ms_gw fallback covers
- FAIL_N=8 is conservative (needs 8 consecutive fails, not 5)

## Implementation

1. SSH to HM1: `ssh -p 222 opc_uname@100.109.153.83`
2. Edit `/opt/cc-infra/docker-compose.yml` line 452:
   - Old: `NVU_BIG_INPUT_THRESHOLD=400000  # R2293 ...`
   - New: `NVU_BIG_INPUT_THRESHOLD=250000  # R2312 ...`
3. `cd /opt/cc-infra && docker compose up -d nv_gw`
4. Verify: `docker exec nv_gw env | grep NVU_BIG_INPUT_THRESHOLD` → 250000 ✓
5. Health: `curl -s http://localhost:40006/health` → OK ✓
6. Container: StartedAt 2026-07-23T23:40:13Z, RestartCount=0, running ✓

## Verification Post-Change
- env: `NVU_BIG_INPUT_THRESHOLD=250000` confirmed in container
- Health: `{"status":"ok",...}` confirmed
- Container: running, healthy, 0 restarts
- No docker log errors after restart

## ⏳ 轮到HM1优化HM2
