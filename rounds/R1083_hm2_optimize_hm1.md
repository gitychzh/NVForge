# HM2 Optimize HM1 — Round R1083

## ⚠️ 触发分析

- **Cron 脚本输出**: `"这是我提交的, 不触发"`
- **最新 commit author**: `opc2_uname` (HM2), R1082
- **HM1 git log**: 停留在 R821 (opc2_uname, 262 轮落后)
- **判定**: **FALSE TRIGGER** — 自提交误触发 (R1044 矛盾派发模式: 脚本正确输出"不触发"但派发消息声称"HM1提交了新commit")

## 数据收集 (改前必有数据)

### 6h 总体 (容器重启 2026-07-10 09:47 UTC)
| 指标 | 值 |
|------|-----|
| 总请求 | 59 |
| 成功 | 51 (86.4%) |
| 失败 | 8 |

### 按模型
| 模型 | 请求 | 成功 | SR |
|------|------|------|-----|
| glm5_2_nv | 55 | 51 | 92.7% |
| dsv4p_nv | 4 | 0 | 0.0% |

### 按路径
| 路径 | 请求 | 成功 | 失败 | avg_dur |
|------|------|------|------|---------|
| nv_integrate | 54 | 50 | 4 | 24,954ms |
| (NULL / ATE) | 4 | 0 | 4 | 88,369ms |
| nvcf_pexec | 1 | 1 | 0 | 125,917ms |

### 错误类型
| 错误 | 数量 |
|------|------|
| NVStream_TimeoutError | 4 (glm5_2_nv) |
| all_tiers_exhausted | 4 (dsv4p_nv) |

### dsv4p_nv ATE 详情 (全部 pre-restart)
| request_id | 耗时 | 错误子分类 | fallback_attempted |
|-----------|------|----------|-------------------|
| 6357fb94 | 132,017ms | all_tiers_failed_in_mapped_tier | f |
| 4e988465 | 1,328ms | all_tiers_failed_in_mapped_tier | f |
| f5569a02 | 110,073ms | all_tiers_failed_in_mapped_tier | f |
| e98b9169 | 110,058ms | all_tiers_failed_in_mapped_tier | f |

### 24h 扩展窗口
| 模型 | 请求 | 成功 | SR |
|------|------|------|-----|
| glm5_2_nv | 406 | 389 | 95.8% |
| dsv4p_nv | 131 | 110 | 84.0% |
| kimi_nv | 62 | 61 | 98.4% |
| minimax_m3_nv | 45 | 37 | 82.2% |

### 24h 错误全景
| 错误 | 数量 |
|------|------|
| all_tiers_exhausted | 37 |
| NVStream_TimeoutError | 7 |
| stream_total_deadline | 3 |

### nv_tier_attempts (24h, 按 tier+error)
| tier | error_type | cnt | avg_ms | max_ms |
|------|-----------|-----|--------|--------|
| dsv4p_nv | IntegrateTimeout | 14 | 56,021 | 67,086 |
| dsv4p_nv | NVCFPexecRemoteDisconnected | 1 | 9,134 | 9,134 |
| glm5_2_nv | IntegrateRemoteDisconnected | 1 | 20,284 | 20,284 |
| glm5_2_nv | IntegrateTimeout | 1 | 90,566 | 90,566 |
| minimax_m3_nv | IntegrateTimeout | 1 | 90,762 | 90,762 |

### NVCFPexecTimeout 按 key 分布 (6h)
- 无 NVCFPexecTimeout — dsv4p_nv 无 pexec 流量, glm5_2_nv 仅 integrate 模式

### Fallback 状态
- fallback_occurred: false (全部 59 请求)
- fallback_actually_attempted: false (全部 59 请求)
- dsv4p_nv ATE: tiers_tried=1, fallback_actually_attempted=false
- 日志: `tier_chain=['glm5_2_nv'] (no fallback, 3model)` — 预期状态 (FALLBACK_GRAPH={})
- 所有 dsv4p_nv ATE 均为 pre-restart (09:47 UTC), 零 post-restart dsv4p 流量

### ms_gw 信号
- ms_requests 6h: 10 req, 0 OK
- ms_gw 日志: MS-STREAM-CLIENT-EOF BrokenPipeError 持续 (code-level 缺陷)
- dsv4p_ms: DeepSeek-V4-Pro 返回数据 但 BrokenPipeError 杀流
- glm5_2_ms: ZHIPUAI/glm-5.2 正常 (MS-STREAM-DONE 成功)

### docker logs (nv_gw, 全部 post-restart)
- glm5_2_nv integrate: 全部 k1-k4 1st key 成功, 3.0-5.7s ttfb, 极健康
- 无 dsv4p_nv 请求 (post-restart 零流量)
- 无 peer-fb 触发
- 无 MS-FB 触发

### HM1 当前参数 (容器 env)
| 参数 | 值 |
|------|-----|
| UPSTREAM_TIMEOUT | 66 |
| TIER_TIMEOUT_BUDGET_S | 132 |
| NVU_TIER_BUDGET_DSV4P_NV | 66 |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 |
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
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 |
| NVU_STREAM_TOTAL_DEADLINE_S | 90 |
| NVU_CONNECT_RESERVE_S | 0 |

## 判定

**NOP — 零参数变更。** 数据与 R1082/R1081/R1080/R1079 一致。

1. dsv4p_nv 4 ATE 均为 pre-restart (09:47 UTC), 零 post-restart dsv4p 流量。NVCF 504 external gateway 错误 (R1078 已诊断), 非 config 可修。
2. ms_gw BrokenPipeError code-level 缺陷 — nv_gw 关闭连接时 ms_gw 仍在流式发送 (MS-STREAM-CLIENT-EOF)。非 config 可修。
3. glm5_2_nv 92.7% SR (6h), 95.8% (24h), 全部 integrate 1st key 成功。ttfb 3.0-5.7s 极健康。
4. kimi_nv 98.4% SR (24h), minimax_m3_nv 82.2% (24h)。glm5_2_nv 无 PEER_FB_SKIP 风险 — 当前 95.8% SR 证明 skip 无害。
5. 所有参数均已 floor/optimal: BUDGET=132, UPSTREAM=66, FASTBREAK=1, KEY_COOLDOWN=25, MIN_OUTBOUND=0。
6. nv_tier_attempts 6h: 仅 2 条 (glm5_2_nv integrate 单次超时+断连) — 系统极度稳定。
7. 24h dsv4p_nv 84.0% SR (110/131) — NVCF 504 间歇性, 非持续故障。ms_gw 偶尔 rescue (MS-OK-STREAM + MS-STREAM-DONE 可见)。

**铁律**: 只改 HM1 不改 HM2。本轮零参数变更。

## ⏳ 轮到HM1优化HM2