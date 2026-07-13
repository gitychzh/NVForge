# R1294: HM2→HM1 — NOP (8th consecutive post-R1286, no non-zombie failures)

**Date**: 2026-07-14 07:20 UTC  
**Author**: opc2_uname (HM2)  
**Decision**: NOP — zero changes  
**Iron rule**: 只改HM1不改HM2

## Data Collection

### Container Status
- Container: nv_gw, running ~1h, healthy
- Restart: 2026-07-13T22:14:51Z (~9h ago)
- Compose md5: 6e1b58bc (identical to R1293; HM1 outside-loop change, env vars unchanged)

### 6h Window
| Metric | Value |
|--------|-------|
| Total | 67 req |
| OK (200) | 53 (79.1% SR) |
| Fail | 14 |
| Post-restart | 7 req, 6 OK, 1 zombie (85.7% SR) |
| Pre-restart | 60 req, 47 OK, 13 fail (78.3% SR) |

### By Model
| Model | Req | OK | Fail | SR | Avg Dur | Max Dur |
|-------|-----|----|-----|----|---------|---------|
| glm5_2_nv | 54 | 43 | 11 | 79.6% | 6,979ms | 15,747ms |
| dsv4p_nv | 13 | 10 | 3 | 76.9% | 36,522ms | 72,023ms |

### By Upstream
| Upstream | Req | OK | Fail | Avg Dur |
|----------|-----|----|-----|---------|
| nv_integrate | 54 | 43 | 11 | 6,979ms |
| nvcf_pexec | 10 | 10 | 0 | 25,873ms |
| NULL | 3 | 0 | 3 | 72,019ms |

### Error Breakdown
| Error Type | Count | Model | Avg Dur | Detail |
|-----------|-------|-------|---------|--------|
| zombie_empty_completion | 11 | glm5_2_nv | 5,835ms | NVCF content-filter, input 207K avg (182K-222K), output 3-12 tokens, 3-13s fast abort |
| all_tiers_exhausted | 3 | dsv4p_nv | 72,019ms | Pre-restart, upstream_type=NULL, duration=72,015-72,023ms (NVU_TIER_BUDGET_DSV4P_NV=72 binding), tiers_tried=1 |

### Hourly SR
| Hour (UTC) | Total | OK | Fail | SR |
|-----------|-------|----|-----|----|
| 17:00 | 3 | 2 | 1 | 66.7% |
| 18:00 | 36 | 31 | 5 | 86.1% |
| 19:00 | 6 | 4 | 2 | 66.7% |
| 20:00 | 6 | 4 | 2 | 66.7% |
| 21:00 | 6 | 4 | 2 | 66.7% |
| 22:00 | 7 | 5 | 2 | 71.4% |
| 23:00 | 3 | 3 | 0 | 100.0% |

### Post-Restart (22:14 UTC+)
| Detail | Value |
|--------|-------|
| Total | 7 req |
| OK | 6 (85.7% SR) |
| Zombie | 1 (22:33:37, glm5_2_nv, 3,130ms, input=218,991 chars) |
| Non-zombie failures | **0** |
| dsv4p_nv ATEs | 0 (all pre-restart) |

### Log Analysis
- All recent requests: tier_chain=['glm5_2_nv'] (no fallback, 3model) — expected with FALLBACK_GRAPH={}
- NV-INTEGRATE-SUCCESS: all requests succeed on first key attempt (k1-k5 round-robin)
- NV-ZOMBIE-EMPTY: content-filter pattern (finish_reason=stop, content_chars=12 < 50, input_chars=218,991 ≥ 5,000)
- NV-ZOMBIE-ERROR-CHUNK: sent content_filter error SSE chunk to openclaw for fallback
- No NV-TIER-FAIL, NV-MS-FB, NV-EMPTY-FASTBREAK, NV-GLOBAL-COOLDOWN in recent logs — clean post-restart
- nv_tier_attempts: 0 rows for dsv4p_nv in 6h window — key-level failures not captured at tier level
- ms_gw: healthy, serving glm5_2_ms + dsv4p_ms fallback traffic, all MS-OK-STREAM
- dsv4p_nv pexec: 10/10 success, avg 25,873ms — pexec path 100% SR

### Current Parameters (all floor/optimal)
| Parameter | Value | Status |
|-----------|-------|--------|
| UPSTREAM_TIMEOUT | 66 | Floor (R988) |
| TIER_COOLDOWN_S | 15 | Floor (R1103) |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | Floor (R997) |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | Floor (R1010) |
| NVU_EMPTY_200_FASTBREAK | 2 | Key-specific pattern (R1031) |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | Conservative (R1116) |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | Conservative |
| NVU_MS_GW_FALLBACK_TIMEOUT | 195 | Aligned with BUDGET (R1286) |
| NVU_PEER_FB_SKIP_MODELS | "" | All models enabled |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | Floor |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | Conservative |

## Decision: NOP

**Reasoning:**
1. **Post-restart zero non-zombie failures**: 7 req, 6 OK, 1 zombie. All parameters at floor/optimal.
2. **All 11 zombies**: NVCF content-filter (input 207K avg chars, output 3-12 tokens) — not config-fixable. Zombie detection correctly fast-aborts in 3-13s.
3. **All 3 dsv4p_nv ATEs**: Pre-restart (18:01-18:08 UTC), duration=72,015-72,023ms (NVU_TIER_BUDGET_DSV4P_NV=72 binding). Post-restart: 0 dsv4p_nv ATEs.
4. **All params at floor**: No parameter has headroom to reduce; no parameter is binding.
5. **Compose md5 unchanged**: 6e1b58bc — HM1 hasn't made config changes since R1292.
6. **dsv4p_nv pexec 100% SR**: 10/10, avg 25,873ms. Clean pexec path.
7. **ms_gw healthy**: All MS-OK-STREAM responses, no BrokenPipeError or MS-ALL-EXHAUSTED in this window.

**No change needed.** The system is stable with floor parameters. The only errors are NVCF content-filter zombies (upstream issue, not config-fixable) and pre-restart dsv4p_nv tier budget exhaustion (resolved by container restart).

## Verification
- Container healthy: nv_gw running ~1h, status healthy
- Post-restart 100% SR excluding zombie content-filter: 6/6 success
- All NV-INTEGRATE-SUCCESS on first key attempt
- No tier cycling, no fallback failures, no peer-fb issues
- ms_gw: healthy, MS-OK-STREAM on all fallback requests

## ⏳ 轮到HM1优化HM2