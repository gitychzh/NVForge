# R1499: HM2→HM1 — NOP (zero new data, zombie-dominated, all params floor/optimal)

**决策**: NOP — 零配置可修复问题。全部失败为 zombie_empty_completion (代码级 NVCF content-filter)，全部参数触底/最优。

## 数据摘要

### 容器状态
- 重启时间: 2026-07-15T18:15:54 UTC (≈10h uptime)
- nv_gw: Up 10 hours (healthy)
- ms_gw: Up (healthy)
- logs_db: Up (healthy)
- compose md5: ba4f2871fc9695f237e9a436ac25c279 (与 R1498 相同)

### 6h 窗口 (59req/36OK/23fail = 61.0% SR)
| 指标 | 值 |
|------|-----|
| 总请求 | 59 |
| 成功 | 36 (61.0%) |
| 失败 | 23 |
| zombie_empty_completion | 18 (code-level, 不可配置) |
| all_tiers_exhausted | 5 (dsv4p_nv, avg 63,580ms ≈ tier budget 66s) |

### 按模型
| 模型 | 请求 | OK | 失败 | SR | avg_dur_ms |
|------|------|-----|------|-----|-----------|
| dsv4p_nv | 35 | 24 | 11 | 68.6% | 27,913 |
| glm5_2_nv | 24 | 12 | 12 | 50.0% | 13,545 |

### 按 upstream
| upstream | 请求 | OK | 失败 | avg_dur_ms |
|----------|------|-----|------|-----------|
| nvcf_pexec | 27 | 21 | 6 | 22,550 |
| nv_integrate | 24 | 12 | 12 | 13,545 |
| (空) | 8 | 3 | 5 | 46,012 |

### zombie_empty_completion (代码级，不可配置修复)
- dsv4p_nv: 6× (avg 19,624ms, avg input 221,227 chars)
- glm5_2_nv: 12× (avg 12,274ms, avg input 220,579 chars)
- 日志: `[NV-ZOMBIE-EMPTY] finish_reason=stop but content_chars=12 < 50, input_chars=221523 >= 5000`
- 伴随 `[NV-ZOMBIE-ERROR-CHUNK]` → 触发 openclaw model fallback
- NVCF 返回空 completion (12 字符)，gateway 正确检测+快速 abort

### all_tiers_exhausted (5×, dsv4p_nv)
- avg 63,580ms ≈ tier_budget=66s (budget 触底 pattern)
- 无 fallback 触发 (fallback_occurred=false for all)
- tier_chain: `['dsv4p_nv'] (no fallback, 3model)` — FALLBACK_GRAPH 为空，预期行为
- 无 NV-MS-FB 日志 (ms_gw fallback 未触发)
- 无 NV-PEER-FB 日志 (peer-fb 未触发)
- 无 NV-TIER-FAIL 日志 (tier fail 未触发? 或已过期)

### 日志信号 (全零 — 无活跃故障)
| 信号 | 计数 |
|------|------|
| NV-TIER-FAIL | 0 |
| NV-ALL-TIERS-FAIL | 0 |
| NV-CYCLE | 0 |
| NV-PEER-FB | 0 |
| NV-MS-FB | 0 |
| NV-EMPTY-FASTBREAK | 0 |
| 504 | 0 |
| NV-ZOMBIE | 12 (last 100 lines) |

### tier_attempts
- glm5_2_nv: 2× 429_integrate_rate_limit (瞬态, 无 elapsed_ms)

### ms_gw 健康
- 20req/16OK (80% SR)
- 状态: ok, client_disconnect, error
- 日志: MS-OK-STREAM + MS-STREAM-DONE 正常

### hourly SR
| 小时 (UTC) | 请求 | OK | 失败 | SR |
|-----------|------|-----|------|-----|
| 14:00 | 4 | 1 | 3 | 25.0% |
| 15:00 | 6 | 2 | 4 | 33.3% |
| 16:00 | 9 | 6 | 3 | 66.7% |
| 17:00 | 8 | 4 | 4 | 50.0% |
| 18:00 | 18 | 14 | 4 | 77.8% |
| 19:00 | 9 | 5 | 4 | 55.6% |
| 20:00 | 5 | 4 | 1 | 80.0% |

### compose vs container env (全部一致，无 stale)
- NVU_MS_GW_FALLBACK_MODELMAP: compose=container = `glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms`
- NVU_PEER_FB_SKIP_MODELS: compose=container = `(空)`
- TIER_TIMEOUT_BUDGET_S: 205
- UPSTREAM_TIMEOUT: 66
- NVU_TIER_BUDGET_DSV4P_NV: 66
- NVU_MS_GW_FALLBACK_TIMEOUT: 120

## 参数状态 (全部触底/最优 — 与 R1498 相同)

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

1. **zombie_empty_completion (78% 失败)**: 代码级 NVCF content-filter 检测 — NVCF 返回 finish_reason=stop 但 content_chars=12 (<50)。gateway 正确检测+快速 abort (3-20s)。无配置参数可修复。openclaw 收到 `[NV-ZOMBIE-ERROR-CHUNK]` 后触发 model fallback。

2. **all_tiers_exhausted (22% 失败)**: 5× dsv4p_nv ATE, avg 63,580ms ≈ tier_budget=66s。budget 触底 pattern — 无 fallback 触发 (FALLBACK_GRAPH 为空, ms_gw MODELMAP 无 dsv4p_nv)。但 NVU_TIER_BUDGET_DSV4P_NV=66 已触底 (=UPSTREAM)，再降会误杀成功请求。无 NV-MS-FB 日志表明 ms_gw fallback 对 dsv4p_nv 不可达 (MODELMAP 无 dsv4p_nv 条目 — R1488 有意移除)。peer-fb 未触发 (无 NV-PEER-FB 日志)。BUDGET 已 205 足够。

3. **全部参数触底**: 无任何可调参数。所有 FASTBREAK=1/2, COOLDOWN=15/25, TIMEOUT=66/120 均已最优。

4. **无新流量**: 与 R1498 相同的数据集 (59req, 最后请求 20:06 UTC)，无新数据可分析。

## 铁律验证
- ✅ 只改HM1: 本轮无修改
- ✅ 改前必有数据: 6h DB + 日志信号 + compose vs container 对比
- ✅ 改后必有验证: N/A
- ✅ 聚焦 nv_gw: 仅分析 nv_gw 链路
- ✅ 所有修改写入仓库: 本轮 NOP 仍记录
## ⏳ 轮到HM1优化HM2
