# R345: HM2→HM1 — ⏸️ 无操作: 零流量 · 全参数均衡 · 无变更窗口 · 铁律:只改HM1不改HM2

## 📊 数据采集 (11:10 UTC, 2026-06-30)

### 配置快照 (docker exec hm40006 env)
| 参数 | 当前值 | 说明 |
|------|--------|------|
| UPSTREAM_TIMEOUT | 45 | Per-key NVCF timeout |
| TIER_TIMEOUT_BUDGET_S | 100 | 总 tier 预算 |
| KEY_COOLDOWN_S | 38 | Key 429 冷却 |
| TIER_COOLDOWN_S | 38 | Tier 冷却 (KEY=TIER=38 不变量维持) |
| MIN_OUTBOUND_INTERVAL_S | 6.0 | 出站最小间隔 |
| HM_CONNECT_RESERVE_S | 10 | 连接预留 |
| HM_SSLEOF_RETRY_DELAY_S | 3.0 | SSL 错误重试延迟 |

### 核心发现: 零流量 — 容器重启后无请求
- 容器于 09:32 UTC 重启, 截至 11:10 UTC (~1h38min): **零请求到达**
- DB 最后记录: 2026-06-30 07:43 UTC (重启前)
- 容器健康 (Up 2 hours, health=200 OK) 但空闲
- 非 HM1 参数问题 — 上游未发送新请求

### 错误详情 (今日)
| 时间 | 错误类型 | 持续时间 | 详情 |
|------|---------|---------|------|
| 00:09:58 | all_tiers_exhausted | 88,019ms | 3次 NVCFPexecTimeout |
| 00:27:14 | all_tiers_exhausted | 85,805ms | 6次: 5×NVCFPexecTimeout + budget_exhausted_after_connect |
| 04:03:15 | BadRequest | 0ms | request_model=? 空请求 |

### 指标验证
- 所有成功请求: first attempt 成功, 无 fallback
- Per-key 延迟均匀: k0-k4 avg 20.5-24.0s, P50 18.9-20.7s
- 仅 1 次 key_cycle_429s_before_success (retry 成功)

## 🔧 变更执行
**无变更** — 全参数均衡, 零流量无优化数据. 7 参数皆最优. 本回合 ⏸️ 无操作.

## ⏳ 轮到HM1优化HM2 ← 脚本检测此标记