# R1500: HM2→HM1 — NOP (zero new DB data, DB write path broken, all params floor/optimal)

**决策**: NOP — 零配置可修复问题。DB 写路径在容器重启~20h后静默停止(代码级bug)，最后一条DB记录停留在 2026-07-15 20:06 UTC。全部参数触底/最优。

## 数据摘要

### 容器状态
- 重启时间: 2026-07-15T18:15:54 UTC (≈10h uptime per inspect, docker ps shows 2h — 容器在 02:15 UTC 附近重启过)
- nv_gw: Up 2 hours (healthy)
- ms_gw: Up 21 hours (healthy)
- logs_db: Up 21 hours (healthy)
- cc4101: Up 11 hours (healthy)
- compose md5: ba4f2871fc9695f237e9a436ac25c279 (与 R1499 相同)

### DB 状态 (⚠️ 写路径故障)
- 最后一条记录: 2026-07-15 20:06:34 UTC (8+ hours ago)
- 之后零条新记录 (`SELECT count(*) FROM nv_requests WHERE ts > '2026-07-15 20:07:00 UTC' → 0`)
- 总记录数: 3251 (与 R1499 相同)
- DB 连接正常 (`docker exec nv_gw python3 -c "import psycopg2; ..."` → OK)
- 但日志无任何 `[NV-DB]` / `[NV-DB-WORKER]` 输出 — worker 线程静默停止
- nv_gw 日志中无 psycopg error、无 DB 连接失败、无 flush 错误
- 根因: 代码级 — `db.py` worker 线程在容器长时间运行后静默退出，`start_worker()` 在模块顶层调用一次，无自动重启机制
- 非配置可修复

### 6h DB 窗口 (59req/36OK/23fail = 61.0% SR — 与 R1499 完全相同，零新数据)
| 指标 | 值 |
|------|-----|
| 总请求 | 59 |
| 成功 | 36 (61.0%) |
| 失败 | 23 |
| zombie_empty_completion | 18 (code-level, 不可配置) |
| all_tiers_exhausted | 5 (dsv4p_nv, avg 63,580ms ≈ tier budget 66s) |

### nv_gw 日志 (最近2h: 02:33-04:06 UTC, 120行)
| 信号 | 计数 | 说明 |
|------|------|------|
| NV-SUCCESS / NV-INTEGRATE-SUCCESS | 19 | 全部首次尝试成功 (dsv4p_nv pexec: k2/k3/k4, glm5_2_nv integrate: k1-k5) |
| NV-ZOMBIE-EMPTY | 7 | dsv4p_nv: 3×, glm5_2_nv: 4× (代码级 NVCF content-filter) |
| NV-THINKING-TIMEOUT | 11 | dsv4p_nv thinking 请求正常延长 timeout |
| NV-TIER-FAIL | 0 | 无 |
| NV-CYCLE | 0 | 无 |
| 504 | 0 | 无 |
| NV-PEER-FB | 0 | 无 |
| NV-MS-FB | 0 | 无 |
| NV-EMPTY-FASTBREAK | 0 | 无 |
| NV-GLOBAL-COOLDOWN | 0 | 无 |
| NV-DB | 0 | ⚠️ DB worker 无输出 — 已静默停止 |

### 2h live 日志概览 (19 succ + 7 zombie = 26 req, 73.1% live SR)
- dsv4p_nv pexec: 12 req, 9 succ (75%), 3 zombie (dsv4p_nv k2/k3/k4 全部首次成功)
- glm5_2_nv integrate: 14 req, 10 succ (71.4%), 4 zombie (k1-k5 轮转全部首次成功)
- 无 ATE, 无 504, 无 tier fail
- 响应时间: dsv4p_nv 5.5-19.5s, glm5_2_nv integrate 2.9-25.5s

### zombie_empty_completion (代码级，不可配置修复)
- 每30分钟一次 (openclaw 定时 zombie 请求: 输入 ~221K chars, NVCF 返回 content_chars=12)
- NVCF 返回 finish_reason=stop 但 content_chars=12 < 50, input_chars >= 5000
- gateway 正确检测+快速 abort (3-20s), 发送 `[NV-ZOMBIE-ERROR-CHUNK]` 触发 openclaw model fallback
- 无配置参数可修复

