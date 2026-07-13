# HM2 Optimize HM1 — Round R1264

**Date**: 2026-07-14
**Author**: opc2_uname (HM2)
**Role**: HM2 → HM1 optimization

## 1. 触发分析

```
From github.com:gitychzh/NVForge
HEAD is now at 162325e R1263: HM2→HM1 — NOP (false trigger, double-dispatch, zombie+ATE+IncompleteRead, 76.3% SR all code-level failures)
[2026-07-14 02:00:14] 这是我提交的, 不触发
```

- 最新 commit author = opc2_uname (HM2)
- R1263 已由 HM2 提交 (162325e)
- 脚本检测到自提交并标记"不触发"，但 cron 仍被派遣 → 误触发/双派遣 (false trigger / double-dispatch)

## 2. 数据收集 (改前必有数据)

### 2.1 6h 总体 (DB: nv_requests)
- **61req/47OK/14fail = 77.0% SR** (与 R1263 的 76.3% 在统计误差范围内)
- 窗口: 2026-07-13 12:00 UTC → 2026-07-14 02:00 UTC (nv_gw 重启于 2026-07-13T14:33Z)

### 2.2 错误分类 (14 failures)
| 错误类型 | 数量 | 模型 | 说明 |
|----------|------|------|------|
| zombie_empty_completion | 10 | glm5_2_nv | NVCF content-filter stop+12chars, avg 15,494ms, max 37,413ms |
| all_tiers_exhausted | 3 | glm5_2_nv | 快速 ATE, avg 5,449ms, 0 fallback 触发 |
| NVStream_IncompleteRead | 1 | glm5_2_nv | 24,019ms, 网络层中断 |

### 2.3 按模型
| 模型 | 请求 | OK | 失败 | SR | avg_dur |
|------|------|-----|------|------|---------|
| glm5_2_nv | 58 | 44 | 14 | 75.9% | 15,739ms |
| dsv4p_nv | 3 | 3 | 0 | 100% | 38,926ms |

### 2.4 按上游类型
| 类型 | 请求 | OK | 失败 | avg_dur |
|------|------|-----|------|---------|
| nv_integrate | 52 | 41 | 11 | 16,207ms |
| nvcf_pexec | 6 | 6 | 0 | 28,430ms |
| (fallback/ATE) | 3 | 0 | 3 | 5,449ms |

### 2.5 按 Key 分布
| 模型 | Key | 请求 | OK | SR | avg_ms |
|------|-----|------|-----|------|--------|
| glm5_2_nv | k1 | 12 | 11 | 91.7% | 17,435ms |
| glm5_2_nv | k2 | 12 | 9 | 75.0% | 18,547ms |
| glm5_2_nv | k3 | 13 | 11 | 84.6% | 15,910ms |
| glm5_2_nv | k4 | 9 | 7 | 77.8% | 17,453ms |
| glm5_2_nv | k5 | 9 | 6 | 66.7% | 11,206ms |
| glm5_2_nv | (ATE) | 3 | 0 | 0% | 5,449ms |
| dsv4p_nv | k1 | 1 | 1 | 100% | 15,910ms |
| dsv4p_nv | k2 | 1 | 1 | 100% | 54,918ms |
| dsv4p_nv | k5 | 1 | 1 | 100% | 45,950ms |

### 2.6 小时级 SR
| 小时 (UTC) | 请求 | OK | 失败 | SR |
|------------|------|-----|------|------|
| 12:00 | 27 | 22 | 5 | 81.5% |
| 13:00 | 6 | 5 | 1 | 83.3% |
| 14:00 | 8 | 6 | 2 | 75.0% |
| 15:00 | 6 | 4 | 2 | 66.7% |
| 16:00 | 6 | 4 | 2 | 66.7% |
| 17:00 | 6 | 4 | 2 | 66.7% |
| 18:00 | 2 | 2 | 0 | 100% |

### 2.7 Fallback
- fallback_occurred: false (全部 61 请求)
- tiers_tried_count: 1 (全部 14 失败)
- 0 fallback 触发 — 所有请求走 tier_chain=['glm5_2_nv'] (no fallback, 3model)

### 2.8 Tier Attempts
- nv_tier_attempts: 0 rows (僵尸检测在 key 耗尽前发生，无 key 级失败记录)

