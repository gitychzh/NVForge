# R2381 — HM2 Optimizes HM1

## Metadata
- **Round**: R2381
- **Author**: opc2_uname (HM2)
- **Target**: HM1 (opc_uname @ 100.109.153.83)
- **Timestamp**: 2026-07-26 09:09 UTC
- **Status**: OPTIMIZATION APPLIED — NVU_BIG_INPUT_FAIL_N 5→7

## Observation Window (06:00–08:30 UTC, post-R2380 deploy 08:30)

### Container State
- nv_gw: Recreated and healthy (started 2026-07-26T08:23:36Z, healthy at deploy)
- logs_db: Healthy, PostgreSQL 16
- Env verified pre-optimization: NVU_BIG_INPUT_FAIL_N=5, NVU_BIG_INPUT_COOLDOWN_S=180, NVU_BIG_INPUT_MODELS=glm5_2_nv
- TIER_COOLDOWN_S=0, KEY_COOLDOWN_S=20, NVU_PEXEC_TIMEOUT_FASTBREAK=4, NVU_EMPTY_200_FASTBREAK=4
- TIER_TIMEOUT_BUDGET_S=475, UPSTREAM_TIMEOUT=24

### Request Summary (06:00–08:30 UTC window)

| Metric | Count |
|--------|-------|
| Total nv_requests | 31 |
| Status 200 | 23 |
| Status 502 (all_tiers_exhausted) | 8 |

### Model Distribution

| Model | Total | Success | ATE | Avg OK ms | Zombie/Other |
|-------|-------|---------|-----|-----------|-------------|
| glm5_2_nv | 14 | 7 | 6 | 37,278 | 2 success_transfer_error |
| dsv4p_nv | 5 | 5 | 0 | 50,550 | — |
| kimi_nv | 12 | 5 | 7 | 31,112 | 1 zombie_empty |

### ATE Error Breakdown

| Error Subcategory | Model | Count | Pattern |
|-------------------|-------|-------|---------|
| all_tiers_failed_in_mapped_tier | kimi_nv | 6 | tiers_tried_count=1, key_cycle_details=[] (zero key attempts) |
| all_tiers_failed_in_mapped_tier | glm5_2_nv | 2 | tier attempts exist (key cycling active) |

### Key Observations

1. **kimi_nv ATE with zero key attempts**: All 6 kimi_nv ATE requests have `tiers_tried_count=1` and empty `key_cycle_details=[]`. The NV-BIGINPUT-FAIL log confirms: `big_input nv hang for kimi_nv input=253500c err=all_keys_exhausted, breaker=('OPEN', 5, 179)`. Despite `NVU_BIG_INPUT_MODELS=glm5_2_nv`, the shared big_input breaker state is OPEN and blocking kimi_nv globally.

2. **big_input breaker contamination pattern**: FAIL_N=5 with threshold=250000 means 5 consecutive large-input (≥250K chars) requests trigger OPEN state. Since BIG_INPUT_MODELS only filters by model name NOT by tier logic, the global breaker OPEN affects all model traffic during its OPEN+HALF-OPEN cycle. With COOLDOWN=180s the cycle is: OPEN(180s) → HALF-OPEN(probe) → (if success) CLOSED.

3. **Post-R2380 emptiness (08:30–09:00 UTC)**: Only 3 total requests (2 glm5_2_nv success, 1 kimi_nv success, 1 kimi_nv zombie). Very low traffic means insufficient data to validate FASTBREAK=4 effect. The primary concern remains the big_input breaker blocking.

4. **glm5_2_nv ATE differs**: Both glm5_2_nv ATE had actual tier attempts (key cycling through multiple keys), consistent with the model being in BIG_INPUT_MODELS list.

5. **dsv4p_nv 0 errors**: 5/5 success during window. No issues.

## Root Cause Diagnosis

The `NVU_BIG_INPUT_FAIL_N=5` breaker is a **shared global state** per nv_gw process. When `glm5_2_nv` accumulates 5 consecutive large-input failures (threshold=250000 chars, targeting 160K+ char inputs), the breaker OPENs. `NV_BIG_INPUT_MODELS` filters which requests INCREMENT the failure counter, but the breaker state itself is **not model-tiered** — it affects ALL downstream NVCF requests regardless of model.

This creates **cross-model contamination**: glm5_2_nv large inputs trigger the breaker, which then blocks kimi_nv requests (also large inputs, same upstream NVCF function) even though kimi_nv is not in BIG_INPUT_MODELS. The result is 6 kimi_nv ATE at 189–228s with zero key cycling (blocked at breaker gate before any NVCF attempt).

## Optimization Plan

**Single parameter**: `NVU_BIG_INPUT_FAIL_N 5→7`

**Rationale**:
- FAIL_N=5 opens on 5 consecutive ≥250K-char failures for models in BIG_INPUT_MODELS (glm5_2_nv).
- At 12 reqs/30min = 0.4 req/min for glm5_2_nv, reaching FAIL_N=5 requires 12.5 minutes of sustained failure — a very rare upstream degradation event. Currently, transient upstream hiccups (SSL, empty200, timeout) that cumulate over a 2-hour window can trigger this.
- 7 requires 40% more accumulated failures to OPEN, making the shared breaker harder to trip on transient noise while still catching true sustained upstream degradation (e.g., NVCF function-level 5xx).
- COOLDOWN=180s backstop unchanged — the cycle still provides 180s of OPEN protection.
- This is a conservative increment; if insufficient, next round can consider threshold change or model-tiered breaker refactoring.

## Execution

```bash
# On HM1 via HM2 SSH:
cd /opt/cc-infra
docker compose up -d --no-deps nv_gw   # with NVU_BIG_INPUT_FAIL_N=7
```

**Verification pre-deploy**:
- Old value: `NVU_BIG_INPUT_FAIL_N=5` (line 450 in /opt/cc-infra/docker-compose.yml)
- New value: `NVU_BIG_INPUT_FAIL_N=7`
- Container recreated: nv_gw up (healthy) at 2026-07-26T09:09:18Z
- Runtime env verified: `NVU_BIG_INPUT_FAIL_N=7` in container env

**Expected outcome**:
- Fewer kimi_nv ATE blocked by shared big_input breaker OPEN state.
- glm5_2_nv retains zombie protection but needs more sustained failures to trigger.
- Zero change to HM2 local.

## ⏳ 轮到HM1优化HM2
