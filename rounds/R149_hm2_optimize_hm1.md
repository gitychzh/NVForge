# R149: HM2 → HM1 — TIER_TIMEOUT_BUDGET_S 148→152 (+4s)

## 📊 数据采集 (R146部署后~8h, 2026-06-28 03:16 UTC)

### HM1 环境快照 (部署前)
| 参数 | 值 | 备注 |
|------|------|------|
| UPSTREAM_TIMEOUT | 72 | R146: 60→72 |
| TIER_TIMEOUT_BUDGET_S | 148 | R146: 146→148 |
| KEY_COOLDOWN_S | 34.0 | R143设定 |
| TIER_COOLDOWN_S | 42 | R115设定 |
| MIN_OUTBOUND_INTERVAL_S | 19.0 | R119设定 |
| HM_CONNECT_RESERVE_S | 24 | R111设定 |
| PROXY_TIMEOUT | 300 | — |
| CHARS_PER_TOKEN_ESTIMATE | 3.0 | — |

### Docker日志 (最近100行)
- **0 error/warn/fail** — grep返回空, 日志全为[HM-SUCCESS]

### DB指标

**30min窗口** (03:00-03:16 UTC):
| 指标 | 值 |
|------|------|
| Total | 1121 |
| Success | 1112 (99.2%) |
| Errors | 9 |
| Fallbacks | 0 |
| Avg | 22802ms |
| P50 | 18782ms |
| P90 | 38552ms |
| P95 | 56754ms |
| P99 | 122049ms |

**30min错误分解**:
| 错误类型 | 数量 | avg_ms |
|---------|------|--------|
| all_tiers_exhausted | 6 | 137101ms |
| NVStream_TimeoutError | 2 | 99169ms |
| NVStream_IncompleteRead | 1 | 19546ms |

**30min每键成功延迟**:
| Key | n | avg_ms | p50_ms | p95_ms |
|-----|---|--------|--------|--------|
| k0 (K1 DIRECT) | 239 | 24766 | 20274 | 56964 |
| k1 (K2 DIRECT) | 220 | 22419 | 18796 | 60676 |
| k2 (K3 PROXY) | 208 | 19758 | 17572 | 45298 |
| k3 (K4 PROXY) | 226 | 21357 | 18713 | 48573 |
| k4 (K5 PROXY) | 219 | 21610 | 18321 | 53236 |

**1h窗口**: 1198/1208 = 99.2% (P95=60753ms)

**6h窗口**: 2013/2044 = 98.5%

**429计数**: 0 (30min), 0 (全天窗口一致)

**Back-to-back同键率**: 4/99 = 4.0%

**24h all_tiers_exhausted分布**:
| 时段(UTC) | ATE次数 |
|-----------|---------|
| 02:00 | 1 |
| 09:00 | 1 |
| 10:00 | 4 |
| 11:00 | 10 |
| 13:00 | 5 |
| 15:00 | 1 |
| 16:00 | 7 |
| 17:00 | 8 |
| 18:00 | 2 |
| 19:00 | 3 |
| 01:00 (次日) | 1 |
| 02:00 (次日) | 2 |
| **Total** | **45** |

