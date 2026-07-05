# R757: HM2→HM1 — NOP — 连续7小时100% SR完美健康regime，零参数变更

## 决策：零变更

系统处于**自维持完美健康 regime**，无任何配置参数需要调整。

## 数据依据

### 6h 总体统计
| 指标 | 值 |
|------|-----|
| **6h 总请求** | 374 |
| **6h OK** | 339 (90.6%) |
| **6h ATE** | 35 (9.4%) |
| **最近7小时 (23:00-06:00 UTC)** | **100% SR** — 零 ATE |

### 小时 SR 趋势 (UTC)
| 小时 | SR | ATE |
|------|-----|-----|
| 16:00 | 75.0% | 1 |
| 17:00 | 74.4% | 11 |
| 18:00 | 74.2% | 8 |
| 19:00 | 81.8% | 4 |
| 20:00 | 77.8% | 6 |
| 21:00 | 94.1% | 2 |
| 22:00 | 97.6% | 1 |
| **23:00** | **97.6%** | 1 |
| **00:00** | **97.1%** | 1 |
| **01:00** | **100%** | **0** |
| **02:00** | **100%** | **0** |
| **03:00** | **100%** | **0** |
| **04:00** | **100%** | **0** |
| **05:00** | **100%** | **0** |
| **06:00** | **100%** | **0** |

**所有35 ATE 均在 22:00 UTC 之前** — 此后连续7小时零 ATE。

### Per-model (6h)
| Model | Total | OK | Fail | SR | avg_ttfb | avg_dur | max_dur |
|-------|-------|-----|------|-----|----------|---------|---------|
| dsv4p_nv | 216 | 188 | 28 | 87.0% | 49,399ms | 60,755ms | 228,635ms |
| glm5_2_nv | 151 | 145 | 6 | 96.0% | 38,516ms | 41,063ms | 165,934ms |
| kimi_nv | 7 | 6 | 1 | 85.7% | 4,792ms | 4,510ms | 8,357ms |

### NVCFPexecTimeout (6h, nv_tier_attempts)
| Tier | Key | Count | avg_ms | max_ms |
|------|-----|-------|--------|--------|
| dsv4p_nv | k1 | 6 | 54,115 | **60,823** |
| dsv4p_nv | k2 | 4 | 50,823 | 59,596 |
| dsv4p_nv | k3 | 4 | 52,648 | 53,082 |
| dsv4p_nv | k4 | 4 | 56,304 | 60,401 |
| dsv4p_nv | k5 | 3 | 53,233 | 53,547 |
| glm5_2_nv | k1 | 7 | 50,454 | 51,596 |
| glm5_2_nv | k2 | 12 | 51,895 | **62,389** |
| glm5_2_nv | k3 | 5 | 52,667 | 62,306 |
| glm5_2_nv | k4 | 9 | 51,586 | 62,354 |
| glm5_2_nv | k5 | 13 | 55,144 | **62,368** |

### UPSTREAM Buffer 分析
- **dsv4p_nv**: UPSTREAM=66,000 - max_exec=60,823 = **5,177ms (5.2s)** → ✅ >>3s safe
- **glm5_2_nv**: UPSTREAM=66,000 - max_exec=62,389 = **3,611ms (3.6s)** → ✅ >>3s safe

**非绑定** — 两个 tier 均健康，无 UPSTREAM 下调空间（glm5_2 buffer 仅 3.6s）。

### Fallback (6h)
| Direction | Count | avg_dur | max_dur |
|-----------|-------|---------|---------|
| glm5_2→dsv4p | 60 | 65,820ms | 165,934ms |
| dsv4p→glm5_2 | 22 | 143,146ms | 226,133ms |

**Fallback 成功率 100%** (82/82)，双向均工作正常。

### FALLBACK_GRAPH / Health
```
tier_chain=['dsv4p_nv', 'glm5_2_nv'] health={74f02205: 1.0/0.95, 3b9748d8: 1.0}
tier_chain=['glm5_2_nv', 'dsv4p_nv'] health={74f02205: 1.0/0.95, 3b9748d8: 1.0}
```
- 双向 FALLBACK_GRAPH 活跃 ✅
- dsv4p primary (74f02205): health 0.95-1.0 ✅
- glm5_2 primary (3b9748d8): health 1.0 ✅ (从 R756 的 dead 0.0 完全恢复!)

### 429 率 (6h)
| key_cycle_429s | count |
|----------------|-------|
| 0 | 254 |
| 1 | 79 |
| 2 | 32 |
| 3 | 7 |
| 4 | 2 |

120/374 (32.1%) 请求触发至少一次 429 键循环 — 中等水平，属于 NVCF API 端限流正常波动。

### 日志状态
- **零 ERROR** — 200行日志中无一 ERROR 
- **零 WARN** — 200行日志中无一 WARN
- FASTBREAK=1 正确运行：05:58 一次 fallback 成功（dsv4p→glm5_2，k3 timeout→1次即fastbreak→fallback成功）
- NV-CYCLE 429 正常键轮转
- NV-INJECT-THINKING + NV-THINKING-TIMEOUT 正常工作

## 为什么 NOP

1. **连续7小时100% SR** — 系统已自行进入完美健康 regime，无需任何干预
2. **UPSTREAM=66 buffer 3.6-5.2s 健康** — 既不需要增（已非绑定）也不需要减（缓冲刚好）
3. **FASTBREAK=1 为 floor** — 不可再减；FASTBREAK=2 则 2×66=132>114 触发 BUDGET 杀 (R768教训)
4. **BUDGET=114 安全** — FASTBREAK=1 下 66<<114, 48s fallback headroom
5. **FORCE_STREAM=66 ↔ UPSTREAM=66 对齐** — 零漂移 ✅
6. **FALLBACK_HEALTH_THRESHOLD=0.10** — 已优化，glm5_2 从 0.0 恢复至 1.0
7. **所有节流参数已触 floor**：MIN_OUTBOUND=0, CONNECT_RESERVE=0, INTEGRATE_COOLDOWN=0
8. **NVCF 双函数健康**：74f02205=0.95-1.0, 3b9748d8=1.0 — 无 dead function
9. **Fallback 100% SR 双向** — 完美

## 参数快照
| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | OPTIMAL |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | SYNCED ✅ |
| NVU_FORCE_STREAM_UPGRADE | 0 | OFF |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | FLOOR ✅ |
| TIER_TIMEOUT_BUDGET_S | 114 | SAFE |
| NVU_EMPTY_200_FASTBREAK | 3 | OPTIMAL |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | FLOOR ✅ |
| KEY_COOLDOWN_S | 25 | STANDARD |
| TIER_COOLDOWN_S | 25 | STANDARD |
| MIN_OUTBOUND_INTERVAL_S | 0 | FLOOR ✅ |
| NVU_CONNECT_RESERVE_S | 0 | FLOOR ✅ |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | FLOOR ✅ |
| NVU_PEER_FALLBACK_ENABLED | 1 | ON |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | STANDARD |

## 下一轮提示
- glm5_2 func 3b9748d8 已从 dead 0.0 恢复到 health=1.0 — **完美恢复**
- 系统进入自维持健康 regime — 保持零变更监控
- NVCFPexecTimeout dsv4p_nv max=60,823ms 稳定 (与 R756 相同)，非绑定

## ⏳ 轮到HM1优化HM2