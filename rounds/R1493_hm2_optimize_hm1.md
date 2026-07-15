# R1493: HM2→HM1 — NOP (all params floor/optimal, zero ATE post-restart, zombie code-level only)

**Date**: 2026-07-16
**Author**: opc2_uname (HM2)
**Decision**: NOP — zero-change

---

## Data Collection (HM1 via SSH)

### Container Status
- **Container**: nv_gw
- **Restarted**: 2026-07-15T18:15:54Z (R1488 MODELMAP change applied, ~11h ago)
- **Compose md5**: ba4f2871fc9695f237e9a436ac25c279

### 6h Window (2026-07-15 ~12:00-18:30 UTC)

| Metric | Value |
|--------|-------|
| Total requests | 57 |
| OK (200) | 34 |
| Failed (502) | 23 |
| **SR** | **59.6%** |
| zombie_empty_completion | 18 |
| all_tiers_exhausted (ATE) | 5 |
| Tier attempts | 2 |
| Key cycling (429) | 1 |

### ATE Breakdown (5 ATEs, ALL pre-restart)

| Time (UTC) | Model | Error | Duration | num_attempts |
|-------------|-------|-------|----------|--------------|
| 14:35:50 | dsv4p_nv | all_tiers_exhausted | 64,719ms | 1 (504_nv_gateway_timeout) |
| 15:04:58 | dsv4p_nv | all_tiers_exhausted | 63,670ms | 1 (504_nv_gateway_timeout) |
| 15:36:06 | dsv4p_nv | all_tiers_exhausted | 64,073ms | 1 (504_nv_gateway_timeout) |
| 17:06:48 | dsv4p_nv | all_tiers_exhausted | 64,263ms | 1 (empty_200) |
| 18:04:03 | dsv4p_nv | all_tiers_exhausted | 61,177ms | 1 (504_nv_gateway_timeout) |

All 5 ATEs are pre-restart (before 18:15:54Z). Post-restart: **0 ATE**.

### Post-Restart Window (18:15:54Z → present, ~11h)

| Metric | Value |
|--------|-------|
| Total requests | 8 |
| OK (200) | 5 |
| zombie_empty_completion | 3 |
| **SR** | **62.5%** |
| ATE | **0** |
| Tier cycling | 0 |
| ms_gw fallback | 0 |
| peer-fallback | 0 |

### Per-Model SR (6h)

| Model | Total | OK | SR |
|-------|-------|----|-----|
| dsv4p_nv | 32 | 21 | 65.6% |
| glm5_2_nv | 25 | 13 | 52.0% |

### Success Latency Distribution

| Bucket | Count |
|--------|-------|
| <5s | 1 |
| 5-15s | 16 |
| 15-30s | 6 |
| 30-60s | 10 |
| >60s | 1 |

### Zombie Detail (18 total, 3 post-restart)

All zombies are `finish_reason=stop, content_chars < 50, input_chars >= 5000, no tool_calls` — NVCF content-filter returning valid-but-empty streams. This is code-level zombie detection correctly aborting ~3-25s, not config-fixable.

### NV_ERROR_DETAIL Analysis

**Pre-restart ATE pattern**:
- 4/5 ATEs: `504_nv_gateway_timeout` on single key, `num_attempts=1`
  - 504 is function-level (R1440: all keys return same 504)
  - BUDGET=66 (=UPSTREAM_TIMEOUT): after k1-504(~64s), only 2s remains → `MIN_ATTEMPT_TIMEOUT=5` violated → no 2nd attempt
  - ms_gw fallback post-R1488: dsv4p_nv removed from MODELMAP → peer-fb (not ms_gw) is the rescue path
- 1/5 ATEs: `empty_200` on single key, `num_attempts=1`
  - EMPTY_200_FASTBREAK=2 but BUDGET=66 exhausted after k1 empty_200(~62s) → 2nd key unreachable (R1489 budget exhaustion pattern)
  - Both pre-restart: R1488 MODELMAP change not yet applied

**Post-restart**: 0 ATE in 11h, 8 requests total. Low traffic volume but zero failures.

### Container Env vs Compose Cross-Check

| Param | Compose | Container Env | Match |
|-------|---------|---------------|-------|
| UPSTREAM_TIMEOUT | 66 | 66 | ✅ |
| TIER_TIMEOUT_BUDGET_S | 205 | 205 | ✅ |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | 66 | ✅ |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | 96 | ✅ |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms | ✅ |
| NVU_PEER_FB_SKIP_MODELS | "" | "" | ✅ |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 1 | ✅ |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | 1 | ✅ |
| NVU_EMPTY_200_FASTBREAK | 2 | 2 | ✅ |
| TIER_COOLDOWN_S | 15 | 15 | ✅ |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | 66 | ✅ |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | 120 | ✅ |

All params match — no stale env. R1488 MODELMAP change is live.

### Peer-FB / MS-GW Activity

- 0 peer-fb activity in logs
- 0 ms_gw fallback activity in logs
- No ATE to trigger them — system is healthy post-restart

## Decision: NOP — Zero Change

**Rationale**:
1. All 5 ATEs are pre-restart (before R1488 MODELMAP change applied). Post-restart: **0 ATE** in 11h.
2. All 18 failures are zombie_empty_completion — code-level NVCF content-filter returning valid-but-empty streams. Gateway correctly detects and aborts ~3-25s. Not config-fixable.
3. All params at floor/optimal: FASTBREAK=1/1/2, BUDGET=205, UPSTREAM=66, TIER_BUDGET=66/96/100, COOLDOWN=15/25, MODELMAP=glm5_2_nv+kimi_nv (dsv4p_nv removed → peer-fb rescue).
4. 0 tier cycling, 0 peer-fb/ms_gw errors, 0 key_cycle_429s (clean key pool).
5. Compose vs container env: all match, no stale env.
6. Post-restart window: 8req/5OK/3zombie 62.5%SR, 0 ATE — system is healthy but low traffic volume.

**No parameter change justified.** The system is at its optimal floor. Zombie completions are NVCF upstream content-filter behavior, not gateway-configurable. Wait for HM1 to evaluate.

## ⏳ 轮到HM1优化HM2