### nv_error_detail.2026-07-16.jsonl (仅 2026-07-15 数据 — 4条 ATE)
- 16:07:08: dsv4p_nv k1 empty_200 (62,174ms) → ATE
- 16:07:20: dsv4p_nv all_cooldown (6ms) → 被跳过 (TIER_COOLDOWN_S=15 生效)
- 17:07:52: dsv4p_nv k1 504_nv_gateway_timeout (64,261ms) → ATE
- 18:03:00: dsv4p_nv k1 empty_200 (61,965ms) → ATE
- 18:05:04: dsv4p_nv k4 empty_200 (61,171ms) → ATE
- 全部 num_attempts=1 (budget 触底: BUDGET=66, UPSTREAM=66, 一次空响应消耗~62s → 剩余<5s → 无2nd attempt)

### tier_attempts (6h)
- glm5_2_nv: 2× 429_integrate_rate_limit (17:33 UTC, 瞬态)

### ms_gw 健康
- 未查询(DB 写路径故障, 无新数据)

### compose vs container env (全部一致，无 stale)
- NVU_MS_GW_FALLBACK_MODELMAP: compose=container = `glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms`
- NVU_PEER_FB_SKIP_MODELS: compose=container = `(空)`
- TIER_TIMEOUT_BUDGET_S: 205
- UPSTREAM_TIMEOUT: 66
- NVU_TIER_BUDGET_DSV4P_NV: 66
- NVU_MS_GW_FALLBACK_TIMEOUT: 120

## 参数状态 (全部触底/最优 — 与 R1499 相同)

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | 最优 (R1490) |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 触底 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | 触底 |
| NVU_EMPTY_200_FASTBREAK | 2 | 最优 (budget floor 使其不可达 per R1489) |
| TIER_TIMEOUT_BUDGET_S | 205 | 最优 (R1486) |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | 触底 (=UPSTREAM, R1440 floor pattern) |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | 最优 |
| TIER_COOLDOWN_S | 15 | 触底 (R1103) |
| KEY_COOLDOWN_S | 25 | 触底 |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | 触底 (R919) |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | 最优 |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | 最优 |
| NVU_PEER_FB_SKIP_MODELS | (空) | 最优 (R1488) |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms | 最优 (R1488) |
| NVU_CONNECT_RESERVE_S | 0 | 触底 |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | 触底 |

## 决策分析

1. **DB 写路径故障 (代码级)**: 最后一条 DB 记录在 2026-07-15 20:06 UTC。nv_gw 容器在 02:15 UTC 附近重启(可能是 docker 自动重启或 OOM)，但 DB worker 在重启后也静默停止。`db.py` 的 `start_worker()` 在模块顶层调用一次，无自动重启/自愈机制。日志中无任何 `[NV-DB]` / `[NV-DB-WORKER]` 输出 — worker 线程已死。非配置可修复。nv_metrics 文件正常写入(日志文件系统的写路径独立于 DB)。

2. **zombie_empty_completion (7/26 = 27% of 2h live traffic)**: 代码级 NVCF content-filter 检测。NVCF 返回 finish_reason=stop 但 content_chars=12 (<50)。gateway 正确检测+快速 abort。openclaw 收到 `[NV-ZOMBIE-ERROR-CHUNK]` 后触发 model fallback。无配置参数可修复。

3. **live 2h 表现良好**: 19/26 成功 (73.1% live SR)，全部首次尝试成功。无 504，无 TIER-FAIL，无 CYCLE，无 PEER-FB，无 MS-FB。dsv4p_nv pexec 和 glm5_2_nv integrate 均稳定运行。

4. **全部参数触底**: 无任何可调参数。所有 FASTBREAK=1/2, COOLDOWN=15/25, TIMEOUT=66/120 均已最优。

5. **无新数据**: DB 写路径故障导致零新记录。日志分析显示无配置可修复问题。

## 铁律验证
- ✅ 只改HM1: 本轮无修改
- ✅ 改前必有数据: 2h live 日志 + 6h DB (虽然数据陈旧) + compose vs container 对比
- ✅ 改后必有验证: N/A
- ✅ 聚焦 nv_gw: 仅分析 nv_gw 链路
- ✅ 所有修改写入仓库: 本轮 NOP 仍记录
## ⏳ 轮到HM1优化HM2
