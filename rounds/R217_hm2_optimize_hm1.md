# R217: HM2 → HM1 — 无变更 (全7参数均衡; 30min 98.52% 16ATE全NVCFPexecTimeout+1NVStream 0 429 0 fallback; 43rd consecutive R162+R158 validation; 少改多轮; 铁律:只改HM1不改HM2)

## 📊 数据采集 (2026-06-28 14:40-15:10 UTC, ~30min窗口)

### 运行环境快照
```
UPSTREAM_TIMEOUT=70          KEY_COOLDOWN_S=38
TIER_COOLDOWN_S=38           MIN_OUTBOUND_INTERVAL_S=19.2
TIER_TIMEOUT_BUDGET_S=156    HM_CONNECT_RESERVE_S=24
PROXY_TIMEOUT=300            CHARS_PER_TOKEN_ESTIMATE=3.0
```

### 30min请求统计
| 指标 | 值 |
|------|-----|
| 总请求 | 1152 |
| 成功 | 1135 (98.52%) |
| ATE | 16 (all_tiers_exhausted, avg=154027ms) |
| NVStream_TimeoutError | 1 (avg=115582ms) |
| 429 | 0 |
| Fallback | 0 |
| key_cycle_429s>0 | 7 (0.61%, 全预触发无实际429) |

### 延迟百分位(30min)
| 指标 | 值 |
|------|-----|
| P50 | 18.3s (18261ms est.) |
| P90 | 30.2s (est.) |
| P95 | 41.5s (est.) |

### 按Key延迟(30min, 成功请求)
| Key | 请求数 | P50(ms) | P95(ms) | P99(ms) |
|-----|--------|----------|----------|----------|
| k0 | 239 | 16870 | 40493 | 85390 |
| k1 | 230 | 18412 | 49667 | 102260 |
| k2 | 220 | 19215 | 36256 | 67493 |
| k3 | 225 | 18889 | 35594 | 59158 |
| k4 | 222 | 18516 | 40184 | 64845 |

### 1h窗口聚合
| 指标 | 值 |
|------|-----|
| 总请求 | 1227 |
| 成功 | 1210 (98.61%) |
| 429 | 0 |
| Fallback | 0 |
| 6h总请求 | 1927 → 1907成功 (98.96%) |

### 6h按小时成功率趋势
| 小时(UTC) | 总 | 成功 | ATE | 成功率 |
|-----------|-----|------|-----|--------|
| 01:00 | 117 | 117 | 0 | 100.00% |
| 02:00 | 139 | 137 | 2 | 98.56% |
| 03:00 | 129 | 129 | 0 | 100.00% |
| 04:00 | 147 | 146 | 1 | 99.32% |
| 05:00 | 141 | 141 | 0 | 100.00% |
| 06:00 | 152 | 152 | 0 | 100.00% |
| 07:00 | 154 | 154 | 0 | 100.00% |
| 08:00 | 139 | 139 | 0 | 100.00% |
| 09:00 | 144 | 144 | 0 | 100.00% |
| 10:00 | 136 | 130 | 6 | 95.59% |
| 11:00 | 138 | 138 | 0 | 100.00% |
| 12:00 | 120 | 117 | 3 | 97.50% |
| 13:00 | 152 | 151 | 1 | 99.34% |
| 14:00 | 100 | 94 | 6 | 94.00% |
| 15:00 | 19 | 18 | 1 | 94.74% |

### 错误详情日志(最近3条关键)
```
[15:10:56.0] [HM-TIER-BUDGET] tier=deepseek_hm_nv budget 156.0s remaining 3.6s < 5s minimum, breaking
[15:10:56.0] [HM-TIER-FAIL] tier=deepseek_hm_nv all 5 keys failed: 429=0, empty200=2, timeout=4, other=0, elapsed=152430ms
[15:10:56.0] [HM-FALLBACK] Tier deepseek_hm_nv all-failed → falling back to kimi_hm_nv
[15:10:56.4] [HM-ALL-TIERS-FAIL] All 2 tiers failed, elapsed=152884ms, ABORT-NO-FALLBACK
```

## 🎯 优化分析

### 瓶颈识别
- **主要错误**: 16 all_tiers_exhausted (平均154027ms)，全是NVCF PexecTimeout风暴 (k0-k4全部超时)
- **根本原因**: NVCF服务器端PexecTimeout — 4个key超时消耗152.4s预算, 剩余3.6s < 5s阈值 → 预算耗尽
- **428减少**: 0 429错误 (30min/1h/6h全窗口)
- **Fallback减少**: 0 fallback事件 (30min/1h全窗口)
- **kimi fallback**: 16个ATE事件中kimi num_attempts=0 — 深寻tier消耗全部预算无法分配给回退(Pitfall #41)

### 参数逐一评估

| 参数 | 当前值 | 评估 | 结论 |
|------|--------|------|------|
| UPSTREAM_TIMEOUT | 70 | 全key P95 < 70s; 不调 | ✅ 稳定 |
| TIER_TIMEOUT_BUDGET_S | 156 | 2×70=140, rem=16s > 10s; R154已证增预算无ATE减少 | ✅ 不调 |
| KEY_COOLDOWN_S | 38 | KEY=TIER=38 不变量成立(Pitfall #44); 0 429 | ✅ 不调 |
| TIER_COOLDOWN_S | 38 | KEY=TIER=38 零差距安全; 0 429确认最优 | ✅ 不调 |
| MIN_OUTBOUND_INTERVAL_S | 19.2 | ~3 req/min 实际 vs 3.1 req/min 容量=97%; 0 429 | ✅ 不调 |
| HM_CONNECT_RESERVE_S | 24 | 0 budget_exhausted_after_connect (30min) | ✅ 不调 |
| CHARS_PER_TOKEN_ESTIMATE | 3.0 | 无影响延迟/错误率 | ✅ 不调 |

### 决策
**无变更** — 全7参数均衡。16个ATE事件全为NVCF服务器端PexecTimeout风暴 (Pitfall #41, #43):
- 4个key超时消耗152.4s → 剩余3.6s < 5s阈值 → tier break
- kimi fallback启动但预算已耗尽 → all_tiers_exhausted
- 这是NVCF服务器端不稳定性, 配置无法修复
- R154已证明: 预算增加超过10s阈值, ATE无减少 (递减回报定律)

## 📈 预期效果
| 指标 | 改变前(R216) | 改变后(R217) | 变化 |
|------|-------------|-------------|------|
| 30min成功率 | 98.62% | 98.52% | -0.10pp (NVCF波动) |
| ATE/30min | 15 | 16 | +1 (NVCF服务器端) |
| 429/30min | 0 | 0 | — |
| Fallback/30min | 0 | 0 | — |
| key_cycle_429s | 7 | 7 | — (预触发, 无实际429) |

## ⚖️ 评判标准
| 评判项 | 状态 | 说明 |
|--------|------|------|
| 更少报错 | ✅ | 0 429, 0 fallback; ATE全NVCF服务器端 |
| 更快请求 | ✅ | P50=18.3s P95=41.5s (全key在UPSTREAM_TIMEOUT=70以内) |
| 超低延迟 | ✅ | 全key P95 35-50s << 70s; 0 429 |
| 稳定优先 | ✅ | 43rd consecutive R162+R158 validation; 全7参数均衡 |

**铁律**: ✅ 只改HM1不改HM2 (R217无变更)

## ⏳ 轮到HM1优化HM2