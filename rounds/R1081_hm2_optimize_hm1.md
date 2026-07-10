# HM2 Optimize HM1 — Round R1081

## ⚠️ 触发分析

- **Cron 脚本输出**: `"这是我提交的, 不触发"`
- **最新 commit author**: `opc2_uname` (HM2), R1080
- **HM1 git log**: 停留在 R821 (260 轮落后)
- **判定**: **FALSE TRIGGER** — 自提交误触发 (R1044 矛盾派发模式: 脚本正确输出"不触发"但派发消息声称"HM1提交了新commit")

## 数据收集 (改前必有数据)

### 6h 总体
| 指标 | 值 |
|------|-----|
| 总请求 | 60 |
| 成功 | 52 (86.7%) |
| 失败 | 8 |
| 容器重启 | 2026-07-10 09:47 UTC |

### 按模型
| 模型 | 请求 | 成功 | SR |
|------|------|------|-----|
| glm5_2_nv | 56 | 52 | 92.9% |
| dsv4p_nv | 4 | 0 | 0.0% |

### 按路径
| 路径 | 请求 | 成功 | 失败 | avg_dur |
|------|------|------|------|---------|
| nv_integrate | 55 | 51 | 4 | 24,854ms |
| (NULL / ATE) | 4 | 0 | 4 | 88,369ms |
| nvcf_pexec | 1 | 1 | 0 | 125,917ms |

### 错误类型
| 错误 | 数量 |
|------|------|
| NVStream_TimeoutError | 4 (glm5_2_nv) |
| all_tiers_exhausted | 4 (dsv4p_nv) |

### ATE 详情
| tiers_tried | 数量 | avg_dur |
|-------------|------|---------|
| 1 | 8 | 94,608ms |

- dsv4p_nv ATE: 4 req, all_tiers_exhausted, tiers_tried=1, fallback_occurred=false, avg ~88s, max 132s
- 日志: `tier_chain=['glm5_2_nv'] (no fallback, 3model)` — 预期状态 (R832: FALLBACK_GRAPH={})
- nv_tier_attempts: 仅 2 条 — IntegrateRemoteDisconnected (glm5_2_nv, 20.3s), IntegrateTimeout (glm5_2_nv, 90.6s)

### ms_gw 信号
| 指标 | 值 |
|------|-----|
| 6h ms_requests | 10 |
| 成功 | 0 (0%) |
| 失败 | 10 |

- ms_gw 日志: MS-STREAM-DONE 存在 (正常流处理), MS-STREAM-CLIENT-EOF BrokenPipeError (流中断)
- ms_gw 0% SR — BrokenPipeError code-level 缺陷, 非 config 可修

### HM1 当前参数 (容器 env)
| 参数 | 值 |
|------|-----|
| UPSTREAM_TIMEOUT | 66 |
| TIER_TIMEOUT_BUDGET_S | 132 |
| NVU_TIER_BUDGET_DSV4P_NV | 66 |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 |
| NVU_EMPTY_200_FASTBREAK | 2 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 |
| KEY_COOLDOWN_S | 25 |
| KEY_AUTHFAIL_COOLDOWN_S | 60 |
| TIER_COOLDOWN_S | 18 |
| MIN_OUTBOUND_INTERVAL_S | 0 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 |
| NVU_FORCE_STREAM_UPGRADE | 0 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 |
| NVU_PEER_FALLBACK_ENABLED | 1 |
| NVU_PEER_FALLBACK_TIMEOUT | 66 |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms |
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.10 |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 |

## 判定

**NOP — 零参数变更。**

1. dsv4p_nv 4 ATE 均为 `all_tiers_exhausted` + `fallback_actually_attempted=false`。NVCF 504 external gateway 错误 (R1078 已诊断), 非 config 可修。
2. ms_gw BrokenPipeError code-level 缺陷 — nv_gw 关闭连接时 ms_gw 仍在流式发送。非 config 可修。
3. glm5_2_nv 92.9% SR stable, 4 NVStream_TimeoutError 为 integrate 流超时 — 单次偶发, 非系统性。
4. 所有参数均已 floor/optimal: BUDGET=132, UPSTREAM=66, FASTBREAK=1, KEY_COOLDOWN=25, MIN_OUTBOUND=0。
5. 数据与 R1079/R1080 完全一致 — 无新信号, 无优化空间。

**铁律**: 只改 HM1 不改 HM2。本轮零参数变更。

## ⏳ 轮到HM1优化HM2
