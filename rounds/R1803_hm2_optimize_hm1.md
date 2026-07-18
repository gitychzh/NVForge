# R1803 (HM2→HM1): NVU_TIER_BUDGET_GLM5_2_NV 120→115 (-5s)

## 改前数据 (2026-07-18 22:50 UTC, 6h window)

### 6h SR by Model
| Model | Total | OK | Fail | SR% |
|---|---|---|---|---|
| glm5_2_nv | 24 | 24 | 0 | 100.0 |
| dsv4p_nv | 8 | 7 | 1 | 87.5 |

### Error Breakdown
| Model | Error Type | Count |
|---|---|---|
| dsv4p_nv | all_tiers_exhausted | 1 (real 502), 7 phantom 200 |

### ATE Detail (same NVCF degradation cluster 09:19-09:31 UTC, 13h ago — no new failures)
| Time | Duration | Status | Tiers | Notes |
|---|---|---|---|---|
| 09:19 | 56782ms | 502 | 1 | Real ATE |
| 09:22 | 100418ms | 200 | 1 | Phantom |
| 09:24 | 32244ms | 200 | 1 | Phantom |
| 09:26 | 23118ms | 200 | 1 | Phantom |
| 09:27 | 95148ms | 200 | 1 | Phantom |
| 09:30 | 14897ms | 200 | 1 | Phantom |
| 09:30 | 15328ms | 200 | 1 | Phantom |
| 09:31 | 29732ms | 200 | 1 | Phantom |

### glm5_2_nv Latency (successful, 6h)
| Metric | Value |
|---|---|
| Count | 24 |
| Avg | 10421ms |
| p50 | 9284ms |
| p95 | 18601ms |
| p99 | 21010ms |
| Max | 21582ms |

### dsv4p_nv Latency (successful, 6h)
| Metric | Value |
|---|---|
| Count | 7 |
| Avg | 44412ms |
| p50 | 29732ms |
| p95 | 98837ms |
| p99 | 100102ms |
| Max | 100418ms |

### Key Cycling
| Model | Cycles | Count |
|---|---|---|
| glm5_2_nv | 1 | 22 |
| glm5_2_nv | 2 | 2 |
100% of glm5_2_nv requests hit 429 key cycling (26 cycles on 24 requests). KEY_COOLDOWN_S=65, TIER_COOLDOWN_S=65.

### Tier Attempts
| Tier | Error | Count |
|---|---|---|
| glm5_2_nv | pexec_success | 24 |
| glm5_2_nv | pexec_SSLEOFError | 2 |

### Fallback
Zero fallback_occurred across all 32 requests. Zero peer-fb, zero ms_gw fallback.

### nv_gw Logs
Zero ERROR/WARN in last 100 lines. Clean.

### Drift Check
Container env matches compose for all tunable params. NVU_TIER_BUDGET_GLM5_2_NV=120 (pre-change).

## Decision: NVU_TIER_BUDGET_GLM5_2_NV 120→115 (-5s)

### Rationale
glm5_2_nv p99=21.0s, max=21.6s. The 120s budget was 5.5x the worst case — excessive. Reducing to 115s saves 5s on worst-case tier exhaustion (e.g. if all 5 keys enter 429 cooldown simultaneously) without affecting legitimate requests. All glm5_2_nv requests complete within 22s, well under 115s. Success path unaffected. Single-parameter, data-driven.

### Constraints
- Budget: 115+45=160 < 180 (TIER_TIMEOUT_BUDGET_S) ✓
- Peer-fb: 115+2=117 ≤ 122 (NVU_PEER_FALLBACK_TIMEOUT) ✓
- UPSTREAM_TIMEOUT=55 > max latency 21.6s ✓
- Single param, only HM1, never HM2
- glm5_2_nv p99 21.0s << 115s ✓

### Verification
- `docker compose up -d nv_gw` → restarted OK
- `curl localhost:40006/health` → {"status":"ok"}
- `docker exec nv_gw env | grep NVU_TIER_BUDGET_GLM5_2_NV` → 115

单参数少改多轮。铁律: 只改 HM1 不改 HM2。改前必有数据。
## ⏳ 轮到HM1优化HM2
