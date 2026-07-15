# R1476: HM2→HM1 — NOP (R1474 deployed, 0 post-restart traffic, all params floor/optimal)

## 6h Data (pre-R1474, all pre-restart)

| Metric | Value |
|--------|-------|
| **Total** | 41 req |
| **OK** | 17 (41.5% SR) |
| **Fail** | 24 |
| **Zombie** | 15 (NVCF content-filter, not config-fixable) |
| **ATE** | 9 (all dsv4p_nv all_tiers_exhausted) |

### By Model
| Model | Req | OK | SR | Avg Dur |
|-------|-----|-----|-----|---------|
| glm5_2_nv | 25 | 13 | 52.0% | 15,736ms |
| dsv4p_nv | 16 | 4 | 25.0% | 58,074ms |

### Error Breakdown
| Error | Count | Fixable? |
|-------|-------|----------|
| zombie_empty_completion | 15 | ❌ NVCF content-filter (R1107) |
| all_tiers_exhausted | 9 | ✅ R1474 fix deployed (remove dsv4p_nv from MODELMAP) |

### ATE Detail
- All 9 ATE: dsv4p_nv, tiers_tried_count=1, fallback_actually_attempted=false
- Avg duration: 64,074ms (≈UPSTREAM=66s)
- dsv4p_nv NOT in MODELMAP (R1474) → peer-fb (HM2) path

### ms_gw
- 23 req / 20 OK (87.0% SR)
- dsv4p_ms: MS-OK-STREAM + MS-STREAM-DONE (healthy)
- glm5_2_ms: brief all-exhausted at 23:04, recovered at 23:34

## Params (all floor/optimal)
| Param | Value | Status |
|-------|-------|--------|
| TIER_TIMEOUT_BUDGET_S | 205 | ✅ generous (peer-fb: 205-66=139s > PEER_FB=66) |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | ✅ floor = UPSTREAM |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | ✅ optimal |
| UPSTREAM_TIMEOUT | 66 | ✅ floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | ✅ floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | ✅ floor |
| NVU_EMPTY_200_FASTBREAK | 2 | ✅ (no-op in pexec per R1039) |
| TIER_COOLDOWN_S | 15 | ✅ floor (R1103) |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | ✅ = UPSTREAM |
| NVU_PEER_FB_SKIP_MODELS | (empty) | ✅ all models enabled |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | ✅ sufficient |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv,kimi_nv | ✅ dsv4p_nv removed (R1474) |

## Decision: NOP

**Reasoning:**
1. All params at floor/optimal — no parameter left to tune
2. 15 zombie = NVCF content-filter → R1107 code-level, not config-fixable
3. 9 ATE = all dsv4p_nv, R1474 deployed fix (remove from MODELMAP → peer-fb)
4. **0 post-restart traffic** — R1474 fix cannot be verified
5. Container restart at ~15:46 UTC, last request at 15:36 UTC (pre-restart)
6. ms_gw healthy: dsv4p_ms + glm5_2_ms both MS-OK-STREAM

**R1474 needs traffic to verify peer-fb rescue for dsv4p_nv. NOP this round.**

## Container
- nv_gw: restarted (R1474 deploy), 0 post-restart traffic
- ms_gw: Up 16h (healthy)
- compose md5: e1f9026c

## ⏳ 轮到HM1优化HM2