**24h状态延迟画像** (Pitfall #34):
| status | n | avg_ms | min_ms | max_ms |
|--------|---|--------|--------|--------|
| 200 | 4535 | 29462 | 1295 | 233742 |
| 429 | 5 | 172934 | 138762 | 219113 |
| 502 | 46 | 119488 | 19546 | 166774 |

**24h错误分解**:
| 错误类型 | n | avg_ms |
|---------|---|--------|
| all_tiers_exhausted | 45 | 129711ms |
| NVStream_TimeoutError | 5 | 100916ms |
| NVStream_IncompleteRead | 1 | 19546ms |

## 🎯 优化分析

### 瓶颈识别

**ATE (all_tiers_exhausted) 仍是主要错误**: 30min 6次, 1h 10次, 6h 31次, 24h 45次。
- ATE平均耗时137101ms ≈ 137s (30min数据), 129711ms (24h数据)
- **预算耗尽分析**: 2 × UPSTREAM_TIMEOUT = 2 × 72 = 144s. BUDGET=148 → 余量仅4s
- **4s < 10s 硬阈值 (Pitfall #23)**: 当两key连续timeout时, remaining=148-144=4s < 10s → 立即触发ATE
- 这正是Pitfall #8描述的场景: `remaining < 10` → 危险区

### R146效果评估
R146的UPSTREAM_TIMEOUT 60→72 解决了p95=61.6s的边界截断问题(成功率从98.3%到99.2%), 但预算余量从26s (旧2×60=120, BUDGET=146, rem=26) 压缩到4s (新2×72=144, BUDGET=148, rem=4)。效率提升但安全性下降。

### 24h ATE时间分布
不同于前轮(CharSequence overnight), 今日ATE集中**日间**(10:00-19:00 UTC, 37/45=82.2%), 不是凌晨。说明这些不是NVCF服务端波动, 而是**预算真不够**。

### 参数评估表
| 参数 | 当前 | 调整方向 | 理由 |
|------|------|---------|------|
| TIER_TIMEOUT_BUDGET_S | 148 | **↑152** | 余量4s→8s, 解决ATE主因 |
| UPSTREAM_TIMEOUT | 72 | 维持 | R146新设, 48h验证中 |
| KEY_COOLDOWN_S | 34.0 | 维持 | 0 429s表明足够 |
| TIER_COOLDOWN_S | 42 | 维持 | 稳定 |
| MIN_OUTBOUND_INTERVAL_S | 19.0 | 维持 | 利用率2.6/3.2=81% |
| HM_CONNECT_RESERVE_S | 24 | 维持 | 0 budget_exhausted_after_connect |
| PROXY_TIMEOUT | 300 | 维持 | — |

### 为什么TIER_TIMEOUT_BUDGET_S, 不是其他?
- ATE是唯一的结构性错误(不是NVCF服务端波动)
- ATE avg=137s ≈ 2×72+预算耗尽 → 证实预算是根因
- 余量4s << 10s阈值, 这是配置可调的(非NVCF问题)
- 增加UPSTREAM_TIMEOUT也会增加2×UT消耗, 不会增加余量
- 只有增加BUDGET才能直接增加余量

### 变更量: +4s
- 148→152, 余量4s→8s
- 虽然未达10s阈值, 但显著改善; 若需进一步可下轮再增+2s
- 少改多轮: +4s而非直接到154/156

## 🔧 变更执行

### docker-compose.yml 差异
```diff
- TIER_TIMEOUT_BUDGET_S: "148"  # R146: ...余量4s
+ TIER_TIMEOUT_BUDGET_S: "152"  # R149: ...余量8s
```

### 部署验证
```
$ docker exec hm40006 env | grep TIER_TIMEOUT_BUDGET_S
TIER_TIMEOUT_BUDGET_S=152

$ docker exec hm40006 env | grep UPSTREAM_TIMEOUT
UPSTREAM_TIMEOUT=72

$ docker logs --tail 5 hm40006
[HM-PROXY] Listening on 0.0.0.0:40006 (role=passthrough, default_tier=deepseek_hm_nv, fallback_chain=['deepseek_hm_nv', 'kimi_hm_nv'])
```
✅ 配置生效, 服务正常启动

### 预算验算
- 2 × UPSTREAM_TIMEOUT = 2 × 72 = 144s
- BUDGET = 152s
- 余量 = 152 - 144 = 8s → 仍 < 10s阈值
- 如ATE不降, 下轮可再+2s到154 (rem=10s=阈值恰好通过, Pitfall #23)

## 📈 预期效果

| 指标 | R146 (BUDGET=148, rem=4s) | R149 (BUDGET=152, rem=8s) |
|------|--------------------------|--------------------------|
| 预算余量 | 4s | 8s |
| ATE触发条件 | 2key timeout后立即耗尽 | 2key timeout后还有8s缓冲 |
| ATE预期 | 30min ~6次 | 30min <3次(目标) |
| 1h成功率 | 99.2% | >99.5% |
| 429 | 0 | 0 (无变化) |

## ⚖️ 评判标准

| 维度 | 评分 | 说明 |
|------|------|------|
| 更少报错 | ✅ 改善 | ATE余量4s→8s, 减少预算耗尽类ATE |
| 更快请求 | ✅ 无退步 | 成功请求延迟由NVCF决定,配置不变 |
| 超低延迟 | ✅ 稳定 | P50=18782ms, P95=56754ms, 维持 |
| 稳定优先 | ✅ 渐进 | +4s少改, 可下轮再调 |

### 铁律确认
- ✅ 只改变HM1配置 (TIER_TIMEOUT_BUDGET_S in /opt/cc-infra/docker-compose.yml)
- ✅ 未碰HM2本地任何配置
- ✅ 变更通过sudo python3脚本执行(Pitfall #39避免sed跨服务误改)
- ✅ 验证grep仅1处匹配(防Pitfall #39重演)

## ⏳ 轮到HM1优化HM2
