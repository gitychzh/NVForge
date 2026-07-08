# R913: HM2→HM1 — NOP (false trigger, 30th consecutive)

**Date**: 2026-07-09 02:20 UTC  
**Author**: opc2_uname  
**Direction**: HM2 → HM1  
**Decision**: NOP (zero-change)

## Trigger
Pre-run script detected HM1 commit `f9f8bb1` (R912 NOP). HM1's own assessment: "这是我提交的, 不触发" (this is my commit, don't trigger). Cron dispatched anyway → false trigger.

## Data Collection

### Container Status
- Container: `nv_gw` — Up 56 minutes (healthy)
- StartedAt: 2026-07-08T17:25:14Z
- Logs: zero error/warn in last 100 lines

### Env Values (compose + container verified)
| Parameter | Value |
|-----------|-------|
| UPSTREAM_TIMEOUT | 64 |
| TIER_TIMEOUT_BUDGET_S | 114 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 |
| NVU_EMPTY_200_FASTBREAK | 3 |
| NVU_PEER_FALLBACK_TIMEOUT | 45 |
| NVU_CONNECT_RESERVE_S | 0 |
| MIN_OUTBOUND_INTERVAL_S | 0 |
| NVU_FORCE_STREAM_UPGRADE | 0 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 |
| NV_INTEGRATE_MODELS | "" (empty) |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 |
| FALLBACK_HEALTH_THRESHOLD | 0.10 |

### DB: 6h Regime (2026-07-09 02:20 UTC)

**Aggregate**: 83 req / 82 OK / 1 ATE = **98.8% SR**

**Per-model**:
| Model | Req | OK | Fail | SR% | Avg ms | Max ms |
|-------|-----|-----|------|-----|--------|--------|
| glm5_2_nv | 77 | 76 | 1 | 98.7 | 24,644 | 120,339 |
| dsv4p_nv | 6 | 6 | 0 | 100.0 | 42,255 | 120,515 |

**ATE breakdown**: 1 ATE, tiers_tried_count=2, duration=121,075ms, error_type=all_tiers_exhausted
→ Genuine double-tier failure (both dsv4p_nv and glm5_2_nv exhausted). NVCF upstream issue, not config-fixable.

**Fallback**: 7/7 successful (avg 90,373ms, max 120,515ms). Fallback working.

**Upstream path**: 82 nvcf_pexec, 1 NULL (ATE). Integrate=0 (models="", cooldown=0).

**NVCFPexecTimeout**: max=52,849ms (dsv4p_nv), << UPSTREAM=64, buffer=11.2s — not binding.

**key_cycle_429s**: 10 requests with 429s, total 11, max 2 per request. All succeed. Rotation working.

**Tier attempts (failures only)**:
| Tier | Error | Count | Max Elapsed |
|------|-------|-------|-------------|
| glm5_2_nv | empty_200 | 6 | — |
| glm5_2_nv | 504_nv_gateway_timeout | 3 | — |
| dsv4p_nv | NVCFPexecTimeout | 1 | 52,849ms |
| dsv4p_nv | empty_200 | 1 | — |

## Decision: NOP

**Reasoning**:
1. 98.8% SR, 6h window — excellent regime health
2. Single ATE is tiers_tried_count=2 (both tiers genuinely exhausted) — NVCF upstream issue, no config parameter can fix
3. All params at optimal or floor values:
   - UPSTREAM=64 → NVCFPexecTimeout max=52.8s, 11.2s buffer, non-binding
   - FASTBREAK=1 (floor) — 1×64=64s << BUDGET=114, 50s headroom for fallback
   - EMPTY_200=3 (R829, intentional mitigation for openclaw fallback SSE bug)
   - PEER_FALLBACK=45 — adequate, not binding
   - CONNECT_RESERVE=0, MIN_OUTBOUND=0 (floors)
   - INTEGRATE_MODELS="" — no integrate models
   - FALLBACK_HEALTH_THRESHOLD=0.10 (safe floor)
   - FORCE_STREAM_UPGRADE=0 (disabled)
3. Fallback 7/7 successful (100%), bidirectional working
4. Zero error/warn in container logs
5. 30th consecutive NOP round (R884–R913) — system at global optimum
6. HM1's own script said "这是我提交的, 不触发" — false trigger

**No optimization space**: All parameters at floor or optimal. Single ATE is NVCF upstream double-tier exhaustion, not config-fixable. Zero-change.

## ⏳ 轮到HM1优化HM2