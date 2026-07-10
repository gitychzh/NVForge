# HM2 Optimize HM1 — Round R1094

## 1. 触发分析
cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2, R1093)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — double-dispatch false trigger
- HM1 本地 git log 停留在 R821（273 轮落后 HM2 的 R1094）

## 2. 数据收集（改前必有数据）

### 6h 窗口 (21:05 UTC 回溯)
| 指标 | 值 |
|------|----|
| 总请求 | 27 |
| 成功 | 24 (88.9%) |
| 失败 | 3 (11.1%) |

### 按模型
| 模型 | 请求 | OK | 失败 | SR% | avg_dur |
|------|------|----|------|-----|---------|
| glm5_2_nv | 25 | 24 | 1 | 96.0% | 27,554ms |
| dsv4p_nv | 2 | 0 | 2 | 0.0% | 66,673ms |

### 按路径
| 路径 | 请求 | OK | 失败 | avg_ttfb | avg_dur |
|------|------|----|------|----------|---------|
| nv_integrate | 24 | 23 | 1 | 20,183ms | 23,456ms |
| ATE (NULL) | 2 | 0 | 2 | 1,060ms | 66,673ms |
| nvcf_pexec | 1 | 1 | 0 | 125,916ms | 125,917ms |

### 错误分类
| 错误类型 | 数量 |
|----------|------|
| all_tiers_exhausted | 2 |
| NVStream_TimeoutError | 1 |

### 失败详情
| 时间 | 模型 | 耗时 | 错误 | tiers_tried | fallback_attempted |
|------|------|------|------|------------|--------------------|
| 09:06 UTC | dsv4p_nv | 132,017ms | all_tiers_exhausted | 1 | f |
| 08:20 UTC | dsv4p_nv | 1,328ms | all_tiers_exhausted | 1 | f |

### nv_tier_attempts
| tier | error_type | cnt | avg_ms | max_ms |
|------|------------|-----|--------|--------|
| glm5_2_nv | IntegrateTimeout | 1 | 90,566ms | 90,566ms |

### 容器状态
- nv_gw 重启: 2026-07-10T12:09:57Z (9h ago)
- 重启后: 仅 2 请求 (glm5_2_nv integrate, 均 OK)
- dsv4p_nv: **重启后零流量** — R1088 BUDGET=198 完全未测试

### ms_gw
- ms_requests 6h: 4 total, 0 OK
- 模式: MS-OK + MS-STREAM-CLIENT-EOF / BrokenPipeError (已知流同步缺陷, 非配置可修复)
- dsv4p_ms 处理成功但 nv_gw 先断开连接

### Fallback 触发
- fallback_occurred=false for ALL 27 请求
- 无跨模型 fallback, 无 peer-fallback 触发

## 3. 决策

**NOP — 零参数修改**

理由:
1. **False trigger**: cron 脚本明确标记 "不触发"
2. **Post-restart 零 dsv4p_nv 流量**: R1088 的 BUDGET=198 完全未测试
3. **所有 HM1 env 参数已处于优化值**:
   - UPSTREAM_TIMEOUT=66 (NVCFPexecTimeout 绑定)
   - TIER_TIMEOUT_BUDGET_S=198 (R1088: ms_gw fallback budget 132s)
   - NVU_TIER_BUDGET_DSV4P_NV=66 (R1078: cap dsv4p tier)
   - NVU_TIER_BUDGET_GLM5_2_NV=96 (R835: integrate per-model budget)
   - NVU_PEXEC_TIMEOUT_FASTBREAK=1 (R997: 已验证 10h+)
   - NVU_EMPTY_200_FASTBREAK=2 (R1031: key-specific signal)
   - NVU_INTEGRATE_TIMEOUT_FASTBREAK=1 (R1010: 已验证)
   - NVU_MS_GW_FALLBACK_TIMEOUT=180 (R1088: BUDGET=198 覆盖)
   - NVU_PEER_FB_SKIP_MODELS=glm5_2_nv (R1039)
   - NVU_FALLBACK_HEALTH_THRESHOLD=0.10 (R818: 已验证)
4. **glm5_2_nv 96.0% SR** — 稳定, 无需修改
5. **dsv4p_nv 2 ATE 均为 pre-restart** — 重启后零流量, 无数据驱动修改
6. **ms_gw BrokenPipeError**: 已知流同步缺陷, 非配置可修复

铁律: 只改 HM1 不改 HM2。

## ⏳ 轮到HM1优化HM2
