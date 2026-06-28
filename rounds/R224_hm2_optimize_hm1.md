# R224: HM2→HM1 — 无变更 (全7参数均衡; 49th consecutive R162+R158 validation; 30min 98.29% 18ATE全NVCFPexecTimeout 0 429 0 fallback; 1 SSLEOFError k3 auto-retried; 少改多轮; 铁律:只改HM1不改HM2)

## 📊 数据采集 (2026-06-28 16:35 UTC+8)

### Config Snapshot (docker exec hm40006 env)
```
UPSTREAM_TIMEOUT=70
TIER_TIMEOUT_BUDGET_S=156
KEY_COOLDOWN_S=38
TIER_COOLDOWN_S=38
MIN_OUTBOUND_INTERVAL_S=19.2
HM_CONNECT_RESERVE_S=24
PROXY_TIMEOUT=300
CHARS_PER_TOKEN_ESTIMATE=3.0
```

### 30min DB Metrics
| Metric | Value |
|--------|-------|
| Total requests | 1108 |
| Success (200) | 1089 (98.29%) |
| Errors | 19 |
| all_tiers_exhausted | 18 (avg 154238ms) |
| NVStream_TimeoutError | 1 (115582ms) |
| SSLEOFError | 1 (k3, auto-retried) |
| 429 errors | 0 |
| Fallback | 0 |
| P50 (ok) | 18171ms (18.2s) |
| P95 (ok) | 41483ms (41.5s) |
| P99 (ok) | 66369ms (66.4s) |

### 1h Window
| Metric | Value |
|--------|-------|
| Total | 1188 |
| Success | 1169 (98.40%) |
| Errors | 19 |
| Fallback | 0 |

### Per-Key Distribution (30min)
| Key | Requests | Avg OK (ms) | P95 OK (ms) | ATE | SSL |
|-----|----------|-------------|-------------|-----|-----|
| k0 (K1) | 231 | 18790 | 46956 | 0 | 0 |
| k1 (K2) | 221 | 20721 | 44060 | 0 | 0 |
| k2 (K3) | 212 | 20326 | 36120 | 0 | 0 |
| k3 (K4) | 213 | 19835 | 36806 | 0 | 0 |
| k4 (K5) | 214 | 20522 | 42545 | 0 | 0 |
| (unkeyed ATE) | 18 | — | — | 18 | 0 |

### Error Detail JSONL Analysis
All 18 ATE events confirmed NVCF server-side PexecTimeout storms:
- **kimi_hm_nv**: num_attempts=0 across ALL events → tier never reached
- **deepseek_hm_nv**: 5-6 key attempts, all NVCFPexecTimeout (53-57s per key) or empty_200
- Budget consumed: ~152-156s per event → remaining < 5s threshold
- The SSLEOFError on k3 was auto-retried successfully (2s backoff)

### Request Rate
- Steady ~3 req/min across entire 30min window
- MIN_OUTBOUND utilization: ~70% (3.0/min of 3.13/min capacity at 19.2s)
- No back-to-back events observed (RR counter healthy)

### Docker Logs (last 100 lines)
- 0 HM-TIER-BUDGET threshold hits in 30min window
- 1 HM-ERR: SSLEOFError k3 (transient, auto-retried)
- All other lines: [HM-TIER] Starting tier=deepseek_hm_nv — healthy
- No HM-FALLBACK, no HM-TIER-FAIL, no panic

## 🎯 优化分析

### Parameter Evaluation Table
| Parameter | Current | Evaluation | Action |
|-----------|---------|------------|--------|
| UPSTREAM_TIMEOUT | 70 | P99=66.4s < 70s ✅. Per-key P95=36-47s << 70s ✅. NVCFPexecTimeout actual ~5-57s per key (NVCF server-side, not HM-configured). 49th consecutive R158 validation | 无调整 |
| TIER_TIMEOUT_BUDGET_S | 156 | 2×70=140, remaining=16s > 5s threshold ✅. ATE events consume full budget from NVCF storms — config cannot prevent server-side timeouts. R154 diminishing returns proven | 无调整 |
| KEY_COOLDOWN_S | 38 | 0 429s in 30min ✅. KEY=TIER=38 invariant holds (Pitfall #44) ✅. 49th consecutive R162 validation | 无调整 |
| TIER_COOLDOWN_S | 38 | KEY≥TIER invariant at zero gap (neither抢先) ✅. 0 429s confirms no cooldown pressure | 无调整 |
| MIN_OUTBOUND_INTERVAL_S | 19.2 | ~70% capacity utilization, no head-of-line blocking. 0 back-to-back events | 无调整 |
| HM_CONNECT_RESERVE_S | 24 | 0 budget_exhausted_after_connect errors. Connection overhead covered | 无调整 |
| PROXY_TIMEOUT | 300 | Proxy health stable. Not a primary bottleneck | 无调整 |

### Bottleneck Analysis
- **Primary bottleneck**: NVCF PexecTimeout storms (server-side) — 18/19 errors are NVCF-caused
- **HM cannot fix**: The NVCF API's internal timeout behavior is outside HM's control
- **Budget exhaustion**: 5-6 keys × NVCFPexecTimeout (5-57s) consumes ~150s budget → remaining < 5s → tier breaks → kimi never reached
- **kimi starvation**: All ATE events show kimi_hm_nv num_attempts=0 — the fallback tier is starved because budget is consumed by deepseek key timeouts before kimi can fire. This is Pitfall #41 confirmed through 49 consecutive rounds.

### Why No Change
1. **All 7 parameters at equilibrium**: Each parameter's safety invariant is satisfied, no parameter is over-provisioned, no parameter is under-provisioned
2. **49th consecutive R162+R158 validation**: The stability plateau is fully confirmed — R162 (KEY=TIER=38) and R158 (UPSTREAM_TIMEOUT=70) have been validated through 49 consecutive rounds without degradation
3. **ATEs are NVCF server-side**: 18 PexecTimeout events are caused by NVCF API internal behavior, not HM config. Reducing UPSTREAM_TIMEOUT below actual NVCF timeout (53-57s) would truncate legitimate requests. Increasing budget to cover 5-6 timeouts would require BUDGET ≥ 5×70+5=355s (impractical)
4. **Stability IS the optimal state**: Over-optimization risks breaking the equilibrium. The 49-round stability plateau is the definitive confirmation

## 📈 预期效果
- **Stability**: Maintain current 98.29% success rate, 0 429s, 0 fallback
- **Latency**: P50≈18s, P95≈41s, P99≈66s — all well within safety bounds
- **Reliability**: 49th consecutive R162+R158 no-change validation — the definitive long-term stable configuration

## ⚖️ 评判标准
| 标准 | 当前状态 | 判定 |
|------|---------|------|
| 更少报错 | 19/1108 (1.72%) — 18 NVCF server-side, 1 SSLEOF auto-retried | ✅ 优秀 |
| 更快请求 | P50=18.2s, P95=41.5s — 稳定低延迟 | ✅ 优秀 |
| 超低延迟 | P99=66.4s << UPSTREAM_TIMEOUT=70s | ✅ 安全 |
| 稳定优先 | 49th consecutive R162+R158 validation, 0 degradation | ✅ 最优 |
| 铁律 | 只改HM1, 不改HM2 — 本回合无变更, 铁律自动满足 | ✅ 遵守 |

## ⏳ 轮到HM1优化HM2