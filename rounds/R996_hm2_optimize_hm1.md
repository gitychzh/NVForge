# R996: HM2→HM1 — NOP (NVCF upstream degradation, all params at floor/optimal)

## Data (6h, HM1: nv_gw 40006, 2026-07-09 14:00–20:55 UTC)

### 6h Summary
```
total: 73  ok: 59  err: 14  SR: 80.8%  ATE: 14  fallback_occurred: 7 of 17 ATE rows
```

### Per-tier
| tier_model | cnt | ok | err | avg_OK_ms | p95_ms |
|---|---|---|---|---|---|
| glm5_2_nv | 48 | 40 | 8 | 10,527 | 112,060 |
| dsv4p_nv | 25 | 19 | 6 | 69,795 | 139,999 |

### Error breakdown (nv_requests)
| error_type | cnt | fallback_occurred=true | fallback_occurred=false |
|---|---|---|---|
| all_tiers_exhausted | 17 | 3 | 14 |

### Tier Attempts (nv_tier_attempts)
| error_type | cnt |
|---|---|
| NVCFPexecTimeout | 7 |
| 504_nv_gateway_timeout | 2 |
| IntegrateTimeout | 2 |
| empty_200 | 1 |

### Temporal Split
| window | total | ok | err | SR |
|---|---|---|---|---|
| Last 1h (19:55–20:55) | 21 | 15 | 6 | 71.4% |
| 1–3h ago (17:55–19:55) | 31 | 30 | 1 | 96.8% |
| 3–6h ago (14:00–17:55) | 21 | 14 | 7 | 66.7% |

### glm5_2_nv detail
| route | status | cnt | avg_ms |
|---|---|---|---|
| direct | 200 | 37 | 10,527 |
| direct | 502 | 8 | 87,139 |
| fallback | 200 | 3 | 5,530 |

NVCFPexecTimeout max=62,606ms, UPSTREAM=66 buffer=3.4s ≥ 3s ✓.

### dsv4p_nv detail
Pre-restart: 19/19 100% SR (all integrate-first → pexec fallback). avg 69,795ms, p95=139,999ms.

Post-restart (~20:47): NVCF pexec all 5 keys dead — 6 consecutive ATE with ABORT-NO-FALLBACK.
- Each: 504_nv_gateway_timeout on k4 → cycle to k5 → timeout at 49s → budget kill at 112s.
- Log: `All 1 tiers failed (ring tiers tried: ['dsv4p_nv']), elapsed=112055ms, ABORT-NO-FALLBACK`
- Peer-fb: `model=dsv4p_nv in peer-fb skip list (NVCF DEGRADING, peer same function also bad)`
- ms_gw fb: dsv4p_nv NOT in NVU_MS_GW_FALLBACK_MODELMAP (default: only glm5_2_nv→glm5_2_ms). dsv4p_ms is disabled placeholder in ms_gw config (`_disabled=True`).

### ms_gw (HM1 40007, 6h)
| metric | count |
|---|---|
| MS-OK / MS-OK-STREAM | 15 |
| VARIANT-EXHAUSTED | 23 |
| Exhausted rate | 60.5% |

## Current Config (nv_gw, all at floor/optimal)
```
UPSTREAM_TIMEOUT=66                 # buffer=3.4s ≥ 3s ✓ (NVCFPexecTimeout max=62,606ms)
TIER_TIMEOUT_BUDGET_S=112           # generous, >> UPSTREAM
NVU_TIER_BUDGET_GLM5_2_NV=64        # per-tier override, tighter for fast glm5_2 (avg 10.5s)
MIN_OUTBOUND_INTERVAL_S=0           # max throughput
KEY_COOLDOWN_S=25                   # floor
TIER_COOLDOWN_S=25                  # floor
NV_INTEGRATE_KEY_COOLDOWN_S=0       # floor
NVU_CONNECT_RESERVE_S=0             # floor
NVU_FORCE_STREAM_UPGRADE=0          # disabled (HM1 direct, no need)
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66 # aligned with UPSTREAM
NVU_FALLBACK_HEALTH_THRESHOLD=0.10  # R992 value
FALLBACK_HEALTH_THRESHOLD=0.05      # dead param (R919)
NVU_PEXEC_TIMEOUT_FASTBREAK=2       # R832c value (per-key US mihomo proxies)
NVU_EMPTY_200_FASTBREAK=3           # aggressive empty-200 fastbreak
KEY_AUTHFAIL_COOLDOWN_S=60          # R922 symmetric with HM2
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=45
NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv  # both models peer-fb blocked
NVU_MS_GW_FALLBACK_TIMEOUT=45
FALLBACK_GRAPH={}                   # R832: empty (same-model-only mandate)
```

## Analysis

### Root Cause: NVCF Upstream Degradation
The 14 ATE errors are caused by NVCF infrastructure degradation — NOT HM1 configuration issues:
1. **glm5_2_nv**: NVCFPexecTimeout on NVCF pexec function (max 62,606ms). 8 ATE across 48 reqs = 16.7% failure rate. 5 of these had ms_gw fallback blocked (internal ms_gw VARIANT-EXHAUSTED during those bursts).
2. **dsv4p_nv post-restart**: NVCF pexec function completely dead across all 5 keys. 504 timeout on every key attempt. No escape path because:
   - FALLBACK_GRAPH empty (R832 design: same-model only)
   - dsv4p_nv NOT in NVU_MS_GW_FALLBACK_MODELMAP (only glm5_2_nv→glm5_2_ms)
   - dsv4p_nv in NVU_PEER_FB_SKIP_MODELS (HM2 dsv4p_nv also degraded)
   - dsv4p_ms is disabled placeholder in ms_gw
3. **ms_gw**: ModelScope surge causing 60.5% VARIANT-EXHAUSTED rate. Even when nv_gw triggers ms_gw fallback for glm5_2_nv, ms_gw may also fail.

### Why NOP
All nv_gw parameters are at floor/optimal:
- UPSTREAM_TIMEOUT already at 66 (buffer ≥ 3s rule satisfied)
- All cooldowns at floor (0 or 25)
- Budgets generous (112s global, 64s per-tier for glm5_2)
- FASTBREAK=2 appropriate for US mihomo proxy paths
- No cross-model fallback possible (R832 mandate, FALLBACK_GRAPH empty)
- dsv4p_ms not implemented in ms_gw (cannot add to MODELMAP)
- Peer-fb skip list includes dsv4p_nv because HM2's NVCF function is also degraded
- NVU_FALLBACK_HEALTH_THRESHOLD at 0.10 (R992 value, only gates FALLBACK_GRAPH cross-model which is already empty)

No parameter change can fix NVCF upstream 504 timeouts across all 5 keys, NVCFPexecTimeout on glm5_2 function, or ModelScope VARIANT-EXHAUSTED bursts.

### Post-restart verification
Container restarted ~20:47. Pre-restart: dsv4p_nv 19/19 100% SR, glm5_2_nv 40/48 83.3% SR. Post-restart: dsv4p_nv 0/6 0% SR (NVCF dead on all 5 keys). Not a restart-caused regression — the NVCF function degradation coincides with the restart timing but the 504 timeouts are upstream NVCF-side.

## Decision: No Parameter Change

Single param discipline; iron rule: only change HM1 never HM2. All parameters at floor/optimal. NVCF upstream degradation (504 on all 5 dsv4p_nv keys, NVCFPexecTimeout on glm5_2_nv function, ModelScope VARIANT-EXHAUSTED) cannot be resolved from HM1 docker-compose.yml configuration.

## ⏳ 轮到HM1优化HM2