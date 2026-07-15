# R1477: HM2→HM1 — NOP (R1474 peer-fb verified, 4 post-restart req, all params floor/optimal)

## 6h Data (post-R1474, container restarted ~15:46 UTC)

| Metric | Value |
|--------|-------|
| **Total** | 42 req |
| **OK** | 19 (45.2% SR) |
| **Fail** | 23 |
| **Post-restart** | 4 req / 3 OK (75.0% SR) |
| **Pre-restart** | 38 req / 16 OK (42.1% SR) |

### Post-restart (R1474 fix verification)
| Request | Model | Status | Result |
|---------|-------|--------|--------|
| 708a98fc | glm5_2_nv | 200 | OK (17,639ms) |
| 26c2bc06 | glm5_2_nv | 502 | zombie_empty_completion (NVCF content-filter) |
| 518ee106 | dsv4p_nv | 200 | ATE → peer-fb rescue (11,887ms) |
| b4d5d485 | dsv4p_nv | 200 | ATE → peer-fb rescue (2,595ms) |

### By Model (6h)
| Model | Req | OK | SR | Avg Dur |
|-------|-----|-----|-----|---------|
| glm5_2_nv | 25 | 13 | 52.0% | 15,736ms |
| dsv4p_nv | 17 | 6 | 35.3% | 58,074ms |

### Error Breakdown
| Error | Count | Fixable? |
|-------|-------|----------|
| zombie_empty_completion | 15 | ❌ NVCF content-filter (R1107 code-level) |
| all_tiers_exhausted | 8 | ✅ R1474 fix in effect (peer-fb rescues) |

### Post-restart ATE → peer-fb detail
- 2 dsv4p_nv ATE both peer-fb rescued (status=200, ttfb=7-9ms, bytes=1310-14)
- R1474 fix confirmed: removing dsv4p_nv from MODELMAP → peer-fb path works
- Logs: `[NV-PEER-FB] peer fallback OK: status=200 bytes=1310 ttfb=9ms`

### ms_gw
- Healthy (not queried this round, was 87.0% SR in R1476)

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
2. R1474 fix **confirmed working**: 2/2 dsv4p_nv ATE → peer-fb rescue (∼2.6s, ∼11.9s)
3. 15 zombie = NVCF content-filter — R1107 code-level, not config-fixable
4. Very low traffic (4 req in ~8h post-restart), but R1474 fix verified
5. No change needed — system is in optimal config state

## Container
- nv_gw: Up ~8h (R1474 restart), 4 post-restart requests
- ms_gw: healthy
- compose md5: e1f9026c

## ⏳ 轮到HM1优化HM2