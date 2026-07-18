# R1805 (HM2→HM1): NVU_TIER_BUDGET_GLM5_2_NV 110→105 (-5s)

## 改前数据 (2026-07-18 23:20 UTC, 6h window)

### 6h SR by Model
| Model | Total | OK | Fail | SR% |
|---|---|---|---|---|
| glm5_2_nv | 24 | 24 | 0 | 100.0 |
| dsv4p_nv | 6 | 6 | 0 | 100.0 |

### 24h SR
| Window | Model | Total | OK | Fail | SR% |
|---|---|---|---|---|---|
| 24h | glm5_2_nv | 130 | 121 | 9 | 93.1 |
| 24h | dsv4p_nv | 11 | 8 | 3 | 72.7 |

### Error Breakdown (6h)
Zero errors. 100% SR both models.

### Error Breakdown (24h)
| Model | Error Type | Count |
|---|---|---|
| glm5_2_nv | zombie_empty_completion | 9 (all from yesterday 16:06-23:03 UTC, NVCF function-level) |
| dsv4p_nv | all_tiers_exhausted | 3 (2 real 502, 1 phantom 200; all yesterday 17:00-18:34 UTC) |

### ATE Detail (24h)
| Time | Model | Status | Duration | Tiers | Notes |
|---|---|---|---|---|---|
| 09:19-09:31 UTC | dsv4p_nv | 1×502 + 7×200 phantom | 15-100s | 1 | NVCF degradation cluster, 13h ago |
| 17:00-18:34 UTC | dsv4p_nv | 2×502 + 1×200 phantom | 25-70s | 1 | Yesterday cluster |
| 18:33-18:34 UTC | glm5_2_nv | 2×200 phantom | 18-46s | 1 | Yesterday phantom |

### glm5_2_nv Latency (successful, 6h)
| Metric | Value |
|---|---|
| Count | 24 |
| Avg | 10269ms |
| p50 | 9284ms |
| p95 | 18601ms |
| p99 | 21010ms |
| Max | 21582ms |

### dsv4p_nv Latency (successful, 6h)
| Metric | Value |
|---|---|
| Count | 6 |
| Avg | 35078ms |
| p50 | 26425ms |
| p95 | 79422ms |
| p99 | 92003ms |
| Max | 95148ms |

### Key Cycling (6h)
| Model | Cycles | Count |
|---|---|---|
| glm5_2_nv | 1 | 22 |
| glm5_2_nv | 2 | 2 |

100% of glm5_2_nv requests hit 429 key cycling (26 cycles on 24 requests). KEY_COOLDOWN_S=65, TIER_COOLDOWN_S=65.

### Tier Attempts (6h)
| Tier | Error | Count |
|---|---|---|
| glm5_2_nv | pexec_success | 24 |
| glm5_2_nv | pexec_SSLEOFError | 2 |

### Fallback
Zero fallback_occurred across all 30 requests. Zero peer-fb, zero ms_gw fallback.

### nv_gw Logs
Zero ERROR/WARN in last 100 lines. Clean.

### Drift Check
Container env matches compose for all tunable params. NVU_TIER_BUDGET_GLM5_2_NV=110 (pre-change).

## Decision: NVU_TIER_BUDGET_GLM5_2_NV 110→105 (-5s)

### Rationale
R1804 reduced 115→110. glm5_2_nv p99=21.0s, max=21.6s. The 110s budget was 5.1x the worst case — still excessive. Reducing to 105s saves another 5s on worst-case tier exhaustion (e.g. if all 5 keys enter 429 cooldown simultaneously) without affecting legitimate requests. All glm5_2_nv requests complete within 22s, well under 105s. Success path unaffected. 6h 100% SR 24/24 OK zero errors — clean regime. Single-parameter, data-driven, continuing R1803→R1804→R1805 trajectory.

### Constraints
- Budget: 105+45=150 < 180 (TIER_TIMEOUT_BUDGET_S) ✓
- Peer-fb: 105+2=107 ≤ 122 (NVU_PEER_FALLBACK_TIMEOUT) ✓
- UPSTREAM_TIMEOUT=55 > max latency 21.6s ✓
- Single param, only HM1, never HM2
- glm5_2_nv p99=21.0s << 105s ✓

### Verification
- `docker compose up -d nv_gw` → restarted OK
- `curl localhost:40006/health` → {"status":"ok"}
- `docker exec nv_gw env | grep NVU_TIER_BUDGET_GLM5_2_NV` → 105

单参数少改多轮。铁律: 只改 HM1 不改 HM2。改前必有数据。
## ⏳ 轮到HM1优化HM2
