# R1496: HM2→HM1 — NOP (all params floor/optimal, 18 zombie code-level, 0 real ATE post-restart)

**决策**: NOP — 零配置可修复问题。所有参数均已触底/最优。

## 数据摘要

### 6h窗口 (57req/34OK/23fail = 59.6% SR)
| 指标 | 值 |
|------|-----|
| 总请求 | 57 |
| 成功 | 34 (59.6%) |
| 失败 | 23 |
| zombie_empty_completion | 18 (NVCF content-filter, 220K+ input chars → 12 char output) |
| all_tiers_exhausted | 5 (全部 pre-restart) |

### 按模型
| 模型 | 请求 | OK | 失败 | SR | avg_dur |
|------|------|-----|------|-----|---------|
| dsv4p_nv | 33 | 22 | 11 | 66.7% | 29,871ms |
| glm5_2_nv | 24 | 12 | 12 | 50.0% | 13,758ms |

### 容器重启后 (18:15 UTC, 2h uptime)
| 指标 | 值 |
|------|-----|
| 请求 | 13 |
| 成功 | 8 (61.5%) |
| 失败 | 5 |
| 失败原因 | **全部 zombie_empty_completion** |
| 真实 ATE | **0** |
| tier cycling | 0 (NV-TIER-FAIL: 空) |
| peer-fb | 0 (NV-PEER-FB: 空) |
| ms_gw fallback | 0 (NV-MS-FB: 空) |

### ms_gw 健康
- 20req/16OK (80% SR)
- dsv4p_ms: healthy, 3-8s响应 (MS-OK-STREAM)
- glm5_2_ms: 正常

### tier_attempts
- glm5_2_nv: 2× 429_integrate_rate_limit (瞬态, 无 elapsed_ms)

## 僵尸分析

zombie_empty_completion pattern:
- dsv4p_nv: 6× (avg 19,624ms, avg input 221,227 chars)
- glm5_2_nv: 12× (avg 12,661ms, avg input 220,329 chars)
- 日志: `[NV-ZOMBIE-EMPTY] finish_reason=stop but content_chars=12 < 50, input_chars=221523 >= 5000`
- NVCF返回空completion (12字符), gateway正确检测+快速abort (2-25s vs old 96s hang)
- **代码级特性, 不可配置修复** (R1107 pattern)

## 参数状态 (全部触底/最优)

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | 最优 (R1490) |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 触底 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | 触底 |
| NVU_EMPTY_200_FASTBREAK | 2 | 最优 (R1031, 但 budget floor 使其不可达 per R1489) |
| TIER_TIMEOUT_BUDGET_S | 205 | 最优 (R1486: +30s from 175) |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | 触底 (=UPSTREAM, R1440 floor pattern) |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | 最优 |
| TIER_COOLDOWN_S | 15 | 触底 (R1103 revert 18→15) |
| KEY_COOLDOWN_S | 25 | 触底 |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | 触底 (R919) |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | 最优 |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | 最优 |
| NVU_PEER_FB_SKIP_MODELS | (空) | 最优 (R1488: 移除 dsv4p_nv) |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms | 最优 (R1488: 移除 dsv4p_nv:dsv4p_ms) |
| NVU_CONNECT_RESERVE_S | 0 | 触底 |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | 触底 |

## 铁律验证
- ✅ 只改HM1: 本轮无修改
- ✅ 改前必有数据: 6h DB + post-restart segmentation + zombie split
- ✅ 改后必有验证: N/A
- ✅ 聚焦 nv_gw: 仅分析 nv_gw 链路
## ⏳ 轮到HM1优化HM2
