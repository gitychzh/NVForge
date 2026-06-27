# R142: HM2 → HM1 — 无变更 (7参数均衡→稳定优先, 连续7轮验证, 30min 100%, 6h 99.6%)

## 📊 数据采集 (30min + 1h + 6h 窗口, 2026-06-28 ~02:00 UTC)

### Docker日志 (最近100行)
100% `[HM-SUCCESS]`，零错误/零警告。所有请求均在首轮尝试成功。
Round-robin正常轮转: k3→k4→k5→k1→k2→k3...

### 运行环境 (docker exec hm40006 env)
| 参数 | 当前值 | 状态 |
|------|--------|------|
| UPSTREAM_TIMEOUT | 68 | ✅ 不变 |
| TIER_TIMEOUT_BUDGET_S | 146 | ✅ 不变 |
| KEY_COOLDOWN_S | 38.0 | ✅ 不变 |
| TIER_COOLDOWN_S | 42 | ✅ 不变 |
| MIN_OUTBOUND_INTERVAL_S | 19.0 | ✅ 不变 |
| HM_CONNECT_RESERVE_S | 24 | ✅ 不变 |
| PROXY_TIMEOUT | 300 | ✅ 不变 |

### DB指标 (PostgreSQL hm_requests)

#### 30min窗口
| 指标 | 值 |
|------|-----|
| 总请求 | 80 |
| 成功 | 80 (100%) |
| 错误 | 0 |
| Fallback | 0 |
| 429 | 0 |
| All_tiers_exhausted | 0 |
| 平均延迟 | 20689ms |
| P50 | 19185ms |
| P95 | 50616ms |
| P99 | 58522ms |
| Back-to-back同key | 0/79 = 0.0% |

#### 1h窗口
| 指标 | 值 |
|------|-----|
| 总请求 | 142 |
| 成功 | 141 (99.3%) |
| 错误 | 1 (all_tiers_exhausted, 141944ms, k0/k1连续超时耗尽预算) |
| P95 | 52480ms |

#### 6h窗口
| 指标 | 值 |
|------|-----|
| 总请求 | 799 |
| 成功 | 796 (99.6%) |
| 错误 | 3 (1 all_tiers_exhausted, 1 NVStream_TimeoutError, 1 NVStream_IncompleteRead) |
| Fallback | 0 |

#### 24h all_tiers_exhausted分布
- 总计43次, 86%集中在UTC 01:00-11:00(夜间)
- 与R139模式一致, 白天近零
- 非配置可调 → NVCF服务端问题

#### 30min每key延迟 (成功请求)
| Key | n | avg_ms | p50_ms | p95_ms | 连接方式 |
|-----|---|--------|--------|--------|----------|
| k0 | 17 | 24448 | 21091 | 58439 | DIRECT |
| k1 | 16 | 17985 | 15582 | 30807 | DIRECT |
| k2 | 16 | 20258 | 17760 | 38973 | PROXY 7896 |
| k3 | 15 | 20418 | 18987 | 34543 | PROXY 7897 |
| k4 | 16 | 20085 | 19604 | 34488 | PROXY 7899 |

注: k0(DIRECT) p95=58439ms 高于PROXY keys (p54), 符合R138发现的NVCF服务端方差模式(pitfall #29), 非配置问题。

#### 慢成功请求 (≥62s)
- 仅1个请求: 65110ms, 未超过68s UPSTREAM_TIMEOUT

#### 请求速率
- 平均2.7 req/min, 容量3.2 req/min (MIN_OUTBOUND=19s → 84%利用率)

## 🎯 优化分析

### 逐参数评估

| 参数 | 当前值 | 评估 | 理由 |
|------|--------|------|------|
| UPSTREAM_TIMEOUT | 68 | ✅ 不变 | 30min仅1个≥62s请求, 远低于68s阈值; 6h仅1次NVStream_TimeoutError |
| TIER_TIMEOUT_BUDGET_S | 146 | ✅ 不变 | 2×68=136, remaining=10s满足 `<10s` 严格判断; 30min 0 次 ate |
| KEY_COOLDOWN_S | 38.0 | ✅ 不变 | 0次429, 无需调整 |
| TIER_COOLDOWN_S | 42 | ✅ 不变 | 无tier exhaustion事件触发, 间隔=42-38=4s 合理 |
| MIN_OUTBOUND_INTERVAL_S | 19.0 | ✅ 不变 | 2.7/min实际 vs 3.2/min容量=84%利用; 0 429; 0 back-to-back |
| HM_CONNECT_RESERVE_S | 24 | ✅ 不变 | 0 budget_exhausted_after_connect错误 |
| PROXY_TIMEOUT | 300 | ✅ 不变 | 无超时事件 |

### 判断: 无变更
- 连续第7轮验证: 所有7参数持续均衡
- 30min百分百, 6h 99.6% — 维持稳定平台
- 唯一的3次6h错误均为NVCF服务端问题(2次NVStream + 1次ate), 非配置可调
- 24h ate=43次, 86%夜间, 符合已知NVCF服务端不稳定窗口
- Back-to-back rate 0.0% (从R138的5.23%持续下降: R140→1.4%, R142→0.0%)

## 🔧 变更执行
**无变更** — 7参数全部维持当前值。系统处于稳定均衡状态。

## 📈 效果对比 (R140→R141→R142)

| 指标 | R140 | R141 | R142 | 趋势 |
|------|------|------|------|------|
| 30min成功率 | 100% | 100% | 100% | → |
| 6h成功率 | 99.6% | 99.6% | 99.6% | → |
| 30min 429 | 0 | 0 | 0 | → |
| 30min ate | 0 | 0 | 0 | → |
| Back-to-back | ~1% | 1.4% | 0.0% | ↑改善 |
| 30min P95 | — | ~50s | 50616ms | → |
| 24h ate | 43 | 43 | 43 | →(夜间NVCF) |

## ⚖️ 评判标准
- ✅ 更少报错: 30min 0错误, 6h仅3次(均为NVCF服务端)
- ✅ 更快请求: P50=19.2s, avg=20.7s, 维持低位
- ✅ 超低延迟: 无变化, 维持R141水平
- ✅ 稳定优先: 连续7轮均衡, 稳定平台已确立
- ✅ 铁律: 只改HM1不改HM2 — 本轮无变更

## ⏳ 轮到HM1优化HM2
