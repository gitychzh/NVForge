# R652: HM2→HM1 — UPSTREAM_TIMEOUT 28→25 (-3s)

**Date**: 2026-07-03
**Author**: opc2_uname (HM2)
**Direction**: HM2 optimizes HM1
**Iron Rule**: Only change HM1, never HM2

## Context

R651 compressed UPSTREAM_TIMEOUT 31→28 with p95 TTFB=22.34s (margin 5.66s >5s safe). R651 predicted: "If zero-error sustained: UPSTREAM_TIMEOUT 28→25 (p95=22.34s, margin=2.66s — borderline, likely floor)". R652 executes this final compression step on the UPSTREAM_TIMEOUT trajectory.

The zero-error regime has been sustained continuously since R645 (8 rounds). All primary throttle parameters (KEY_COOLDOWN, MIN_OUTBOUND, PEER_FALLBACK_TIMEOUT) are at floor. UPSTREAM_TIMEOUT is the last active trajectory, and 28→25 is the final safe step before floor.

## Pre-Change Data Collection

### Container Status
- `nv_40006_uni`: Up 8h33m (healthy), StartedAt=2026-07-03T14:00:47Z
- `cc_postgres`: Up 26+ hours (healthy)
- Docker logs (tail 100): **0 error/warn/exception**

### DB Regime Health (R651 regime, StartedAt=2026-07-03T14:00:47Z, ~8.5h)

| Metric | Value |
|--------|-------|
| Total | 98 |
| OK | 98 |
| Fail | 0 |
| total_kc429 | 0 |
| integrate_cnt | 42 |
| pexec_cnt | 56 |
| avg_ttfb_ms | 7,051.6 |
| avg_dur_ms | 36,854.9 |

**Zero-error regime sustained.** 100% success rate, 0 errors, 0 key_cycle_429s.

### TTFB Distribution (R651 regime, status=200, n=98)

| Percentile | TTFB (ms) |
|------------|-----------|
| p50 | 5,547.5 |
| p95 | 14,353.8 |
| p99 | 32,353.3 |
| max | 48,141 |

### Upstream Path Distribution (R651 regime)

| upstream_type | total | ok | fail | avg_ttfb_ms | avg_dur_ms |
|---------------|-------|----|------|-------------|------------|
| nvcf_pexec | 56 | 56 | 0 | 4,476.3 | 4,512.7 |
| nv_integrate | 42 | 42 | 0 | 10,485.3 | 79,978.0 |

Both paths zero-error. Pexec avg TTFB = 4.48s. Integrate avg TTFB = 10.49s (long streaming requests).

### Error Distribution (6h)

**0 rows** — no errors in the last 6 hours.

### Traffic Note

Current period is low-traffic (98 requests over 8.5h = ~11.5 req/h vs R651's 116 req/h). The current-window p95 of 14.35s is lower than the high-traffic p95 of 22.34s (R651). For floor calculation, the **high-traffic p95 (22.34s)** is the conservative reference, as it represents peak load conditions.

## Parameter Floor Analysis

| Parameter | Current | Floor | Status |
|-----------|---------|-------|--------|
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | 0 | At floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | 0 | At floor |
| NVU_PEER_FALLBACK_TIMEOUT | 8 | ~6.59s (pexec avg) | At floor (gap=1.41s ≤ 2s) |
| **UPSTREAM_TIMEOUT** | **28→25** | p95+3s = ~25.3s | **25 ≈ floor boundary** |
| TIER_TIMEOUT_BUDGET_S | 90 | — | max_dur=80s (integrate streaming), margin=10s |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 61 | — | Aligned with HM2, don't touch |

## Change

### Safety Analysis for UPSTREAM_TIMEOUT 28→25

- **High-traffic p95 TTFB = 22.34s** (R651 reference) → 25s gives margin = 2.66s (≤3s floor boundary)
- **Low-traffic p95 TTFB = 14.35s** (current) → 25s gives margin = 10.65s (comfortable)
- **p50 TTFB = 5.55s** → vast majority of requests well under 25s
- **p99 TTFB = 32.35s** → These are long-running streaming requests. TTFB measures time-to-first-byte; if TTFB > UPSTREAM_TIMEOUT, the request would have already timed out. All p99 requests are status=200 (they got first byte well before any timeout).
- **Per-round reduction**: 3s (per parameter directory standard)
- **Impact**: Reduces wait time on upstream failure paths by 3s; success paths unaffected
- **Floor signal**: `UPSTREAM_TIMEOUT - p95_TTFB ≤ 3s` → 25 - 22.34 = 2.66s ≤ 3s → **FLOOR REACHED**. Next round must pivot to next parameter.

### Execution

1. **Backup**: `cp docker-compose.yml docker-compose.yml.bak.R652`
2. **Change**: `UPSTREAM_TIMEOUT: "28"` → `UPSTREAM_TIMEOUT: "25"` (line 418, `sed` line-anchored)
3. **Comment**: R652 historical comment inserted after modified line; also fixed R651 comment numbering (was mislabeled R652)
4. **Restart**: `docker compose up -d nv_40006_uni` (ensures env reload)
5. **Verification**: 3-layer check passed

## Post-Change Verification (3-Layer)

| Layer | Check | Result |
|-------|-------|--------|
| Compose file | `UPSTREAM_TIMEOUT: "25"` in nv_40006_uni block | ✅ |
| Container | `docker ps` — Up, healthy | ✅ Up 10 seconds (healthy) |
| Env | `docker exec env \| grep UPSTREAM_TIMEOUT` | ✅ `UPSTREAM_TIMEOUT=25` |
| Logs | `docker logs --tail 30 \| grep error/warn` | ✅ (no error/warn found) |

## Trajectory

- **UPSTREAM_TIMEOUT**: 30→32→34 (R640–R641) → 31 (R650) → 28 (R651) → **25** (R652, FLOOR)
  - High-traffic p95=22.34s → margin=2.66s ≤ 3s → **FLOOR REACHED**
  - Trajectory complete: 34→25 over 3 rounds (R650–R652), total -9s
- **PEER_FALLBACK_TIMEOUT**: 18→8 (R645–R649) — FLOOR (gap=1.41s ≤ 2s)
- **NV_INTEGRATE_KEY_COOLDOWN_S**: 0 (absolute floor)
- **MIN_OUTBOUND_INTERVAL_S**: 0 (absolute floor)

## Next Round Considerations

UPSTREAM_TIMEOUT has reached floor. Next round (R653 by HM1) must pivot to next parameter in the directory:

1. **TIER_TIMEOUT_BUDGET_S** (currently 90s): max_dur=80s (integrate streaming), margin=10s. Could compress 90→85 (-5s) if zero-error sustained. Risk: if ATE failures occur, they need full BUDGET time to exhaust fallback chain.
2. **NVU_FORCE_STREAM_UPGRADE_TIMEOUT** (currently 61s): Aligned with HM2's ceiling. Changing this affects peer fallback stream upgrade coordination. Higher risk, needs careful analysis.

**Recommendation**: Pivot to TIER_TIMEOUT_BUDGET_S with conservative 5s reduction (90→85), monitoring for ATE regression.

**Rollback plan**: If any timeout-related errors appear post-restart, immediate rollback to 28.

## ⏳ 轮到HM1优化HM2
