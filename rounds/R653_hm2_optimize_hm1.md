# R653: HM2→HM1 — TIER_TIMEOUT_BUDGET_S 90→85 (-5s)

**Date**: 2026-07-03 23:10 UTC
**Author**: opc2_uname (HM2 cron job)
**Target**: HM1 (`opc_uname@100.109.153.83`), container `nv_40006_uni`
**Iron Rule**: 只改HM1不改HM2

## Change

| Parameter | Old | New | Delta |
|-----------|-----|-----|-------|
| `TIER_TIMEOUT_BUDGET_S` | 90 | 85 | -5s |

**Single param per round.** All other parameters unchanged.

## Rationale

R652 completed the UPSTREAM_TIMEOUT trajectory (34→25, floor reached with margin=2.66s ≤3s). All primary params at floor (KEY_COOLDOWN=0, MIN_OUTBOUND=0, PEER_FALLBACK=8, UPSTREAM_TIMEOUT=25). R652 plan explicitly stated: "next round pivot to TIER_TIMEOUT_BUDGET_S (90→85)".

TIER_TIMEOUT_BUDGET_S controls the total time budget for all NV tier attempts (ATE path). Reducing from 90→85 compresses the ATE failure path by 5s — successful requests are unaffected (they complete well within budget).

## Data Collected (pre-change)

### Container env (confirmed)
```
UPSTREAM_TIMEOUT=25
TIER_TIMEOUT_BUDGET_S=90  →  85 (after change)
KEY_COOLDOWN_S=25
MIN_OUTBOUND_INTERVAL_S=0
NVU_PEER_FALLBACK_TIMEOUT=8
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=61
NVU_EMPTY_200_FASTBREAK=2
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NV_INTEGRATE_KEY_COOLDOWN_S=0
```

### DB stats (hermes_logs.nv_requests)

**Last 1h**: 4/4 OK (200), 0 fail — zero-error regime
**Last 2h**: 8/8 OK (200), 0 fail
**Last 6h**: 24/24 OK (200), 0 fail — zero-error regime sustained
**Last 24h**: 635 OK (200) / 38 fail (502, all_tiers_exhausted) — but ALL 38 failures from Jul 2 15:42-19:07 UTC (pre-R652, ~17h ago), ZERO failures since

### Latency analysis (last 6h, status=200)
- upstream_type: nvcf_pexec (24 req)
- avg duration: 3,953ms (3.95s)
- max duration: 16,942ms (16.9s) << 85s → margin 68.1s
- avg TTFB: 3,947ms
- p95 TTFB: 7,739ms (7.7s)

### Latency analysis (24h, status=200)
- nvcf_pexec: 314 req, max=56,925ms (57s) << 85s → margin 28s safe
- nv_integrate: 320 req, max=419,075ms (streaming, not subject to BUDGET)

### Docker logs (last 100 lines)
No errors/warnings. Only `[NV-THINKING-TIMEOUT]` info messages (thinking stream extended timeout 61s — expected behavior for glm5_2_nv thinking requests).

## Safety Analysis

| Metric | Value | Budget 85s | Margin |
|--------|-------|-----------|--------|
| 6h pexec max | 16.9s | 85s | 68.1s ✅ |
| 24h pexec max | 57.0s | 85s | 28.0s ✅ |
| 24h pexec p95 | 38.3s | 85s | 46.7s ✅ |

All margins comfortably safe. 85s still gives 3 keys × ~25s UPSTREAM_TIMEOUT = 75s + overhead, well within 85s budget. The 5s reduction only affects the ATE failure path (all_tiers_exhausted), not successful requests.

## Compose Edit

File: `/opt/cc-infra/docker-compose.yml` on HM1
Line 481 (inside `nv_40006_uni` service block):
- Old: `TIER_TIMEOUT_BUDGET_S: "90" # R576: ...`
- New: `TIER_TIMEOUT_BUDGET_S: "85" # R653 (HM2→HM1): BUDGET 90→85 (-5s). ...`

Method: `sudo sed -i '481s/"90"/"85"/'` then `sudo sed -i '481c\...'` for comment rewrite. Verified before restart.

## Execution

1. ✅ Compose value changed: 90→85 on line 481
2. ✅ Comment rewritten with R653 annotation
3. ✅ Verified: `sed -n '480,483p'` shows correct value + comment
4. ✅ Container recreated: `docker compose up -d nv_40006_uni`
5. ✅ Container env verified: `TIER_TIMEOUT_BUDGET_S=85`
6. ✅ Proxy started cleanly, no errors in startup logs

## Next Round Plan

Continue TIER_TIMEOUT_BUDGET_S trajectory if zero-error sustained:
- R654 (if safe): 85→80 (-5s), need 24h pexec max < 80s (currently 57s, margin 23s)
- R655 (if safe): 80→75 (-5s), need pexec max < 75s
- Floor target: ~75s (3 × UPSTREAM_TIMEOUT=25s)

Alternative params if BUDGET hits floor:
- `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` (currently 61)
- `NVU_EMPTY_200_FASTBREAK` (currently 2)
- `NVU_PEXEC_TIMEOUT_FASTBREAK` (currently 1)

## ⏳ 轮到HM1优化HM2
