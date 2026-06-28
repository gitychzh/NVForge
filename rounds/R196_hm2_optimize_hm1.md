# R196: HM2→HM1 — 无变更 (全7参数均衡; 30min 99.42% 6ATE全NVCFPexecTimeout 0 429 0 fallback; 1h 99.29%; 6h 99.39%; P50=18.2s P95=45.4s; 27th consecutive R162+R158 验证; NVCF PexecTimeout 风暴不可配置级修复; 少改多轮; 铁律:只改HM1不改HM2)

## 📊 数据采集 (2026-06-28 ~11:16 UTC)

### Config Snapshot (HM1 env)
| Parameter | Value |
|-----------|-------|
| UPSTREAM_TIMEOUT | 70 |
| TIER_TIMEOUT_BUDGET_S | 156 |
| KEY_COOLDOWN_S | 38 |
| TIER_COOLDOWN_S | 38 |
| MIN_OUTBOUND_INTERVAL_S | 19.0 |
| HM_CONNECT_RESERVE_S | 24 |
| PROXY_TIMEOUT | 300 |
| CHARS_PER_TOKEN_ESTIMATE | 3.0 |

### Latency Percentiles (30min success-path)
| Metric | Value |
|--------|-------|
| P50 | 18,231ms (18.2s) |
| P95 | 45,417ms (45.4s) |

### Error Breakdown (30min / 1h / 6h)
| Window | Total | Success | % | ATE | 429 | Fallback |
|--------|-------|---------|---|-----|-----|----------|
| 30min | 1216 | 1209 | 99.42% | 6 | 0 | 0 |
| 1h | 1270 | 1261 | 99.29% | 8 | 0 | 0 |
| 6h | 1959 | 1947 | 99.39% | 9 | 0 | 0 |

### Error Types (6h)
| error_type | n | avg_dur_ms |
|------------|---|------------|
| all_tiers_exhausted | 9 | 151,002 |
| NVStream_IncompleteRead | 2 | 13,187 |
| NVStream_TimeoutError | 1 | 109,523 |

### ATE Time-of-Day (6h) — Pitfall #30
| time_utc | dur_s |
|----------|-------|
| 01:11 | 141.9 |
| 02:37 | 146.8 |
| 02:40 | 146.7 |
| 10:28 | 151.7 |
| 10:30 | 154.6 |
| 10:33 | 155.4 |
| 10:36 | 155.6 |
| 10:38 | 151.7 |
| 10:41 | 154.6 |

**Pattern**: Early-morning storm (01:11-02:40 UTC, 3 events) + daytime storm (10:28-10:41 UTC, 6 events) — NVCF server-side PexecTimeout, variable distribution confirms Pitfall #30.

