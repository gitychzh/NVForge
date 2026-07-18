# R1749 (HM2→HM1): NOP — false trigger, 零可配置修复故障

## 数据收集 (HM1, 2026-07-18 11:20 UTC)

### 6h DB (nv_requests)
| 指标 | 值 |
|------|-----|
| 总数 | 25 |
| 成功 | 22 (88.0% SR) |
| 失败 | 3 (12.0%) |
| 失败原因 | 3× zombie_empty_completion (glm5_2_nv) |
| 成功 avg_ms | 7,556ms |
| 成功 max_ms | 19,968ms |
| ATE | 0 |
| pexec timeout | 0 |
| SSLEOF | 0 |
| peer-fallback | 0 triggered |
| fallback occurred | 0/25 (全部直连) |
| key_cycle_429s | 24req=1cycle, 1req=2cycle |

### 24h DB
| 指标 | 值 |
|------|-----|
| 总数 | 178 |
| 成功 | 144 (80.9% SR) |
| 失败 | 34 |
| zombie | 32 |
| ATE | 2 (pre-R1745) |

### 容器日志 (最近100行)
- 零 ERROR/WARN/exception
- 1× KEY-FAULT: k4 transient → k5 恢复 (glm5_2_nv, pexec_us_rr)
- 所有请求正常 pexec_us_rr 轮转

### 容器 env vs compose
零漂移 — 所有参数容器值与compose一致:
- EMPTY_200_FASTBREAK=1 ✓
- PEXEC_TIMEOUT_FASTBREAK=1 ✓
- BIG_INPUT_FAIL_N=1 / COOLDOWN=7200 ✓
- MIN_OUTBOUND_INTERVAL_S=0 ✓
- SSLEOF_RETRY_DELAY_S=0.5 ✓
- STREAM_FIRST_BYTE_DEADLINE_S=17 ✓
- STREAM_TOTAL_DEADLINE_S=25 ✓
- KEY_COOLDOWN_S=65 / TIER_COOLDOWN_S=65 ✓
- PEER_FALLBACK_TIMEOUT=122 ✓
- BUDGET_DSV4P_NV=60 / BUDGET_GLM5_2_NV=120 ✓
- TIER_TIMEOUT_BUDGET_S=195 ✓

## 分析

3个失败全部是 `zombie_empty_completion` — NVCF function-level劣化，所有5个key返回empty200。这属于NVCF服务端问题，非nv_gw可配置参数可修复。R1745的BIG_INPUT_COOLDOWN_S 5400→7200已正确覆盖这些zombie (>250K chars glm5_2)的快速失败路径。

所有参数已处于floor/optimal状态:
- FASTBREAK各项=1 (floor)
- MIN_OUTBOUND=0 (floor)
- STREAM deadline经R1742/R1743验证：OK p99=10.8s << 17s/25s
- BUDGET_DSV4P_NV=60 匹配实际ATE=70s (floor)
- PEER_FALLBACK_TIMEOUT=122 满足约束: ≥ HM2_BUDGET=70+2 ✓

零可配置修复故障。NOP。

## 决策: NOP — 不修改任何配置

这是连续第4个NOP回合 (R1746/R1747/R1748/R1749)。双重检测机制 (HM1写commit→HM2检测，HM2写commit→HM1检测) 在零故障regime下持续false trigger，但NOP回合本身无害 — 验证了系统健康状态。

## 评分
- 更少报错: ✓ (零ERROR/WARN，3 zombie全NVCF级)
- 更快请求: ✓ (avg 7,556ms, 正常)
- 超低延迟: ✓ (p99=10.8s, 远低于各deadline)
- 稳定优先: ✓ (零漂移，零可配置故障)

## 铁律
只改HM1不改HM2 ✓ (本轮未改任何配置)
## ⏳ 轮到HM1优化HM2
