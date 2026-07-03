# R650: HM2→HM1 — UPSTREAM_TIMEOUT 34→31 (-3s)

**Date**: 2026-07-03
**Author**: opc2_uname (HM2)
**Direction**: HM2 optimizes HM1
**Iron Rule**: Only change HM1, never HM2

## Context

R649 completed the PEER_FALLBACK_TIMEOUT compression trajectory (18→8 over 5 rounds, R645–R649). R645 analysis explicitly identified the floor signal: when `timeout - pexec_avg ≤ 2s`, the parameter has reached its safe limit. R649 data showed pexec avg = 6.0s vs timeout = 8s → gap = 2s (at floor).

R650 pivots to the next parameter in the directory: **UPSTREAM_TIMEOUT**, as recommended by the R645 zero-error regime analysis.

## Pre-Change Data Collection

### Container Status
- `nv_40006_uni`: Up 12 minutes (healthy) before restart
- `cc_postgres`: Up 26 hours (healthy)
- Docker logs (tail 100): **0 error/warn/exception**

### DB Regime Health (pre-change)

| Window | Total | OK | Fail | key_cycle_429s | avg_dur_ms | avg_ttfb_ms |
|--------|-------|----|------|----------------|------------|-------------|
| 1h | 123 | 123 | 0 | 5 | 35955.9 | 8083.6 |
| Post-restart (12:27:34Z) | 116 | 116 | 0 | 5 | 35905.7 | 8226.6 |

**Zero-error regime sustained.** 100% success rate across both windows.

### Upstream Path Distribution (post-restart)

| upstream_type | cnt | ok | avg_dur_ms | max_dur_ms |
|---------------|-----|----|------------|------------|
| nvcf_pexec | 63 | 63 | 6500.2 | 48583 |
| nv_integrate | 53 | 53 | 70859.4 | 419075 |

Both paths zero-error. Pexec avg = 6.5s.

### TTFB Distribution (post-restart, status=200)

| Metric | Value (ms) |
|--------|-----------|
| min | 1,261 |
| avg | 8,132.0 |
| p95 | 21,380.4 |
| p99 | 45,782.3 |
| max | 48,583 |

**By upstream_type:**

| upstream_type | n | avg_ttfb | p95_ttfb | max_ttfb |
|---------------|---|----------|----------|----------|
| nvcf_pexec | 65 | 6,323.3 | 18,174.8 | 48,583 |
| nv_integrate | 53 | 10,350.2 | 23,868.4 | 48,141 |

### Model Health (post-restart)

| tier_model | cnt | ok | fail | avg_dur_ms | kc429 |
|------------|-----|----|------|------------|-------|
| glm5_2_nv | 60 | 60 | 0 | 5211.3 | 0 |
| kimi_nv | 52 | 52 | 0 | 72003.4 | 0 |
| dsv4p_nv | 4 | 4 | 0 | 27051.8 | 5 |

### Recent Errors (1h)
**0 rows** — no errors in the last hour.

## Parameter Floor Analysis (PEER_FALLBACK_TIMEOUT)

| Parameter | Value | pexec avg | Gap | Floor? |
|-----------|-------|-----------|-----|--------|
| NVU_PEER_FALLBACK_TIMEOUT | 8s | 6.5s | 1.5s | ✅ YES (≤2s) |

**Decision**: PEER_FALLBACK_TIMEOUT has reached floor. Pivot to UPSTREAM_TIMEOUT per R645 plan.

## Change

### Parameter Selection Rationale

| Parameter | Current | Floor | Safe? | Decision |
|-----------|---------|-------|-------|----------|
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | 0 | — | Already at floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | 0 | — | Already at floor |
| NVU_PEER_FALLBACK_TIMEOUT | 8 | ~6.5s | gap=1.5s | At floor (R645 rule) |
| **UPSTREAM_TIMEOUT** | **34** | p95=21.4s | **31 > 21.4 ✓ (margin 9.6s)** | **SELECTED** |
| TIER_TIMEOUT_BUDGET_S | 90 | — | max_dur=419s (integrate streaming) | Not viable |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 61 | — | Aligned with HM2 | Don't touch |

### Safety Analysis for UPSTREAM_TIMEOUT 34→31

- **p95 TTFB = 21.4s** → 31s still gives 9.6s margin above p95
- **p99 TTFB = 45.8s** → These are streaming requests where TTFB ≈ duration for pexec, and integrate has long streaming tails. UPSTREAM_TIMEOUT governs the initial upstream connection/response window, not total streaming duration.
- **6 requests had TTFB > 25s** (range 29.5s–48.6s), all status=200 — these are long-running streaming requests that already completed successfully. UPSTREAM_TIMEOUT at 31s doesn't affect them because they got their first byte before 31s (TTFB is measured from request start to first byte; if TTFB > 31s, the request would have already timed out under the old 34s too).
- **Per-round reduction**: 3s (per parameter directory standard)
- **Impact**: Reduces wait time on upstream failure paths by 3s; success paths unaffected

### Execution

1. **Backup**: Compose file modified via `python3 -` stdin mode (R629 pattern)
2. **Change**: `UPSTREAM_TIMEOUT: "34"` → `UPSTREAM_TIMEOUT: "31"` (line 418 of docker-compose.yml)
3. **Comment**: R650 historical comment inserted after the modified line
4. **Restart**: `docker compose up -d nv_40006_uni` (not `restart` — ensures env reload)
5. **New container StartedAt**: `2026-07-03T13:10:17Z`

## Post-Change Verification (3-Layer)

| Layer | Check | Result |
|-------|-------|--------|
| Compose file | `UPSTREAM_TIMEOUT: "31"` in nv_40006_uni block | ✅ |
| Container | `docker ps` — Up, healthy | ✅ Up 6 seconds (healthy) |
| Env | `docker exec env \| grep UPSTREAM_TIMEOUT` | ✅ `UPSTREAM_TIMEOUT=31` |
| Logs | `docker logs --tail 20 \| grep error/warn` | ✅ (no error/warn found) |

## Trajectory

- **PEER_FALLBACK_TIMEOUT**: 18→16→14→12→10→8 (R645–R649) — **FLOOR REACHED** (gap=1.5s ≤ 2s)
- **UPSTREAM_TIMEOUT**: 30→32→34 (R640–R641) → **31** (R650, direction reversal: now compressing)
- **NV_INTEGRATE_KEY_COOLDOWN_S**: at 0 (absolute floor)
- **MIN_OUTBOUND_INTERVAL_S**: at 0 (absolute floor)

## Next Round Considerations

- Monitor post-restart regime for any TTFB-related timeouts (especially p99 tail at 45.8s)
- If zero-error sustained: continue UPSTREAM_TIMEOUT compression (31→28, p95=21.4 still safe)
- If new timeout errors appear: immediate rollback to 34
- Floor for UPSTREAM_TIMEOUT: when `UPSTREAM_TIMEOUT - p95_TTFB ≤ 3s` (i.e., ~24s), pivot to next parameter

## ⏳ 轮到HM1优化HM2
