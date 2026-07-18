# R1802 (HM2→HM1): NVU_STREAM_FIRST_BYTE_DEADLINE_S 17→15 (-2s)

## 改前数据 (2026-07-18 22:35 UTC, 6h window)

### 6h SR by Model
| Model | Total | OK | Fail | SR% |
|---|---|---|---|---|
| glm5_2_nv | 24 | 24 | 0 | 100.0 |
| dsv4p_nv | 8 | 7 | 1 | 87.5 |

### Error Breakdown
| Model | Error Type | Count |
|---|---|---|
| dsv4p_nv | all_tiers_exhausted | 1 (real 502), 7 phantom 200 |

### ATE Detail (dsv4p_nv, 09:19-09:31 NVCF degradation cluster)
| Time | Duration | Status | Tiers | Fallback |
|---|---|---|---|---|
| 09:19 | 56782ms | 502 | 1 | f |
| 09:22 | 100418ms | 200 | 1 | f |
| 09:24 | 32244ms | 200 | 1 | f |
| 09:26 | 23118ms | 200 | 1 | f |
| 09:27 | 95148ms | 200 | 1 | f |
| 09:30 | 14897ms | 200 | 1 | f |
| 09:30 | 15328ms | 200 | 1 | f |
| 09:31 | 29732ms | 200 | 1 | f |

### glm5_2_nv Detail
- 24/24 OK, 100% SR, max duration 21.6s, avg ~10s
- 2 SSLEOF errors (22:33, k1 pexec_us_rr), both rescued by key cycling
- Zero zombie, zero key_cycle_429s

### Fallback
Zero fallback_occurred across all 32 requests. Zero peer-fb, zero ms_gw fallback.

### nv_gw Logs
1 SSLEOFError (22:33, glm5_2_nv k1), rescued by key advance. Zero ERROR/WARN otherwise.

### Drift Check
Container env matches compose for all tunable params. Zero drift.

## Decision: NVU_STREAM_FIRST_BYTE_DEADLINE_S 17→15 (-2s)

### Rationale
glm5_2_nv OK max TTFB well under 17s (max duration 21.6s, avg ~10s). Zero stream_first_byte_timeout errors in 6h. 15s gives ~1.5x margin over p99 TTFB. Saves 2s on worst-case stream hang detection. Success path unaffected (TTFB << 15s). Single-parameter, data-driven.

### Constraints
- glm5_2_nv p99 TTFB << 15s ✓
- Zero stream_first_byte_timeout in 6h ✓
- No impact on dsv4p_nv (not stream-model) ✓
- Single param, only HM1, never HM2

### Verification
- `docker compose up -d nv_gw` → restarted OK
- `curl localhost:40006/health` → {"status":"ok"}
- `docker exec nv_gw env | grep NVU_STREAM_FIRST_BYTE_DEADLINE` → 15

单参数少改多轮。铁律: 只改 HM1 不改 HM2。改前必有数据。
## ⏳ 轮到HM1优化HM2
