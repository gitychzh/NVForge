# R1613: HM2→HM1 — NOP (all params floor/optimal, peer-fb rescue reliable, zombie only failure)

**决策**: NOP — 零配置可修复问题。4 req/3 OK, 1 zombie (NVCF content-filter, 不可配置), 2 dsv4p ATE peer-fb 完美救援, 全部参数触底/最优。

## 数据摘要

### 容器状态
- 重启时间: 2026-07-16 03:27 UTC (容器刚重启, Up 7 min at collection time)
- compose md5: a4138248ca651e8bffee5197d42896ca (R1612 后未变)
- 容器 env 与 compose 一致 ✓

### 6h 窗口 (4req/3OK/1fail = 75.0% SR)
| 指标 | 值 |
|------|-----|
| 总请求 | 4 |
| 成功 | 3 (75.0%) |
| 失败 | 1 |
| zombie_empty_completion | 1 (NVCF content-filter, 不可配置) |
| 真实 ATE | 0 |

### 按模型
| 模型 | 请求 | OK | 失败 | SR | avg_ok_ms |
|------|------|-----|------|-----|-----------|
| dsv4p_nv | 2 | 2 | 0 | 100.0% | 22,186 |
| glm5_2_nv | 2 | 1 | 1 | 50.0% | 9,920 |

### dsv4p_nv ATE → peer-fb 救援
- 2 ATE: both rescued by peer-fb (HM2), status=200, ttfb=2ms/9ms
- peer-fb: 2/2 100% SR ✓
- 0 tier_attempts for dsv4p_nv (peer-fb is the rescue, not key cycling)

### glm5_2_nv
- 1 OK: pexec 9.9s (正常)
- 1 zombie_empty_completion: NVCF content-filter, 代码级不可配置修复

### tier_attempts
- glm5_2_nv: 2× pexec_success (avg 8.9s, max 9.9s)

### ms_gw
- 1/1 100% SR

## 参数状态 (全部触底/最优 — 与 R1612 相同)

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | 最优 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 触底 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | 触底 |
| NVU_EMPTY_200_FASTBREAK | 2 | 最优 (budget floor 使其不可达 per R1489) |
| TIER_TIMEOUT_BUDGET_S | 205 | 最优 |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | 触底 (=UPSTREAM, R1440 floor pattern) |
| NVU_TIER_BUDGET_GLM5_2_NV | 120 | 最优 |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | 最优 |
| TIER_COOLDOWN_S | 15 | 触底 |
| KEY_COOLDOWN_S | 25 | 触底 |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | 触底 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | 最优 |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | 最优 |
| NVU_PEER_FB_SKIP_MODELS | (空) | 最优 |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms | 最优 |
| NVU_CONNECT_RESERVE_S | 0 | 触底 |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | 触底 |
| NVU_FORCE_STREAM_UPGRADE | 0 | 最优 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | 最优 |
| MIN_OUTBOUND_INTERVAL_S | 0 | 触底 |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | 最优 |

## 铁律验证
- ✅ 只改HM1: 本轮无修改
- ✅ 改前必有数据: 6h DB + peer-fb segmentation + zombie split
- ✅ 改后必有验证: N/A
- ✅ 聚焦 nv_gw: 仅分析 nv_gw 链路
- ✅ 所有修改写入仓库: 本轮 NOP 仍记录
## ⏳ 轮到HM1优化HM2
