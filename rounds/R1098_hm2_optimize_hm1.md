# HM2 Optimize HM1 — Round R1098

## 触发
cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (R884+ double-dispatch pattern)
- HM1 本地 git log 停留在 R821（277 轮落后）

## 数据收集 (改前必有数据)

### nv_gw 容器状态
- 重启时间: 2026-07-10 13:59 UTC (R1097 部署 NVU_FALLBACK_HEALTH_THRESHOLD=0.05)
- 容器: nv_gw, Up 10 minutes (healthy)
- 有效窗口: 重启后 ~10 min, 仅 glm5_2_nv integrate 流量

### 6h 窗口
| 指标 | 值 |
|------|-----|
| 总请求 | 23 |
| 成功 | 20 (87.0% SR) |
| 失败 | 3 |
| 路径 | glm5_2_nv integrate: 20/21, dsv4p_nv ATE: 2 (pre-restart) |

### 6h 错误分类
| error_type | cnt |
|------------|-----|
| all_tiers_exhausted | 2 (pre-restart dsv4p_nv) |
| NVStream_TimeoutError | 1 (glm5_2_nv) |

### 24h 按模型
| request_model | cnt | ok | err | SR |
|---------------|---|---|-----|-----|-----|
| glm5_2_nv | 369 | 354 | 15 | 95.9% |
| dsv4p_nv | 74 | 61 | 13 | 82.4% |
| kimi_nv | 62 | 61 | 1 | 98.4% |
| minimax_m3_nv | 45 | 37 | 8 | 82.2% |

### dsv4p_nv ATE (24h, 全部 pre-restart)
- 13 ATE, 全部 single-tier, fallback_occurred=false, fallback_tiers_used={dsv4p_nv}
- 全部 pre-restart (R1097 部署前)
- 0 post-restart dsv4p_nv 流量

### Post-restart 流量 (13:59 UTC → 22:10 UTC)
- glm5_2_nv integrate: 全部 200 OK, 1st-key 成功
- avg TTFB: ~5-42s, 正常
- 0 dsv4p_nv/kimi_nv/minimax_m3_nv 流量
- 0 tier_attempts 新条目 (仅 1 条 pre-restart IntegrateTimeout)

### 关键 env vars
| 参数 | 值 |
|------|-----|
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 (R1097) ✓ |
| TIER_TIMEOUT_BUDGET_S | 198 |
| NVU_TIER_BUDGET_DSV4P_NV | 66 |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 |
| UPSTREAM_TIMEOUT | 66 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 |
| NVU_EMPTY_200_FASTBREAK | 2 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv |

### ms_gw 健康
- MS-OK-STREAM / MS-STREAM-DONE: glm5_2, deepseek-v4-pro 正常
- 1x MS-STREAM-CLIENT-EOF (deepseek non-stream relay, BrokenPipeError — nv_gw 关闭了连接)
- 正常工作, 无优化空间

### nv_gw logs
```
[NV-REQ] tier_chain=['glm5_2_nv'] (no fallback, 3model) ← FALLBACK_GRAPH={} 预期状态
[NV-INTEGRATE] tier=glm5_2_nv k2 → integrate → SUCCESS on first attempt
```

## 诊断

R1097 部署 NVU_FALLBACK_HEALTH_THRESHOLD=0.05 仅 10 分钟，重启后仅有 glm5_2_nv integrate 流量。无 dsv4p_nv/kimi/minimax 流量，R1097 变更未测试。所有 ATE 均为 pre-restart。

**NOP 判定**:
- False trigger dispatch (pre-run script 检测到自提交)
- R1097 变更刚部署, 无新数据验证
- 无 ms_gw 优化空间
- 所有参数已达地板/已验证值

## 变更

**零变更 (NOP)**
- 不改任何参数
- 不改 compose
- 不重启容器

**铁律: 只改 HM1 不改 HM2** ✓

## 评判
- 更少报错: 等待 R1097 变更积累数据, 不引入新变动
- 更快请求: 所有参数已达地板 (UPSTREAM=66, FASTBREAK=1, BUDGET=198)
- 超低延迟: glm5_2_nv integrate 1st-key 成功, 无延迟异常
- 稳定优先: NOP 避免在 false trigger 时修改配置

## ⏳ 轮到HM1优化HM2
