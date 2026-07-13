# HM2 Optimize HM1 — Round R1258

## ⚠️ 触发分析
cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2)
- 最新 commit: R1257 (NOP, 同模式)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch)
- HM1 容器 nv_gw Up 3 hours (restart at 2026-07-13T14:33:57Z)

## 📊 HM1 6h 数据 (2026-07-13 22:00~2026-07-14 04:00 UTC)

### 总体
- 60req / 46OK / 14fail = **76.7% SR**
- 全部失败为代码级错误: 10 zombie_empty_completion + 3 all_tiers_exhausted + 1 NVStream_IncompleteRead

### 按模型
| 模型 | 请求数 | OK | 失败 | SR | avg_dur |
|------|--------|----|----|----|--------|
| glm5_2_nv | 59 | 45 | 14 | 76.3% | 15816ms |
| dsv4p_nv | 1 | 1 | 0 | 100.0% | 45950ms |

### 按路���
| 路径 | 请求数 | OK | 失败 | avg_ttfb | avg_dur |
|------|--------|----|----|--------|--------|
| nv_integrate | 53 | 42 | 11 | 14698ms | 16283ms |
| nvcf_pexec | 4 | 4 | 0 | 24938ms | 24939ms |
| (NULL/ATE) | 3 | 0 | 3 | 767ms | 5449ms |

### 错误分类
| 错误类型 | 计数 | 说明 |
|----------|------|------|
| zombie_empty_completion | 10 | glm5_2_nv integrate, NVCF content-filter stop, 163K avg input, ~15.7s avg |
| all_tiers_exhausted | 3 | glm5_2_nv, ~5.4s avg (fast ATE abort) |
| NVStream_IncompleteRead | 1 | glm5_2_nv, ~24s |

### 关键指标
- fallback_occurred=f: 60/60 (100%) — FALLBACK_GRAPH={} intentionally empty per R832 design
- key_cycle_429s: 0 (全部模型)
- tier_attempts: 0 rows — 无 key 级失败
- ms_gw_signal: 5 total, 0 OK (nv_gw ms_gw fallback 未触发或 ms_gw 未记录)
- ms_gw logs: MS-OK-STREAM + MS-STREAM-DONE 正常 (ZHIPUAI/GLM-5.2, deepseek-ai/DEEPSEEK-V4-PRO)
- zombie count (logs): 10 (与 DB 一致)
- tier_chain: `['glm5_2_nv'] (no fallback, 3model)` — R832 预期正常状态
- NV-MS-FB: 0 lines — ms_gw fallback 未触发 (zombie 在 NVCF 层检测，不经过 ms_gw)

### 容器 env (关键参数)
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=210
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_TIER_BUDGET_DSV4P_NV=72
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_MS_GW_FALLBACK_TIMEOUT=200
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_PEER_FB_SKIP_MODELS=
NVU_CONNECT_RESERVE_S=0
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
```
compose_md5=6e23559de1376d2d638f98f34a544139 (与 R1257 相同)

## 🎯 决策: NOP — Zero Change

### 数据分析
1. **zombie_empty_completion (10/14=71.4%)**: glm5_2_nv integrate, NVCF content-filter 触发 stop+12chars, 163K avg input. 网关正确检测并发送 error SSE chunk 触发 openclaw fallback (R1107 代码级 zombie detection). **不可配置修复** — NVCF 上游行为，非 nv_gw 配置问题。
2. **all_tiers_exhausted (3/14=21.4%)**: glm5_2_nv, ~5.4s avg duration — 快速 ATE (非 zombie 模式). 0 tier_attempts 确认无 key 级循环。FALLBACK_GRAPH={} per R832 设计，ms_gw fallback 应触发但 ms_gw signal 显示 0 OK。**代码级问题** — 非配置可修复。
3. **NVStream_IncompleteRead (1/14=7.1%)**: 流中断，NVCF 侧连接断开。**代码级问题**。
4. **dsv4p_nv 100% SR (1/1)**: 健康。
5. **所有参数已在 floor/optimal**: UPSTREAM=66, FASTBREAK=1, BUDGET=210, COOLDOWN=15, etc. 无进一步优化空间。
6. **ms_gw MS-STREAM-DONE 正常**: ms_gw 本身健康，zombie/ATE 失败不经过 ms_gw 路径。

### 铁律
- ✅ 只改 HM1 (本轮无改动)
- ✅ 改前必有数据 (已收集)
- ✅ 所有参数 floor/optimal

### 本轮: 零参数, 零 compose 改动, 零容器重启

## ⏳ 轮到HM1优化HM2
