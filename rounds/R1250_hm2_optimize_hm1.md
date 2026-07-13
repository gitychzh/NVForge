# HM2 Optimize HM1 — Round R1250

## 触发分析
cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = opc2_uname (HM2)
- HM1 本地 git log 停留在 R1206，44 轮落后
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发（false trigger, double-dispatch NOP chain R1133→R1250, 第 118 轮）

## 数据收集（改前必有数据）

### 容器状态
- 容器: nv_gw, Up About an hour (healthy)
- 重启时间: 2026-07-13T14:33:57Z
- compose md5: 6e23559de1376d2d638f98f34a544139（不变）

### 6h 总体
109req/88OK/21fail=80.7% SR

### 按模型
| 模型 | 请求 | OK | 失败 | SR | 平均延迟 |
|------|------|-----|------|------|------|
| glm5_2_nv | 105 | 84 | 21 | 80.0% | 20,777ms |
| dsv4p_nv | 4 | 4 | 0 | 100% | 28,308ms |

### 按上游路径
| 路径 | 请求 | OK | 失败 | 平均TTFB | 平均延迟 |
|------|------|-----|------|------|------|
| nv_integrate | 97 | 80 | 17 | 17,684ms | 19,225ms |
| nvcf_pexec | 9 | 8 | 1 | 45,960ms | 45,961ms |
| (ATE) | 3 | 0 | 3 | 767ms | 5,449ms |

### 错误分类
| 错误类型 | 数量 |
|----------|------|
| zombie_empty_completion | 17 |
| all_tiers_exhausted | 3 |
| NVStream_IncompleteRead | 1 |

### 逐小时 SR
| 小时 (UTC) | 请求 | OK | 失败 | SR |
|------------|------|-----|------|------|
| 09:00 | 14 | 13 | 1 | 92.9% |
| 10:00 | 42 | 33 | 9 | 78.6% |
| 11:00 | 8 | 6 | 2 | 75.0% |
| 12:00 | 27 | 22 | 5 | 81.5% |
| 13:00 | 6 | 5 | 1 | 83.3% |
| 14:00 | 8 | 6 | 2 | 75.0% |
| 15:00 | 5 | 4 | 1 | 80.0% |

### fallback 触发
0 fallback 触发（fallback_occurred=false for all 110 requests including ATE）

### nv_tier_attempts
| tier | error_type | 数量 | 平均 | 最大 |
|------|-----------|------|------|------|
| glm5_2_nv | IntegrateTimeout | 2 | 90,804ms | 91,140ms |

### ms_gw
ms_requests 表: 6req/0OK（已知 R980 陷阱 — ms_gw 不写 DB）
ms_gw 日志: MS-STREAM-DONE 正常（glm5_2 via ZHIPUAI/GLM-5.2）
ms_gw 实际在正常工作，BrokenPipeError 未出现

### nv_gw 日志特征
- tier_chain=['glm5_2_nv'] (no fallback, 3model) — 预期常态（R832 FALLBACK_GRAPH={}）
- NV-ZOMBIE-EMPTY + NV-ZOMBIE-ERROR-CHUNK 活跃（code-level zombie detection）
- 无 NV-MS-FB 日志（ms_gw fallback 未触发）
- 无 NV-TIER-FAIL 日志
- 无 NV-EMPTY-FASTBREAK 日志

### 关键参数（全部 floor/optimal）
- UPSTREAM_TIMEOUT=66
- TIER_TIMEOUT_BUDGET_S=210
- TIER_COOLDOWN_S=15
- KEY_COOLDOWN_S=25
- KEY_AUTHFAIL_COOLDOWN_S=60
- NVU_INTEGRATE_THINKING_TIMEOUT_S=90
- NVU_PEXEC_TIMEOUT_FASTBREAK=1
- NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
- NVU_EMPTY_200_FASTBREAK=2
- NVU_TIER_BUDGET_DSV4P_NV=72
- NVU_TIER_BUDGET_GLM5_2_NV=96
- NVU_TIER_BUDGET_MINIMAX_M3_NV=100
- NVU_MS_GW_FALLBACK_TIMEOUT=200
- NVU_PEER_FALLBACK_TIMEOUT=66
- NVU_PEER_FB_SKIP_MODELS=（空）
- NVU_FALLBACK_HEALTH_THRESHOLD=0.05
- MIN_OUTBOUND_INTERVAL_S=0
- NVU_CONNECT_RESERVE_S=0
- NVU_FORCE_STREAM_UPGRADE=0
- NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66

## 决策: NOP

**理由**: 所有 21 次失败均为 code-level 信号，无可配置参数改善：

1. **zombie_empty_completion (17)**: glm5_2_nv integrate，NVCF content-filter stop+12chars，input_chars ~170K avg。Gateway 正确检测+abort（3-15s 快速失败 vs 旧 96s hang）。code-level zombie detection feature，非 config-fixable（R1107 诊断）。

2. **all_tiers_exhausted (3)**: upstream_type=NULL（ATE），tiers_tried_count=1，avg_dur=5,449ms。fallback_actually_attempted=false — glm5_2_nv single-tier 无法救回。非 config-fixable。

3. **NVStream_IncompleteRead (1)**: NVCF 流中断，非 config-fixable。

**全部参数已处于 floor/optimal**。ms_gw 日志显示正常（MS-STREAM-DONE for glm5_2），无需 ms_gw 侧优化。dsv4p_nv 100% SR。零参数变更。

铁律: 只改 HM1 不改 HM2.

## ⏳ 轮到HM1优化HM2
