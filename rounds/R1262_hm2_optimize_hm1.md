# HM2 Optimize HM1 — Round R1262

**Date**: 2026-07-14
**Author**: opc2_uname (HM2)
**Role**: HM2 → HM1 optimization

## 1. 触发分析

cron 脚本输出:
```
这是我提交的, 不触发
```

- 最新 commit author = opc2_uname (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发/双派遣 (false trigger / double-dispatch)
- R1261 已由预运行脚本提交 (da46e9a)

## 2. 数据收集 (改前必有数据)

### 2.1 6h 总体
- **59req/45OK/14fail = 76.3% SR** (与 R1261 完全一致)

### 2.2 错误分类 (14 failures)
| 错误类型 | 数量 | 模型 | 说明 |
|----------|------|------|------|
| zombie_empty_completion | 10 | glm5_2_nv | NVCF content-filter stop+12chars, avg 15,494ms, avg input 168,886 chars |
| all_tiers_exhausted | 3 | glm5_2_nv | 快速 ATE, avg 5,449ms |
| NVStream_IncompleteRead | 1 | glm5_2_nv | 24,019ms |

### 2.3 按模型
| 模型 | 请求 | OK | 失败 | SR | avg_dur |
|------|------|-----|------|------|---------|
| glm5_2_nv | 58 | 44 | 14 | 75.9% | 15,739ms |
| dsv4p_nv | 1 | 1 | 0 | 100% | 45,950ms |

### 2.4 按上游类型
| 类型 | 请求 | OK | 失败 | avg_ttfb | avg_dur |
|------|------|-----|------|----------|---------|
| nv_integrate | 52 | 41 | 11 | 14,696ms | 16,207ms |
| nvcf_pexec | 4 | 4 | 0 | 24,938ms | 24,939ms |
| (fallback) | 3 | 0 | 3 | 767ms | 5,449ms |

### 2.5 小时级 SR
| 小时 (UTC) | 请求 | OK | 失败 | SR |
|------------|------|-----|------|------|
| 12:00 | 27 | 22 | 5 | 81.5% |
| 13:00 | 6 | 5 | 1 | 83.3% |
| 14:00 | 8 | 6 | 2 | 75.0% |
| 15:00 | 6 | 4 | 2 | 66.7% |
| 16:00 | 6 | 4 | 2 | 66.7% |
| 17:00 | 6 | 4 | 2 | 66.7% |

### 2.6 Fallback
- fallback_occurred: false (全部 59 请求)
- tiers_tried_count: 1 (全部 14 失败)
- 0 fallback 触发 — 所有请求走 tier_chain=['glm5_2_nv'] (no fallback, 3model)

### 2.7 Tier Attempts
- nv_tier_attempts: 0 rows (僵尸检测在 key 耗尽前发生)

### 2.8 ms_gw
- ms_requests: 5 total, 0 ok (ms_gw 不写 DB — log-only 模式)
- ms_gw logs: MS-OK-STREAM + MS-STREAM-DONE 正常 (ZHIPUAI/GLM-5.2 + deepseek-ai/DEEPSEEK-V4-PRO)

### 2.9 容器状态
- nv_gw: Up 3 hours (healthy), restarted 2026-07-13T14:33:57Z
- compose md5: 6e23559de1376d2d638f98f34a544139 (unchanged)

### 2.10 关键参数 (全部 floor/optimal)
| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | floor |
| TIER_TIMEOUT_BUDGET_S | 210 | optimal |
| TIER_COOLDOWN_S | 15 | floor |
| KEY_COOLDOWN_S | 25 | floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | floor |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | optimal |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal |
| NVU_MS_GW_FALLBACK_TIMEOUT | 200 | optimal |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | optimal |
| NVU_PEER_FB_SKIP_MODELS | (empty) | optimal |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | defensive |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | floor |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | dead param |

## 3. 分析

### 3.1 zombie_empty_completion (10/14 = 71.4% of failures)
- 全部 glm5_2_nv integrate, NVCF content-filter 返回 stop+12chars
- 网关正确检测并 abort (NV-ZOMBIE-EMPTY + NV-ZOMBIE-ERROR-CHUNK)
- 3-15s 快速 abort vs 旧 96s hang — 代码级改善
- **代码级特性，不可配置修复** — NOP

### 3.2 all_tiers_exhausted (3/14 = 21.4%)
- 全部 glm5_2_nv, avg 5,449ms 快速 ATE
- 可能原因: 所有 key 在 cooldown 或 NVCF 404
- **代码级/上游问题，不可配置修复** — NOP

### 3.3 NVStream_IncompleteRead (1/14 = 7.1%)
- glm5_2_nv, 24,019ms
- 网络层中断，非配置问题
- **代码级，不可配置修复** — NOP

### 3.4 ms_gw 健康
- MS-STREAM-DONE 正常
- 无配置瓶颈

## 4. 决策: NOP

**Zero param change. Zero config change. Zero container restart.**

理由:
1. 所有 14 个失败均为代码级 (zombie 检测 + NVCF 上游 + 网络中断)
2. 所有参数已处于 floor/optimal — 无优化空间
3. compose md5 未变化
4. 铁律: 只改 HM1 不改 HM2

## ⏳ 轮到HM1优化HM2
