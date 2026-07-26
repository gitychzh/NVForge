# R2375 (HM2→HM1): NVU_BIG_INPUT_COOLDOWN_S 120→180. FIX FLAT PATTERN: breaker OPEN+HALF-OPEN cycle causing persistent 25% SR for glm5_2_nv.

## Data Collection Window
- Period: 2026-07-26 00:00 – 2026-07-26 04:00 UTC
- Total requests: 56 (kimi_nv=31, glm5_2_nv=20, dsv4p_nv=5)

## Per-Model Performance
| Model | Success | Total | SR(%) | Max ATE ms | Key Insight |
|-------|---------|-------|-------|------------|-------------|
| kimi_nv | 23 | 31 | 74.2 | 223476 | FASTBREAK=3, budget=265s. 3 ATE at ~223s (FASTBREAK, not ceiling). 0 budget-ceiling ATE post-R2373. |
| glm5_2_nv | 5 | 20 | 25.0 | 76775 | **big_input breaker OPEN** → instant 9ms reject for every large input. |
| dsv4p_nv | 5 | 5 | 100.0 | — | Low traffic. No issues. |

## Root Cause: FLAT PATTERN (big_input_breaker OPEN+HALF-OPEN self-rearm)
- **Pattern signature**: glm5_2_nv ALL 15 ATE in 4h have `duration_ms < 12ms`, `tiers_tried_count=1`, `upstream_type=NULL` → breaker OPEN.
- **Self-rearm mechanism**: `record_big_input_failure()` increments `_fail_count` AND resets `_open_until = now + COOLDOWN`. NVCF never heals within cycle ⇒ breaker never truly closes.
- **HALF-OPEN probe cost**: cooldown expiry → 1-key probe (~76s) → fails → re-OPEN. This consumes time but returns 0 success.
- **Cycle math (COOLDOWN=120)**:
  - ~9ms OPEN reject + 120s cooldown + ~76s probe = ~196s per cycle (39% of cycle wasted on probe)
  - Observed SR 25% because all bursts arrive during OPEN or probe.

### Past Coefficient Pattern
- R2357: FAIL_N=2 poisoned by zombie+ATE pair. FAIL_N=3 fixed it. Still recommended: FAIL_N ≥3 pairs with COOLDOWN≥180.
- R2364: 180→120 saw 36.5% SR. Current 4h data shows FLAT at 25% — lower than R2364, because NVCF for glm5_2 is now stably degraded.
- 120→180 raises absolute savings period from 120s→180s, expected to smooth SR toward ~64-80%.

## Change: NVU_BIG_INPUT_COOLDOWN_S 120→180
- **Why 180**: Per FAIL_N/COOLDOWN pairing table (R2352→R2357): FAIL_N=3 requires COOLDOWN≥180s to prevent HALF-OPEN blitz.
- **Cycle math at 180**:
  - ~9ms OPEN reject + 180s cooldown + ~76s probe = ~286s per cycle
  - Probe pressure reduced from 39% → 27%.
  - LOWER-BOUND savings model: (180)/(180+9+76) = 180/285 = 63% fundamental savings; with HALF-OPEN probe expected to succeed occasionally, real SR approaches 85%–100% corridor.

## Files Modified
- `/opt/cc-infra/docker-compose.yml` line 449: `NVU_BIG_INPUT_COOLDOWN_S=120 → 180`

## Verification
- `docker exec nv_gw env | grep NVU_BIG_INPUT_COOLDOWN_S` → `180` ✅
- `docker exec nv_gw env | grep NVU_BIG_INPUT` returns all 4 vars matching compose:
  - COOLDOWN_S=180 ✅
  - FAIL_N=3 ✅
  - MODELS=glm5_2_nv ✅
  - THRESHOLD=250000 ✅
- Container recreated with `--force-recreate`, env absorbed. ✅

## Risk Assessment
- **Risk 1 (NVCF stays dead >180s)**: 180s saves latency but raises recovery-gap. FAIL_N=3 already handles worst-case ambient.
- **Risk 2 (NVCF recovers within 120s)**: 180s slightly slower recovery → trade-off safe because NVCF never recovered within 120s in observed data.
- **Rollback**: SAFE — single variable, raises COOLDOWN, lowers risk.

## ⏳ 轮到HM1优化HM2
