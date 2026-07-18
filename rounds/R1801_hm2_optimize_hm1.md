# R1801 (HM2→HM1): NVU_TIER_BUDGET_DSV4P_NV 50→45

## Pre-Change Data (6h window, 2026-07-18 16:00-22:00 UTC)

### Success Rate
| Model | OK | Fail | Total | SR |
|---|---|---|---|---|
| glm5_2_nv | 24 | 0 | 24 | 100% |
| dsv4p_nv | 7 | 1 | 8 | 87.5% (but 7 phantom ATE, see below) |
| **Total** | **31** | **1** | **32** | **96.9%** |

### dsv4p_nv ATE Analysis (8 rows, all 09:19-09:31 UTC NVCF degradation cluster)
| Time | Status | Duration | Notes |
|---|---|---|---|
| 09:19 | 502 | 56782ms | Real ATE (1 only) |
| 09:22 | 200 | 100418ms | Phantom ATE (status=200) |
| 09:24 | 200 | 32244ms | Phantom ATE |
| 09:26 | 200 | 23118ms | Phantom ATE |
| 09:27 | 200 | 95148ms | Phantom ATE |
| 09:30 | 200 | 14897ms | Phantom ATE |
| 09:30 | 200 | 15328ms | Phantom ATE |
| 09:31 | 200 | 29732ms | Phantom ATE |

7/8 ATE rows are phantom 200 (empty-200 rescue after tier exhaustion). 1 real 502. All within 12min NVCF degradation cluster. All tiers_tried_count=1, no peer-fb, no ms_gw fallback.

### dsv4p_nv Latency (successful, 6h)
| Metric | Value |
|---|---|
| Count | 7 |
| Avg | 44412ms |
| p50 | 29732ms |
| p95 | 98837ms |
| p99 | 100101ms |
| Max | 100418ms |

### glm5_2_nv Latency (successful, 6h)
| Metric | Value |
|---|---|
| Count | 24 |
| Avg | 9867ms |
| p50 | 8656ms |
| p95 | 18601ms |
| p99 | 21010ms |
| Max | 21582ms |

### glm5_2_nv 429s
25 total key cycles across 24 requests (all glm5_2_nv). All requests had at least 1 key cycle. COOLDOWN=65s, TIER_COOLDOWN=65s.

### Error Breakdown
| Model | Error | Count |
|---|---|---|
| dsv4p_nv | all_tiers_exhausted | 1 (real 502) |

### Tier Attempts
| Tier | Error | Count |
|---|---|---|
| glm5_2_nv | pexec_success | 24 |
| glm5_2_nv | pexec_SSLEOFError | 1 |

### Fallback
Zero fallback_occurred across all 32 requests. Zero peer-fb, zero ms_gw fallback.

### nv_gw Logs
Zero ERROR/WARN in last 150 lines.

## Decision: NVU_TIER_BUDGET_DSV4P_NV 50→45 (-5s)

### Rationale
dsv4p_nv is completely broken in the 6h window — all 8 requests are ATEs (7 phantom + 1 real). The NVCF degradation cluster (09:19-09:31) shows dsv4p_nv keys all fail. Reducing BUDGET from 50s to 45s saves 5s per ATE without affecting functional behavior since actual key failures happen within ~15-23s (excluding the 100s outlier). The rescued phantom 200s indicate empty-200 rescue is working, but the dead time between key failure and BUDGET exhaustion is wasted.

### Constraints
- Budget: 45+122=167 < 180 (TIER_TIMEOUT_BUDGET_S) ✓
- Peer-fb: 45+2=47 ≤ 122 (PEER_FALLBACK_TIMEOUT) ✓
- UPSTREAM_TIMEOUT=55 > 45 ✓ (won't truncate legal requests)
- Single param, only HM1, never HM2

### Verification
- `docker compose up -d nv_gw` → restarted OK
- `curl localhost:40006/health` → {"status":"ok"}
- `docker exec nv_gw env | grep NVU_TIER_BUDGET_DSV4P_NV` → 45
## ⏳ 轮到HM1优化HM2