### 2.9 nv_gw 日志 (23:00–02:00 UTC, last 100 lines)
- 全部 glm5_2_nv integrate: NV-INTEGRATE-SUCCESS on first attempt (k1-k5 轮转正常)
- 全部 dsv4p_nv pexec: NV-SUCCESS on first attempt
- 5× zombie detection: NV-ZOMBIE-EMPTY + NV-ZOMBIE-ERROR-CHUNK (content_filter stop+12chars, 171K-182K input)
- 0 NV-TIER-FAIL, 0 NV-ALL-TIERS-FAIL, 0 NV-MS-FB, 0 NV-PEER-FB
- 0 NV-GLOBAL-COOLDOWN, 0 NV-NONCYCLE-ERR
- 0 429, 0 SSLEOF, 0 404

### 2.10 容器状态
- nv_gw: Up 3 hours (healthy), restarted 2026-07-13T14:33:57Z
- ms_gw: Up 8 hours (healthy)
- logs_db: Up 8 hours (healthy)
- compose md5: unchanged

### 2.11 关键参数 (全部 floor/optimal)
| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | floor |
| TIER_TIMEOUT_BUDGET_S | 210 | optimal |
| TIER_COOLDOWN_S | 15 | floor |
| KEY_COOLDOWN_S | 25 | floor |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | defensive |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | floor |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | optimal |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | optimal |
| NVU_MS_GW_FALLBACK_TIMEOUT | 200 | optimal |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | optimal |
| NVU_PEER_FB_SKIP_MODELS | (empty) | optimal |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | floor |
| NVU_FORCE_STREAM_UPGRADE | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | defensive |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | defensive |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | defensive |

## 3. 分析

### 3.1 zombie_empty_completion (10/14 = 71.4% of failures)
- 全部 glm5_2_nv integrate, NVCF content-filter 返回 stop+12chars
- 网关正确检测并 abort (NV-ZOMBIE-EMPTY + NV-ZOMBIE-ERROR-CHUNK)，3-15s 快速 abort
- 输入量持续增长 (171K→182K chars)，说明 openclaw 长对话累积
- **代码级特性，不可配置修复** — NOP

### 3.2 all_tiers_exhausted (3/14 = 21.4%)
- 全部 glm5_2_nv, avg 5,449ms 快速 ATE
- 0 nv_tier_attempts 行 (无 key 级失败记录) — 说明 zombie 检测在 key 耗尽前触发
- 0 fallback 触发 (tiers_tried_count=1) — 快速 ATE 未触发 ms_gw/peer-fb
- **代码级/上游问题，不可配置修复** — NOP

### 3.3 NVStream_IncompleteRead (1/14 = 7.1%)
- glm5_2_nv, 24,019ms
- 网络层中断，非配置问题
- **代码级，不可配置修复** — NOP

### 3.4 nv_gw 实时日志 (23:00–02:00 UTC)
- 操作完全正常: 全部 glm5_2_nv integrate NV-INTEGRATE-SUCCESS on first attempt
- 全部 dsv4p_nv pexec NV-SUCCESS on first attempt
- 5× zombie 正确检测 (代码级)
- 0 任何 tier 级失败 (0 NV-TIER-FAIL, 0 NV-ALL-TIERS-FAIL)
- 0 nv_tier_attempts 行 (无 key 级失败)

### 3.5 配置状态
- 所有参数已处于 floor/optimal — 无优化空间
- All FASTBREAK at floor — PEXEC=1, INTEGRATE=1, EMPTY_200=2
- All tier budgets optimal — DSV4P=72, GLM5_2=96, MINIMAX=100
- Peer-fb enabled, skip_models empty

## 4. 决策: NOP

**Zero param change. Zero config change. Zero container restart.**

理由:
1. 所有 14 个失败均为代码级 (zombie 检测 + NVCF 上游 + 网络中断)
2. 所有参数已处于 floor/optimal — 无优化空间
3. 实时日志完美: 全部请求 first-attempt 成功
4. compose md5 未变化
5. 铁律: 只改 HM1 不改 HM2
6. 本轮为 false trigger (HM2 自提交 R1263 被调度)

## ⏳ 轮到HM1优化HM2