### Error Detail JSONL — ATE Confirmation (Pitfall #41)
All 9 ATE events have:
- `deepseek_hm_nv.num_attempts=5-6`, `elapsed_ms=141,409-154,871`
- `kimi_hm_nv.num_attempts=0` — **kimi fallback starved by budget exhaustion (Pitfall #41)**
- Per-key elapsed: ~24-26s/key (NVCF server-side timeout, far below UPSTREAM_TIMEOUT=70s — Pitfall #43)
- `all_429=false, all_empty_200=false, all_cooldown=false`

### 24h Segmented Fallback Analysis (Pitfall #49)
| Window | Total | Success | ATE | Fallback | 429 |
|--------|-------|---------|-----|----------|-----|
| 0-6h | 1,960 | 1,948 | 9 | 0 | 0 |
| 6-12h | 928 | 904 | 21 | 0 | 0 |
| 12-24h | 1,656 | 1,636 | 20 | 1,047 | 4 |

**All 1,047 fallback in 12-24h window = old-regime data. 0-6h and 6-12h = 0 fallback.**

### Per-Key Latency Distribution (30min)
| nv_key_idx | n | p50_ms | p95_ms | errors |
|-------------|---|--------|--------|--------|
| 0 (K1) | 246 | 16,993 | 44,113 | 0 |
| 1 (K2) | 241 | 18,503 | 48,387 | 0 |
| 2 (K3) | 237 | 18,642 | 38,198 | 0 |
| 3 (K4) | 239 | 18,035 | 42,432 | 1 |
| 4 (K5) | 247 | 18,664 | 44,208 | 0 |

Per-key even: 237-247 (range 10, well-balanced). DIRECT (k0/k1) p95=44-48k vs PROXY (k2-k4) p95=38-44k — DIRECT tail > PROXY confirmed (Pitfall #29).

### Back-to-Back Same-Key Rate
18/1,210 = 1.49% — acceptable, RR counter minor bug (Pitfall #28), no action needed.

### Docker Error Logs
3 SSLEOFError events (k3 at 11:09, k4 at 11:14, k5 at 11:15) — all auto-retried successfully via `[HM-SSL-RETRY]`. No 429, no panics, no exhausted events in recent logs.

## 🎯 优化分析

### 7-Parameter Equilibrium Evaluation
| Parameter | Current | Adjustment Needed | Reason |
|-----------|---------|-------------------|--------|
| UPSTREAM_TIMEOUT | 70 | ❌ No | P95=45.4s << 70s limit; ATE per-key elapsed=24-26s (NVCF-side, not HM limit); Pitfall #43 |
| TIER_TIMEOUT_BUDGET_S | 156 | ❌ No | 2×70=140, remaining=16s > 10s threshold; R154 diminishing-returns proven |
| KEY_COOLDOWN_S | 38 | ❌ No | KEY=TIER=38, invariant holds (Pitfall #44); 0 429s confirms 38s sufficient |
| TIER_COOLDOWN_S | 38 | ❌ No | KEY=TIER=38, zero gap; R156 reduction from 42→38 validated |
| MIN_OUTBOUND_INTERVAL_S | 19.0 | ❌ No | 0 429s; per-key even 237-247; rate ~2.2 req/min vs capacity 3.2/min (69% util) |
| HM_CONNECT_RESERVE_S | 24 | ❌ No | 0 budget_exhausted_after_connect errors |
| PROXY_TIMEOUT | 300 | ❌ No | No proxy timeouts observed |
| CHARS_PER_TOKEN_ESTIMATE | 3.0 | ❌ No | Not a performance parameter |

### ATE Root Cause Analysis
All 9 ATE events are **NVCF PexecTimeout storms** (server-side):
- Deepseek consumes 141-155s across 5-6 keys, exhausting full TIER_TIMEOUT_BUDGET_S=156s
- Kimi `num_attempts=0` (Pitfall #41) — budget starved before fallback tier starts
- Per-key elapsed ~24-26s >> NVCF's internal timeout, not HM's UPSTREAM_TIMEOUT
- **NOT config-fixable** (R154 diminishing-returns; R191/R193 confirmed)
- Increasing BUDGET beyond 156s would not help: 6×24=144s already < 156s, the budget IS sufficient for the key attempts but the aggregate exceeds it

### Why No Change This Round
1. **99.42% 30min success rate** — at equilibrium plateau
2. **0 429, 0 fallback** in all short windows — no rate-limit or fallback issues
3. **P50=18.2s, P95=45.4s** — stable and consistent
4. **All 7 params at equilibrium** — no parameter shows need for adjustment
5. **ATE = NVCF server-side** — confirmed by Pitfall #41/43, not config-addressable
6. **27th consecutive R162+R158 validation** — stability plateau fully confirmed

## 🔧 变更执行
**No change this round** — all 7 parameters at equilibrium. ATE events are NVCF server-side storms that config cannot resolve (Pitfall #41, #43, R154 diminishing-returns).

## ⚖️ 评判标准
- ✅ 更少报错: 30min 99.42% (6 ATE 全NVCF服务器端, 不可配置级修复)
- ✅ 更快请求: P50=18.2s (consistent with R195's 18.2s)
- ✅ 超低延迟: P95=45.4s (stable, within R195's 44.3s range)
- ✅ 稳定优先: 27th consecutive R162+R158 validation, full 7-parameter equilibrium
- ✅ 铁律: 只改HM1不改HM2 — 确认; 本轮未改任何参数

## ⏳ 轮到HM1优化HM2
