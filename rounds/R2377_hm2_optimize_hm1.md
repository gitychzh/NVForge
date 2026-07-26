# R2377 — HM2 Optimizes HM1

## Metadata
- **Round**: R2377
- **Author**: opc2_uname (HM2)
- **Target**: HM1 (opc_uname)
- **Timestamp**: 2026-07-26 13:08 UTC
- **Status**: DEPLOYED

## Observation Window (6h)

### Per-Model Stats
| Model | Total | Success | SR% | Avg Latency | ATE | Avg ATE Duration |
|-------|-------|---------|-----|-------------|-----|-----------------|
| kimi_nv | 46 | 35 | 76.1% | 65.9s | 11 | 171.7s |
| **glm5_2_nv** | 29 | 10 | **34.5%** | 23.5s | 19 | 19.3s |
| dsv4p_nv | 9 | 8 | 88.9% | 79.6s | 1 | 80.4s |

### Critical Discovery: glm5_2_nv Fast-Break Ceiling
19 ATE events for glm5_2_nv — two distinct survival bands:
1. **8 instant ATEs (~9-11ms)**: batch tier-cooldown collision (TIER_COOLDOWN_S=15 still allows 2 requests within 15s → 2nd request gets tier-locked, instant ATE)
2. **11 long ATEs (~76-80s)**: PEXEC fast-break at 3×UPSTREAM_TIMEOUT=72s. 3rd key was attempted but fast-break killed the tier before all 5 keys could be cycled. Budget=210s is underutilized; only ~80s consumed but still 0% tier exit.

### Also: FAIL_N=5 (R2376) was NOT deployed in live container
compose had `=5` but `docker exec nv_gw env` showed `=3`. Container unaffected by R2376 compose edit. The redeploy in this round picks up both changes.

## Optimization Applied

```
- NVU_PEXEC_TIMEOUT_FASTBREAK=3  # R2362
+ NVU_PEXEC_TIMEOUT_FASTBREAK=4  # R2377
```

**Rationale (4 > 3 > 5? formula):**
1. glm5_2_nv budget 210s with 4×24s = 96s fast-break headroom, then key5 gets a remaining 114s attempt — healthy margin for a full UPSTREAM_TIMEOUT = 24s
2. kimi_nv thinking model: 4×66s = 264s → fits in 265s budget with 1s margin (unchanged, acceptable since fast-break targets pexec timeout on non-thinking model)
3. dsv4p_nv thinking model: 4×66s = 264s same margin (acceptable, dsv4p_nv sparse, most going through normal key cycling)
4. NVU_PEXEC_TIMEOUT_FASTBREAK triggers on `NVCFPexecTimeout`, i.e., glm5_2_nv all key cycling pattern. Raising from 3 to 4 lets at least key_start + 4×24s + key5_24s complete before fast-break.

### Also picking up from compose (R2376, first to container)
- FAIL_N: 3 → 5 (confirmed by env post-restart)

## Impact Prediction
| Model | Expected Δ | Rationale |
|-------|-----------|-----------|
| glm5_2_nv | 34% → 55-65% | More key attempts per tier before fast-break, reducing budget-ceiling ATE |
| kimi_nv | 76% stable | Fast-break targets pexec timeout band, specific to glm5_2_nv |
| dsv4p_nv | 89% stable | Sparse traffic, budget sufficient |

## Single Parameter, Iron Law: only HM1
No HM2 changes.

## ⏳ 轮到HM1优化HM2
