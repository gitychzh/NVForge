# R1182: HM2→HM1 — NOP (false trigger, 50th chain of R1133, zombie-only, all params floor/optimal, NVCF content-filter not config-fixable)

## TL;DR
6h: 26req/11OK(42.3%)/15zombie. All failures zombie_empty_completion (glm5_2_nv integrate, NVCF content-filter stop+12chars, 169K-172K input). Gateway detection+error-chunk correct. dsv4p_nv 0 traffic 6h. ms_gw 0 nv-initiated traffic. compose md5 unchanged (7975939c245761e451a8813852dcb9bf). All params at floor/optimal. Zero param. 铁律:只改HM1不改HM2.

## 1. 触发分析
- cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit: R1181 (opc2_uname, HM2) — 自提交误触发
- R1182: 二次派遣 (double-dispatch) — R1181 已由预运行脚本提交, symlink 已指向 R1181, 数据相同
- 50th chain of R1133 (R1133→R1182), 全部 NOP + zombie-only

## 2. 6h 数据全景
| 指标 | 值 |
|------|----|
| 总请求 | 26 |
| 成功 | 11 (42.3%) |
| 失败 | 15 (57.7%) |
| 错误类型 | 15× zombie_empty_completion |
| 上游路径 | 26× nv_integrate (全部) |
| 模型分布 | 26× glm5_2_nv (100%) |
| dsv4p_nv | 0 请求 |
| fallback_occurred | 0 |
| nv_tier_attempts | 0 rows |
| NVCFPexecTimeout | 0 |
| ms_gw 流量 | 0 (nv_gw 未触发 ms_gw) |

## 3. 每小时 SR
| 小时 | 总量 | OK | fail | SR |
|------|------|----|------|----|
| 00:00 | 4 | 0 | 4 | 0.0% |
| 01:00 | 4 | 2 | 2 | 50.0% |
| 02:00 | 4 | 2 | 2 | 50.0% |
| 03:00 | 4 | 2 | 2 | 50.0% |
| 04:00 | 4 | 2 | 2 | 50.0% |
| 05:00 | 4 | 2 | 2 | 50.0% |
| 06:00 | 2 | 1 | 1 | 50.0% |

Pattern: 每30min 2请求 (1×OK + 1×zombie). 稳定节奏, 无突发.

## 4. 最近 10 条请求
| 时间 | 模型 | 状态 | ttfb | dur | 错误 |
|------|------|------|------|-----|------|
| 06:03:35 | glm5_2_nv | 502 | 4767 | 4768 | zombie_empty_completion |
| 06:03:24 | glm5_2_nv | 200 | 4859 | 4859 | — |
| 05:33:36 | glm5_2_nv | 502 | 4494 | 4494 | zombie_empty_completion |
| 05:33:24 | glm5_2_nv | 200 | 5450 | 5451 | — |
| 05:03:39 | glm5_2_nv | 502 | 3540 | 3540 | zombie_empty_completion |
| 05:03:24 | glm5_2_nv | 200 | 8288 | 8288 | — |
| 04:33:34 | glm5_2_nv | 502 | 3296 | 3297 | zombie_empty_completion |
| 04:33:24 | glm5_2_nv | 200 | 3812 | 3813 | — |
| 04:03:36 | glm5_2_nv | 502 | 6059 | 6060 | zombie_empty_completion |
| 04:03:25 | glm5_2_nv | 200 | 5251 | 5251 | — |

## 5. 日志分析
```
[14:03:24.6] [NV-REQ] mapped_model=glm5_2_nv start_tier=glm5_2_nv tier_chain=['glm5_2_nv'] (no fallback, 3model)
[14:03:35.4] [NV-REQ] mapped_model=glm5_2_nv start_tier=glm5_2_nv tier_chain=['glm5_2_nv'] (no fallback, 3model)
[14:03:40.1] [NV-ZOMBIE-EMPTY] (glm5_2_nv) passthrough zombie empty completion: finish_reason=stop but content_chars=12 < 50, input_chars=171792 >= 5000, no tool_calls — aborting stream
[14:03:40.1] [NV-ZOMBIE-ERROR-CHUNK] (glm5_2_nv) sent finish_reason=content_filter error SSE chunk to openclaw, should trigger fallback
```

- 每30min 2请求: 1×OK (5-9s) + 1×zombie (3-6s fast abort)
- tier_chain=['glm5_2_nv'] (no fallback, 3model) — FALLBACK_GRAPH 为空, 预期正常 (R832)
- zombie 检测: content_chars=12 << 50, input_chars=169K-172K, finish_reason=stop, NVCF content-filter 触发
- 错误 chunk 正确发送给 openclaw → openclaw 应 fallback 到 ms_gw
- 零 NV-TIER-FAIL, 零 NV-MS-FB, 零 NV-EMPTY-FASTBREAK, 零 NV-PEER-FB, 零 NV-GLOBAL-COOLDOWN

## 6. 配置状态
| 参数 | 值 | 状态 |
|------|----|----|
| UPSTREAM_TIMEOUT | 66 | floor |
| TIER_TIMEOUT_BUDGET_S | 198 | optimal |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | optimal |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | optimal |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | optimal (R1039 code-level no-op) |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | optimal |
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 | optimal |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | optimal |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | optimal |
| TIER_COOLDOWN_S | 15 | optimal |
| KEY_COOLDOWN_S | 25 | optimal |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | floor |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | dead param (R919) |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | optimal |
| NVU_FORCE_STREAM_UPGRADE | 0 | optimal |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | optimal |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | optimal |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | optimal |
| compose md5 | 7975939c245761e451a8813852dcb9bf | unchanged 48h+ |
| 容器重启 | 2026-07-10T19:03:27Z (~19h ago) | stable |
| HEALTH_THRESHOLD | 0.05 | floor |

## 7. 决策: NOP (零参数变更)
- **所有失败均为 zombie_empty_completion** — NVCF content-filter 导致的僵尸完成
- gateway 正确检测并发送 error chunk 给 openclaw → openclaw 应 fallback
- 3-6s fast abort 远优于旧版 96s NVStream_TimeoutError hang
- code-level zombie detection 功能正常, 非 config-fixable
- **所有参数已达 floor/optimal** — 无进一步优化空间
- dsv4p_nv 零流量 6h, ms_gw 零 nv_gw 触发流量
- 零 NVCFPexecTimeout, 零 tier_attempts, 零 cache miss
- 50th consecutive NOP in R1133 chain — zombie pattern stable, no config change can improve

## ⏳ 轮到HM1优化HM2