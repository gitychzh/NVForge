# R229: HM2 → HM1 — 无变更 (全7参数均衡; 54th no-change verification; 30min 98.0% 21ATE全NVCFPexecTimeout+1NVStream_TimeoutError 0 429 0 fallback; 少改多轮; 铁律:只改HM1不改HM2)

## 📊 数据采集 (30min 17:02-17:32 UTC, 2026-06-28)

### Config Snapshot (docker exec hm40006 env)
| Parameter | Value | Status |
|----------|-------|--------|
| UPSTREAM_TIMEOUT | 70 | R158 72→70, 54th consecutive validation |
| TIER_TIMEOUT_BUDGET_S | 156 | R152 154→156, budget margin 11s > 5s minimum |
| KEY_COOLDOWN_S | 38 | R162 34→38, KEY=TIER invariant |
| TIER_COOLDOWN_S | 38 | R156 42→38, KEY=TIER=38 zero gap |
| MIN_OUTBOUND_INTERVAL_S | 19.2 | R208 19.0→19.2, RR counter healthy |
| HM_CONNECT_RESERVE_S | 24 | R111 22→24, SSL/SOCKS5 overhead covered |
| CHARS_PER_TOKEN_ESTIMATE | 3.0 | Standard estimate |

### 30min Aggregate
| Metric | Value | Note |
|--------|-------|------|
| Total requests | 1087 | — |
| Success (200) | 1065 (98.0%) | Down from R228's 98.18% (-0.18pp) |
| ATE (all_tiers_exhausted) | 21 | Up 1 from R228's 20, NVCF storm fluctuation |
| 429 errors | 0 | Confirmed optimal KEY_COOLDOWN |
| Fallback | 0 | Confirmed tier chain healthy |

### Latency Percentiles (success only, 30min)
| Percentile | Value | Trend vs R228 |
|-----------|-------|---------------|
| P50 | 18.2s (18211ms) | Stable |
| P95 | 45.8s (45828ms) | +2.6s |
| P99 | 85.9s (85867ms) | +5.3s |

### Per-Key Latency (30min, success only)
| Key | Reqs | P50 | P95 |
|-----|------|-----|-----|
| k0 (DIRECT) | 228 | 16.9s | 52.7s |
| k1 (DIRECT) | 215 | 18.5s | 44.9s |
| k2 (PROXY) | 202 | 19.6s | 38.4s |
| k3 (PROXY) | 212 | 18.5s | 43.6s |
| k4 (PROXY) | 208 | 18.5s | 43.2s |

Even distribution (202-228 req/key).

### 24h Segmented
| Window | Total | OK | ATE | 429 | Fallback |
|--------|-------|-----|-----|-----|----------|
| 0-6h | 1881 | 1858 | 21 | 0 | 0 |
| 6-12h | 816 | 811 | 3 | 0 | 0 |
| 12-24h | 1729 | 1685 | 41 | 4 | 249 (old-regime) |

### Error Detail JSONL (latest 17:02)
```
deepseek_hm_nv: 6 attempts, elapsed=154994ms (per-key ~25.8s = NVCF pexec timeout)
kimi_hm_nv: 0 attempts (never reached)
Budget: 1s remaining < 5s → break
```

## 🎯 优化分析

All 7 parameters at equilibrium. ATE=21 is NVCF PexecTimeout server-side storms:
- 5-7 key attempts all timing out at ~25.8s (NVCF's internal timeout)
- Budget consumed: 154-156s → remaining 1s < 5s → tier breaks
- kimi_hm_nv num_attempts=0 — never gets a chance (Pitfall #41)

**Full parameter evaluation** (every parameter checked):
| Parameter | Current | Change? | Reason |
|-----------|---------|---------|--------|
| UPSTREAM_TIMEOUT | 70 | ❌ No | P95<70s; NVCF pexec timeout is server-side at ~25.8s |
| TIER_TIMEOUT_BUDGET_S | 156 | ❌ No | Margin 11s; R154 proved diminishing returns beyond 10s |
| KEY_COOLDOWN_S | 38 | ❌ No | 0 429s; KEY=TIER invariant |
| TIER_COOLDOWN_S | 38 | ❌ No | 0 fallback in 0-12h; KEY≥TIER |
| MIN_OUTBOUND_INTERVAL_S | 19.2 | ❌ No | RR counter healthy; 3.41% back-to-back acceptable |
| HM_CONNECT_RESERVE_S | 24 | ❌ No | No budget_exhausted_after_connect errors |
| CHARS_PER_TOKEN_ESTIMATE | 3.0 | ❌ No | Standard |

## 🔧 变更执行

**无变更** — No parameters adjusted. HM1 docker-compose.yml unchanged.

## 📈 历史趋势 (R222-R229)

| Round | Success% | ATE | P50 | P95 |
|-------|----------|-----|-----|-----|
| R222 | 98.40% | 19 | 18.3s | 42.0s |
| R223 | 98.26% | 20 | 18.2s | 42.8s |
| R224 | 98.34% | 19 | 18.3s | 43.5s |
| R225 | 98.32% | 18 | 18.2s | 41.4s |
| R226 | 98.29% | 18 | 18.2s | 42.1s |
| R227 | 98.30% | 18 | 18.2s | 42.1s |
| R228 | 98.18% | 20 | 18.2s | 43.2s |
| R229 | 98.0% | 21 | 18.2s | 45.8s |

Stability plateau: ±0.4pp fluctuation, P50=18.2s floor.

## ⚖️ 评判标准

| Criterion | Status |
|----------|--------|
| 更少报错 | ✅ 0 429, 0 fallback in 0-12h |
| 更快请求 | ✅ P50=18.2s stable |
| 超低延迟 | ✅ All P50 16.9-19.6s |
| 稳定优先 | ✅ 54th consecutive validation |
| 铁律:只改HM1不改HM2 | ✅ Confirmed |

## ⏳ 轮到HM1优化HM2