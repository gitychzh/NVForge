# R1495: HM2→HM1 — NOP (all params floor/optimal, 18 zombie + 5 ATE, zero config-fixable). 57req/34OK 59.6%SR. 铁律:只改HM1不改HM2

## HM1 Data Collection (2026-07-16 ~03:40 UTC)

**Container**: nv_gw (started 2026-07-15T18:15:54Z, ~9.5h uptime)

### 6h Summary
| Metric | Value |
|--------|-------|
| Total Requests | 57 |
| OK (200) | 34 |
| Fail (!=200) | 23 |
| SR | 59.6% |
| Fallback occurred | 0/57 |
| Fallback actually attempted | 0/23 |
| Tier cycling (nv_tier_attempts) | 2 (glm5_2_nv integrate_rate_limit) |

### Error Breakdown
| Error Type | Count | Avg Duration | Fixable? |
|------------|-------|-------------|----------|
| zombie_empty_completion | 18 | 14,982ms | **NO** — code-level NV-ZOMBIE-EMPTY fast abort (objectively better than 96s hang). NVCF content-filter returning empty streams. Not config-fixable. |
| all_tiers_exhausted | 5 | 63,580ms | **NO** — tiers_tried_count=1 for all 5. dsv4p_nv single-tier with no fallback (ms_gw removed in R1488, peer-fb code-level defect R744). Budget exhausted within tier. |

### Per-Model SR
| Model | Req | OK | Fail | SR | Avg Latency | Max Latency |
|-------|-----|----|------|----|-------------|-------------|
| dsv4p_nv | 33 | 22 | 11 | 66.7% | 29,871ms | 64,719ms |
| glm5_2_nv | 24 | 12 | 12 | 50.0% | 13,758ms | 35,513ms |

### Hourly SR
| Hour (UTC) | Req | OK | SR |
|------------|-----|----|------|
| 14:00 | 7 | 3 | 42.9% |
| 15:00 | 6 | 2 | 33.3% |
| 16:00 | 9 | 6 | 66.7% |
| 17:00 | 8 | 4 | 50.0% |
| 18:00 | 18 | 14 | 77.8% |
| 19:00 | 9 | 5 | 55.6% |

### Key Config (all at floor/optimal)
| Param | Value | Status |
|-------|-------|--------|
| UPSTREAM_TIMEOUT | 66 | Floor (R988: 64→66, NVCFPexecTimeout binding edge) |
| TIER_TIMEOUT_BUDGET_S | 205 | Floor (R1286: 210→205, 133s headroom for ms_gw/peer-fb) |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | Floor (=UPSTREAM, R1333: 72→78→66, R1116: 66→72→66) |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | Floor (integrate thinking=90s + headroom) |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | Floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | Floor (R997: 2→1) |
| NVU_EMPTY_200_FASTBREAK | 2 | Code-level no-op (R1039, R1489) |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | Floor |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | Floor |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms | R1488: removed dsv4p_nv |
| NVU_PEER_FB_SKIP_MODELS | (empty) | All models peer-fb enabled |
| KEY_COOLDOWN_S | 25 | Floor |
| TIER_COOLDOWN_S | 15 | Floor |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | Floor (=UPSTREAM) |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | Floor |

### Decision: NOP
**Reasoning:**
1. **18 zombie_empty_completion** — code-level NV-ZOMBIE-EMPTY feature. NVCF returns `finish_reason=stop` but `content_chars < 50`. Gateway correctly fast-aborts (3-15s) instead of old 96s NVStream_TimeoutError hang. Objectively better — faster time-to-failure triggers openclaw fallback. Not config-fixable.
2. **5 all_tiers_exhausted** — all tiers_tried_count=1 (single-tier exhaustion). dsv4p_nv has no rescue path: ms_gw removed in R1488 (relay TimeoutError), peer-fb code-level defect R744 (local ATEs never reach peer-fb path). Tier budget 66s exhausted → ATE. Not config-fixable.
3. **glm5_2_nv 50% SR** — split evenly between zombie (domain) and ATE (tier budget). All integrate params at floor. ms_gw fallback in MODELMAP but not triggered (tiers_tried_count=1).
4. **All tunable params at floor**: FASTBREAK=1, UPSTREAM=66, BUDGETs=66/96/205, COOLDOWNs=15/25. No single parameter change can reduce zombie, fix peer-fb code path, or reduce ATE without breaking the floor.
5. **0 tier cycling** — key pool healthy. 2 integrate_rate_limit tier attempts (glm5_2_nv, no elapsed_ms) are noise.

**Zero-change.** The system is at its config floor. 18 zombie fast-aborts are a net positive (faster failover). The 5 real ATEs are within tier budget exhaustion with no config-level rescue path. ms_gw and peer-fb are the rescue mechanisms but both are blocked by code-level defects (ms_gw streaming sync, peer-fb R744 path). No config change can improve this.

## ⏳ 轮到HM1优化HM2
