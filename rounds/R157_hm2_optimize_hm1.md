# R157: HM2→HM1 — 无变更 (全7参数均衡: 30min 99.5%, 1h 99.2%, 6h 98.6%; 0 429, 0 fallback; 4 ATE为NVCF server-side不可调; R154 BUDGET收益递减已验证; 少改多轮; 铁律:只改HM1不改HM2)

## 📊 数据采集 (2026-06-28 04:11 UTC, R156之后)

### Config Snapshot
| Parameter | Value |
|-----------|-------|
| UPSTREAM_TIMEOUT | 72 |
| TIER_TIMEOUT_BUDGET_S | 156 |
| KEY_COOLDOWN_S | 34 |
| TIER_COOLDOWN_S | 42 |
| MIN_OUTBOUND_INTERVAL_S | 19.0 |
| HM_CONNECT_RESERVE_S | 24 |
| PROXY_TIMEOUT | 300 |

### 30min Window
- **Total: 1131, Success: 1125, Errors: 6, Fallbacks: 0**
- Success rate: **99.5%** (↑ from R156's 99.3%)
- Avg: 22789ms, P50: 18875ms, P90: 38209ms, P95: 55681ms, P99: 115901ms

### 30min Error Breakdown
| Error Type | Count | Avg Duration |
|------------|-------|-------------|
| all_tiers_exhausted | 4 | 140791ms |
| NVStream_IncompleteRead | 1 | 19546ms |
| NVStream_TimeoutError | 1 | 109523ms |

### 30min Per-Key Success Latency
| Key | Count | Avg | P50 | P95 |
|-----|-------|-----|-----|-----|
| k0 (DIRECT) | 238 | 25140ms | 20835ms | 61111ms |
| k1 (DIRECT) | 223 | 22709ms | 18849ms | 60239ms |
| k2 (PROXY→7896) | 211 | 19799ms | 17362ms | 38504ms |
| k3 (PROXY→7897) | 228 | 21402ms | 18715ms | 45602ms |
| k4 (PROXY→7899) | 225 | 22122ms | 18831ms | 53478ms |

- DIRECT tail latency > PROXY continues (Pitfall #29): k0 p95=61111ms vs k2 p95=38504ms
- NVCF server-side variance, not config issue

### 30min Request Rate
- Avg: 2.6 req/min, Capacity at MOI=19s: 3.2 req/min (81% utilization)
- Max: 5 req/min in peak minute

### 24h all_tiers_exhausted by Hour
| Hour (UTC) | Count | |
|-----------|-------|--|
| 2026-06-27 02:00 | 1 | overnight |
| 2026-06-27 09:00 | 1 | daytime |
| 2026-06-27 10:00 | 4 | daytime |
| 2026-06-27 11:00 | 10 | daytime |
| 2026-06-27 13:00 | 5 | daytime |
| 2026-06-27 15:00 | 1 | daytime |
| 2026-06-27 16:00 | 7 | daytime |
| 2026-06-27 17:00 | 8 | daytime |
| 2026-06-27 18:00 | 2 | daytime |
| 2026-06-27 19:00 | 3 | daytime |
| 2026-06-28 01:00 | 1 | overnight |
| 2026-06-28 02:00 | 2 | overnight |
| **Total** | **45** | **91% daytime (RTC 09-19)** |

- ATE distribution confirms Pitfall #30: VARIABLE pattern, daytime concentration on 6/27
- R155 also saw daytime ATE (37/45 UTC 09-19) — consistent with NVCF server-side instability

### 30min 429 & key_cycle_429s
- **429 count: 0** ✅
- key_cycle_429s: 0-cycles=1117, 1-cycle=12, 2-cycles=1, 5-cycles=1
- 429 rate effectively zero

### 1h Window
- Total: 1192, Success: 1183, Errors: 9, Fallbacks: 0
- **Success rate: 99.2%**, Avg: 23053ms, P95: 56823ms

### 6h Window
- Total: 2049, Success: 2020, Errors: 29, Fallbacks: 0
- **Success rate: 98.6%**

### Back-to-Back Same-Key Rate
- 6.1% (6/98 pairs) — slightly elevated from R142's 0.0%, RR counter behavior per Pitfall #28
- Not a MIN_OUTBOUND_INTERVAL_S issue — no 429s triggered

### 24h Status Breakdown
| Status | Count | Avg | Min | Max |
|--------|-------|-----|-----|-----|
| 200 | 4514 | 29625ms | 1295ms | 233742ms |
| 429 | 5 | 172934ms | 138762ms | 219113ms |
| 502 | 45 | 120018ms | 19546ms | 166774ms |

### 24h Error Breakdown
| Error Type | Count | Avg |
|------------|-------|-----|
| all_tiers_exhausted | 45 | 129711ms |
| NVStream_TimeoutError | 4 | 102228ms |
| NVStream_IncompleteRead | 1 | 19546ms |

## 🎯 优化分析

### 逐参数评估
| Parameter | Value | Adjustment? | Reasoning |
|-----------|-------|-------------|-----------|
| UPSTREAM_TIMEOUT | 72 | ❌ No | P95=55.7s < 72s, no success-path timeout. ATE avg=140.8s ≈ 2×72-3.2s → NVCF server-side consuming budget. Decreasing would reduce ATE budget margin. |
| TIER_TIMEOUT_BUDGET_S | 156 | ❌ No | Margin=12s > 10s threshold. R154 proved diminishing returns beyond threshold (6 ATE at BUDGET=154 same as 156). |
| KEY_COOLDOWN_S | 34 | ❌ No | 0 429s in 30min. Cooldown sufficient. Potential -2s but no urgency — stability over optimization. |
| TIER_COOLDOWN_S | 42 | ❌ No | NVCF server-side ATE cooldown adequate. No tier exhaustion signals. |
| MIN_OUTBOUND_INTERVAL_S | 19.0 | ❌ No | Utilization 81% (2.6/3.2 req/min). Room exists but already at sweet spot. Pegged. |
| HM_CONNECT_RESERVE_S | 24 | ❌ No | No budget_exhausted_after_connect errors. |
| PROXY_TIMEOUT | 300 | ❌ No | Never a bottleneck. |

### 结论
**全7参数均衡**, 无单参数变更可改善指标:
- 30min 99.5% (↑ from R156 99.3%) — slight improvement from NVCF stability
- 0 429, 0 fallback across all windows
- 4 ATE/30min = NVCF server-side (Pitfall #30, daytime concentration confirmed)
- R154 budget diminishing returns reconfirmed
- DIRECT tail latency > PROXY (Pitfall #29) — NVCF server-side, not config issue

## 🔧 变更执行
无变更 — 稳定性即为最优状态

## ⚖️ 评判标准
- ✅ 更少报错: 6 errors/30min (4 ATE NVCF + 2 stream), 0 429, 0 fallback
- ✅ 更快请求: P50=18.9s, P95=55.7s — consistent with R155/R156
- ✅ 超低延迟: No regression in any latency percentile
- ✅ 稳定优先: Full equilibrium across all 7 parameters, 8th consecutive no-change round
- ✅ 铁律: 只改HM1不改HM2 — no changes needed, HM2 untouched

## ⏳ 轮到HM1优化HM2
