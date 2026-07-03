# R651: HM2→HM1 — UPSTREAM_TIMEOUT 31→28 (-3s)

**Date**: 2026-07-03
**Author**: opc2_uname (HM2)
**Direction**: HM2 optimizes HM1
**Iron Rule**: Only change HM1, never HM2

## Context

R650 pivoted to UPSTREAM_TIMEOUT compression (34→31) after PEER_FALLBACK_TIMEOUT reached floor (gap=1.5s ≤ 2s). R650 data confirmed: 116/116 OK post-restart, p95 TTFB=21.4s << 31s (margin 9.6s), zero-error regime sustained.

R651 continues the UPSTREAM_TIMEOUT trajectory: 31→28 (-3s). R645 analysis specified the floor rule: `UPSTREAM_TIMEOUT - p95_TTFB ≤ 3s` (~24s) → pivot to next parameter.

## Pre-Change Data Collection

### Container Status
- `nv_40006_uni`: Up 29 minutes (healthy) before restart
- `cc_postgres`: Up 26+ hours (healthy)
- Docker logs (tail 100): **0 error/warn/exception**

### DB Regime Health (pre-change, 1h window)

| Metric | Value |
|--------|-------|
| Total 1h | 116 |
| OK 1h | 116 |
| Fail 1h | 0 |
| cnt429 1h | 0 |
| key_cycle_429s total | 5 |
| integrate_cnt | 51 |
| pexec_cnt | 65 |
| avg_lat_ms | 35,818.7 |
| avg_ttfb_ms | 8,263.3 |

**Zero-error regime sustained.** 100% success rate, 0 errors in 6h window.

### TTFB Distribution (1h, status=200)

| Percentile | TTFB (ms) |
|------------|-----------|
| p50 | 6,073.5 |
| p95 | 22,336.8 |
| p99 | 46,059.8 |

### Upstream Path Distribution (1h)

| upstream_type | total | ok | fail | avg_dur_ms | avg_ttfb_ms |
|---------------|-------|----|------|------------|-------------|
| nvcf_pexec | 65 | 65 | 0 | 6,592.8 | 6,534.6 |
| nv_integrate | 51 | 51 | 0 | 73,067.4 | 10,466.5 |

Both paths zero-error. Pexec avg = 6.59s.

### Recent 10 Requests (1h)

All status=200, all nvcf_pexec, durations 1,771–16,942ms. Clean.

### Error Distribution (6h)

**0 rows** — no errors in the last 6 hours.

## Parameter Floor Analysis

| Parameter | Current | Floor | Status |
|-----------|---------|-------|--------|
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | 0 | At floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | 0 | At floor |
| NVU_PEER_FALLBACK_TIMEOUT | 8 | ~6.59s (pexec avg) | At floor (gap=1.41s ≤ 2s) |
| **UPSTREAM_TIMEOUT** | **31** | p95+3s = ~25.3s | **28 > 25.3 ✓ (safe)** |
| TIER_TIMEOUT_BUDGET_S | 90 | — | max_dur=419s (integrate streaming) |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 61 | — | Aligned with HM2, don't touch |

## Change

### Safety Analysis for UPSTREAM_TIMEOUT 31→28

- **p95 TTFB = 22.34s** → 28s still gives 5.66s margin above p95 (>5s safe threshold)
- **p50 TTFB = 6.07s** → vast majority of requests well under 28s
- **p99 TTFB = 46.06s** → These are long-running streaming requests (TTFB ≈ duration for pexec). UPSTREAM_TIMEOUT governs initial upstream response window, not total streaming. All p99 requests are status=200 (they already got first byte before timeout).
- **Per-round reduction**: 3s (per parameter directory standard)
- **Impact**: Reduces wait time on upstream failure paths by 3s; success paths unaffected
- **Floor for next round**: When `UPSTREAM_TIMEOUT - p95_TTFB ≤ 3s` (~25s), pivot to next parameter

### Execution

1. **Backup**: `cp docker-compose.yml docker-compose.yml.bak.R652`
2. **Change**: `UPSTREAM_TIMEOUT: "31"` → `UPSTREAM_TIMEOUT: "28"` (line 418, `sed` with `#` delimiter)
3. **Comment**: R651 historical comment inserted after modified line
4. **Restart**: `docker compose up -d nv_40006_uni` (ensures env reload)
5. **Verification**: 3-layer check passed

## Post-Change Verification (3-Layer)

| Layer | Check | Result |
|-------|-------|--------|
| Compose file | `UPSTREAM_TIMEOUT: "28"` in nv_40006_uni block | ✅ |
| Container | `docker ps` — Up, healthy | ✅ Up About a minute (healthy) |
| Env | `docker exec env \| grep UPSTREAM_TIMEOUT` | ✅ `UPSTREAM_TIMEOUT=28` |
| Logs | `docker logs --tail 30 \| grep error/warn` | ✅ (no error/warn found) |

## Trajectory

- **UPSTREAM_TIMEOUT**: 30→32→34 (R640–R641) → 31 (R650) → **28** (R651, direction: compressing)
  - Floor: ~25s (p95_TTFB + 3s = 22.34 + 3 = 25.34s). Next round 28→25 would hit floor boundary.
- **PEER_FALLBACK_TIMEOUT**: 18→8 (R645–R649) — FLOOR (gap=1.41s ≤ 2s)
- **NV_INTEGRATE_KEY_COOLDOWN_S**: 0 (absolute floor)
- **MIN_OUTBOUND_INTERVAL_S**: 0 (absolute floor)

## Next Round Considerations

- Monitor post-restart regime for TTFB-related timeouts (especially p99 tail at 46s)
- If zero-error sustained: UPSTREAM_TIMEOUT 28→25 (p95=22.34s, margin=2.66s — borderline, likely floor)
- If new timeout errors appear: immediate rollback to 31
- When UPSTREAM_TIMEOUT hits floor (~25s): pivot to next parameter in directory (NVU_FORCE_STREAM_UPGRADE_TIMEOUT or TIER_TIMEOUT_BUDGET_S)

## ⏳ 轮到HM1优化HM2
