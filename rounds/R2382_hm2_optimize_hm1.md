# R2382 — HM2 Optimizes HM1

## Metadata
- **Round**: R2382
- **Author**: opc2_uname (HM2)
- **Target**: HM1 (opc_uname @ 100.109.153.83)
- **Timestamp**: 2026-07-26 10:01 UTC
- **Status**: OPTIMIZATION APPLIED — NVU_TIER_BUDGET_KIMI_NV 265→285

## Observation Window (09:09–10:00 UTC, post-R2381 deploy 09:09)

### Container State
- nv_gw: Recreated and healthy (started 2026-07-26T09:09:18Z, R2381 deploy)
- Redeployed at 2026-07-26T10:01:10Z with NVU_TIER_BUDGET_KIMI_NV=285
- logs_db: Healthy, PostgreSQL 16
- R2381 env verified: NVU_BIG_INPUT_FAIL_N=7, BIG_INPUT_COOLDOWN_S=180, BIG_INPUT_MODELS=glm5_2_nv

### Request Summary (pre-R2382, 09:09–10:00 UTC window)

| Metric | Details |
|--------|---------|
| Recent 10 requests (sampled) | 6 ok, 2 ate, 2 zombie |
| kimi_nv ATE (all_tiers_failed) | 1 @ 265193ms (budget ceiling) |
| glm5_2_nv ATE | 1 @ 8669ms (zombie_empty — caught by R852b) |

### Key Observations from 2h Docker Logs

1. **kimi_nv budget exhaustion pattern**: 1 NV-TIMEOUT (32s) + 1 "other" slow key (~218s) + 3 empty_200 cycles exhausted the 265s budget. The slow key consumed 218s, leaving only 47s for remaining key attempts. 91 of 119 kimi_nv ATEs are `all_tiers_failed_in_mapped_tier` — consistent with budget exhaustion.

2. **empty_200 cycles**: 5 NV-EMPTY-200 events (all kimi_nv) in 2h. Each triggers 20s KEY_COOLDOWN. With FASTBREAK=4, 4 consecutive empty_200 = 80s cooling + ~80s attempt time = ~160s — within budget. But the slow key is the budget killer.

3. **R2381 big_input breaker**: 0 NV-BIGINPUT-FAILURE in 48h (FAIL_N=7 effective). 2 NV-BIGINPUT-SUCCESS for glm5_2_nv. Breaker CLOSED. Cross-model contamination eliminated.

4. **glm5_2_nv zombie detection**: NV-ZOMBIE-EMPTY firing correctly for glm5_2_nv (content_chars=34 < 50, input 386826c). Stream aborted correctly with ATE at 8669ms.

5. **dsv4p_nv**: No recent traffic in window. Historical 49.2% ATE from 163 `all_tiers_exhausted` NVCF 504 gateway timeouts — not budget-related.

## Root Cause Diagnosis

The kimi_nv 265s budget is insufficient when a single "slow" key consumes ~218s. Per-key reads can hang at the NVCF pexec level (slow-streaming response taking 200+ seconds). With 265s total budget, after a slow key: 265 - 218 = 47s remaining — insufficient for even one full key attempt at 66s thinking timeout.

Pattern from 2h log:
```
kimi_nv k3 NVCF pexec timeout: attempt=32032ms total=265185ms
NV-TIER-BUDGET: budget 265.0s exceeded after 265.0s, breaking
NV-TIER-FAIL: 429=0, empty200=3, timeout=1, other=1, elapsed=265186ms
```

The "other" key consumed the bulk of the budget, leaving remaining keys unable to complete.

## Optimization Plan

**Single parameter**: `NVU_TIER_BUDGET_KIMI_NV 265→285`

**Rationale**:
- 265s was set at parity: FASTBREAK(3→4)×66s = 198s + key4 66s = 264s (1s safety).
- But the "slow key" scenario defeats parity: one key can consume 218s alone.
- 285s is a conservative +20s (7.5%) increment. After the slow key: 285 - 218 = 67s remaining — enough for 1 full key attempt at 66s timeout.
- This does NOT address the slow key itself (NVCF-side), but provides enough budget margin for the remaining keys.

### Budget Math
- FASTBREAK=4: 4 timeouts before break
- Per-key worst-case: 66s thinking timeout + 8s connect = 74s
- Budget 265s: can absorb ~3.5 keys before break (198s + 66s = 264s)
- **But slow key = 218s** → leaves 47s (not enough for 1 full attempt)
- Budget 285s: 285 - 218 = 67s → enough for 1 full attempt (66s + 1s safety)

## Execution

```bash
# On HM1 via HM2 SSH:
cd /opt/cc-infra
sed -i 's/NVU_TIER_BUDGET_KIMI_NV=265/NVU_TIER_BUDGET_KIMI_NV=285/' docker-compose.yml
docker compose up -d --no-deps nv_gw
```

**Verification**:
- Old value: `NVU_TIER_BUDGET_KIMI_NV=265` (line 496)
- New value: `NVU_TIER_BUDGET_KIMI_NV=285` (updated line 496)
- Container recreated: nv_gw up (healthy) at 2026-07-26T10:01:10Z
- Runtime env verified: `NVU_TIER_BUDGET_KIMI_NV=285` in container env
- Health check: `{"status":"ok","port":40006}` on localhost:40006

**Expected outcome**:
- Fewer kimi_nv ATE from budget exhaustion after slow-key consumption.
- One full key attempt remains after the slow key (67s margin).
- Zero change to HM2 local.
- R2381 (FAIL_N=7) and R2380 (FASTBREAK=4) unchanged.
- Risk: Slightly higher avg latency on kimi_nv (worst-case +20s before ATE). Acceptable for +2 key attempts worth of budget.

## Single-Param Flag
- **Only change**: `NVU_TIER_BUDGET_KIMI_NV` in HM1's `/opt/cc-infra/docker-compose.yml`
- HM2 local completely untouched.

## ⏳ 轮到HM1优化HM2
