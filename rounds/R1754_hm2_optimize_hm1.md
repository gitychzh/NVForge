# R1754 (HM2→HM1): NOP — 零可配置故障，全参数floor/optimal, 1h 100% SR

## 数据收集 (HM1, 2026-07-18 12:05 UTC)

### 6h DB (nv_requests)
| 指标 | 值 |
|------|-----|
| 总数 | 24 |
| 成功 | 22 (91.7% SR) |
| 失败 | 2 (8.3%) |
| 失败原因 | 2× zombie_empty_completion (glm5_2_nv) |
| 成功 avg_ms | 7,751ms |
| 成功 max_ms | 19,968ms |
| ATE | 0 |
| pexec timeout | 0 |
| SSLEOF | 0 |
| peer-fallback | 0 triggered |
| key_cycle_429s | 23req=1cycle, 1req=2cycle |

### 1h DB
| 指标 | 值 |
|------|-----|
| 总数 | 4 |
| 成功 | 4 (100.0% SR) |
| 失败 | 0 |

### 24h DB
| 指标 | 值 |
|------|-----|
| 总数 | 177 |
| 成功 | 145 (81.9% SR) |
| 失败 | 32 |
| zombie | 30 (glm5_2_nv) |
| ATE | 2 (dsv4p_nv: 2× 502) |
| glm5_2_nv | 144/174 OK (82.8% SR), avg=11,024ms |
| dsv4p_nv | 1/3 OK (33.3% SR), avg=25,141ms |

### 容器日志 (最近200行)
- 零 ERROR/WARN/exception
- 正常 pexec_us_rr 轮转，全部成功
- 容器 Up 2 hours (healthy)
- 0 peer-fallback triggered

### 容器 env vs compose — 零漂移 (完整验证)
所有参数容器值与compose一致:
- UPSTREAM_TIMEOUT=55 ✓
- TIER_TIMEOUT_BUDGET_S=195 ✓
- KEY_COOLDOWN_S=65 / TIER_COOLDOWN_S=65 ✓
- MIN_OUTBOUND_INTERVAL_S=0 ✓
- EMPTY_200_FASTBREAK=1 ✓
- PEXEC_TIMEOUT_FASTBREAK=1 ✓
- INTEGRATE_TIMEOUT_FASTBREAK=1 ✓
- BIG_INPUT_FAIL_N=1 / COOLDOWN=7200 ✓
- SSLEOF_RETRY_DELAY_S=0.5 ✓
- STREAM_FIRST_BYTE_DEADLINE_S=17 ✓
- STREAM_TOTAL_DEADLINE_S=25 ✓
- PEER_FALLBACK_TIMEOUT=122 ✓
- PEER_FALLBACK_ENABLED=1 ✓
- BUDGET_DSV4P_NV=60 / BUDGET_GLM5_2_NV=120 ✓
- CONNECT_RESERVE_S=0 ✓
- FORCE_STREAM_UPGRADE=0 ✓
- FORCE_STREAM_UPGRADE_TIMEOUT=66 ✓
- INTEGRATE_KEY_COOLDOWN_S=0 ✓
- FALLBACK_HEALTH_THRESHOLD=0.05 ✓

## 分析

2个失败全部是 `zombie_empty_completion` (glm5_2_nv) — NVCF function-level 劣化，所有key返回empty200。已被BIG_INPUT breaker正确覆盖 (FAIL_N=1, COOLDOWN=7200)。最近1h: 4/4 100% SR，当前窗口完全清洁。

24h数据与R1753基本一致 (R1753: 144OK/33fail/31 zombie; 本轮: 145OK/32fail/30 zombie)，1个zombie移出24h窗口，1个新OK请求进入。趋势无变化。

所有参数已处于floor/optimal状态:
- FASTBREAK各项=1 (floor)
- MIN_OUTBOUND=0 (floor)
- STREAM deadline经R1742/R1743验证：OK p99=10.8s << 17s/25s
- BUDGET_DSV4P_NV=60 匹配实际ATE=70s (floor)
- PEER_FALLBACK_TIMEOUT=122 满足约束: ≥ HM2_BUDGET_GLM5_2=120+2=122 ✓
- Budget: dsv4p ATE 70+122=192<195 (3s margin) ✓
- 1h: 100% SR, 零错误

零可配置修复故障。容器零漂移 — 全面验证13项参数全匹配。

## 决策: NOP — 不修改任何配置

这是连续第9个NOP回合 (R1746/R1747/R1748/R1749/R1750/R1751/R1752/R1753/R1754)。双重检测机制在零故障regime下持续false trigger。2个失败全部NVCF function-level zombie_empty_completion，非nv_gw可配置参数可修复。所有参数floor/optimal，零漂移。1h窗口100% SR，6h 91.7% SR。

## 评分
- 更少报错: ✓ (零ERROR/WARN，2 zombie全NVCF级)
- 更快请求: ✓ (avg 7,751ms，正常)
- 超低延迟: ✓ (max=19,968ms << 各deadline)
- 稳定优先: ✓ (零漂移，零可配置故障，1h 100% SR)

## 铁律
只改HM1不改HM2 ✓ (本轮未改任何配置)
## ⏳ 轮到HM1优化HM2
