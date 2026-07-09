# HM2 Optimize HM1 — Round R1014

> **Trigger**: False trigger (double-dispatch). Cron script: "这是我提交的, 不触发". R1013 already committed.
> **Date**: 2026-07-10 01:45 UTC
> **Decision**: NOP — all params at floor/optimal, no config-fixable issues.

## 1. 触发分析

- Cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit: `5ab16bb R1013: HM2→HM1 — NOP (false trigger, minimax_m3_nv NVCF degraded, all params floor/optimal)`
- 最新 commit author: opc2_uname (HM2自身)
- Symlink `RN_hm2_optimize_hm1.md` → `rounds/R1013_hm2_optimize_hm1.md` (已指向最新)
- 结论: **DOUBLE-DISPATCH false trigger** — R1013 已提交并推送，cron 再次派遣 agent

## 2. 改前数据 (HM1 nv_gw, 6h window)

### 2.1 总体
| 指标 | 6h | 1h |
|------|-----|-----|
| 总请求 | 241 | 74 |
| 成功 | 220 (91.3%) | 66 (89.2%) |
| 失败 | 21 (8.7%) | 8 (10.8%) |

### 2.2 按 tier 分解
| Tier | Total | OK | Err | SR | Avg Lat | Max Lat |
|------|-------|-----|-----|------|---------|---------|
| glm5_2_nv | 132 | 126 | 6 | 95.5% | 25,989ms | 129,132ms |
| dsv4p_nv | 66 | 57 | 9 | 86.4% | 38,522ms | 139,999ms |
| kimi_nv | 24 | 24 | 0 | 100.0% | 15,586ms | 71,985ms |
| minimax_m3_nv | 19 | 13 | 6 | 68.4% | 16,911ms | 75,345ms |

### 2.3 按 upstream 分解
| Tier | Upstream | Total | OK |
|------|----------|-------|-----|
| dsv4p_nv | nvcf_pexec | 42 | 42 |
| dsv4p_nv | nv_integrate | 15 | 15 |
| dsv4p_nv | NULL (ATE) | 9 | 0 |
| glm5_2_nv | nv_integrate | 118 | 118 |
| glm5_2_nv | NULL (ATE) | 14 | 8 |
| minimax_m3_nv | nv_integrate | 12 | 12 |
| minimax_m3_nv | NULL (ATE) | 7 | 1 |
| kimi_nv | nvcf_pexec | 24 | 24 |

### 2.4 ATE 分解
| tiers_tried_count | cnt | avg_dur |
|-------------------|-----|---------|
| 1 | 21 | 137,867ms |

**All 21 ATEs**: single-tier, `fallback_actually_attempted=false`, `all_tiers_failed_in_mapped_tier`

### 2.5 ATE by tier
- **dsv4p_nv (9 ATEs)**: 8 at ~112,050ms (BUDGET=112 bound exactly), 1 at 60,960ms (empty_200)
- **glm5_2_nv (6 ATEs)**: 129-208s, NVU_TIER_BUDGET_GLM5_2_NV=96 but durations far exceed it
- **minimax_m3_nv (6 ATEs)**: 151-159s, NVCF degraded (empty_200 + timeout)

### 2.6 nv_tier_attempts
| Tier | Error Type | Count | Avg | Max |
|------|-----------|-------|-----|-----|
| dsv4p_nv | IntegrateTimeout | 14 | 56,021ms | 67,086ms |
| dsv4p_nv | NVCFPexecRemoteDisconnected | 1 | 9,134ms | 9,134ms |
| kimi_nv | empty_200 | 1 | — | — |

**NVCFPexecTimeout**: 0 instances. UPSTREAM=66 non-binding.

### 2.7 Fallback
| fallback_occurred | cnt | avg_dur |
|-------------------|-----|---------|
| f | 212 | 28,295ms |
| t | 8 | 8,205ms |

### 2.8 ms_gw
| 6h total | OK | Err | SR |
|----------|-----|-----|-----|
| 14 | 0 | 14 | 0.0% |

ms_gw: all 14 requests fail with BrokenPipeError on relay. ms_gw backend returns 200 OK but relay to nv_gw fails with `[Errno 32] Broken pipe`. ms_gw container healthy (Up 26 hours), 7 keys, 10 variants, all models available.

## 3. nv_gw 日志分析

```
[01:38:59.2] tier_chain=['dsv4p_nv'] (no fallback, 3model)
[01:38:59.2] tier_chain=['glm5_2_nv'] (no fallback, 3model)
[01:38:59.2] tier_chain=['kimi_nv'] (no fallback, 3model)
[01:38:59.2] tier_chain=['minimax_m3_nv'] (no fallback, 3model)
```

All tiers show `(no fallback, 3model)` — R832 design (FALLBACK_GRAPH={}). Local all-tiers-exhausted triggers peer fallback to HM2 (100.109.57.26:40006), but peer fallback also fails: `NV-PEER-FB peer connect/request failed after 45044ms: TimeoutError: timed out`. ms_gw fallback not attempted (logs show no `[NV-MS-FB]` entries).

Key minimax log: `[NV-TIER-FAIL] tier=minimax_m3_nv all 5 keys failed: 429=0, empty200=1, timeout=1, other=0` — cycling through all 5 keys despite NVU_EMPTY_200_FASTBREAK=1 and NVU_INTEGRATE_TIMEOUT_FASTBREAK=1. Code-level issue: FASTBREAK not working for minimax integrate.

## 4. HM1 当前参数

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | Non-binding (0 NVCFPexecTimeout) |
| TIER_TIMEOUT_BUDGET_S | 112 | Binding for dsv4p_nv batch (8 ATEs @112s) |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | Not enforced (ATEs 129-208s) |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | Floor ✓ |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | Floor ✓ |
| NVU_EMPTY_200_FASTBREAK | 1 | Floor ✓ |
| KEY_COOLDOWN_S | 25 | Floor ✓ |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | ✓ |
| TIER_COOLDOWN_S | 25 | Floor ✓ |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.10 | Floor ✓ |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | Floor ✓ |
| NVU_FORCE_STREAM_UPGRADE | 0 | Disabled ✓ |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | ✓ |
| MIN_OUTBOUND_INTERVAL_S | 0 | Floor ✓ |
| NVU_CONNECT_RESERVE_S | 0 | Floor ✓ |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv,dsv4p_nv | ✓ |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | ✓ |

## 5. 决策: NOP

### 5.1 为什么不能改
- **所有 FASTBREAK 参数已在 floor=1**: 无法进一步降低
- **UPSTREAM=66 non-binding**: 0 NVCFPexecTimeout，无需调整
- **TIER_TIMEOUT_BUDGET_S=112**: dsv4p_nv 的 8 ATEs 在 ~112s 是 BUDGET-bound，但根本原因是 NVCF 上游退化（那批 ATE 集中在 12:49-12:58 UTC），不是 config 问题。涨价不解决问题，降价会加速 ATE
- **minimax_m3_nv**: NVCF DEGRADED (empty_200 + timeout)，上游问题，非 config 可修复。FASTBREAK=1 理论上应 break after 1 key，但日志显示 cycling all 5 keys → code-level issue
- **ms_gw BrokenPipeError**: code-level relay 缺陷，非 config 可修复
- **所有 COOLDOWN/INTERVAL 参数在 floor**: 无法进一步降低

### 5.2 信号分类
| 信号 | 类型 | 可修复性 |
|------|------|---------|
| dsv4p_nv BUDGET-bound ATE (8) | NVCF 上游退化 | 不可修复 (config) |
| dsv4p_nv empty_200 ATE (1) | NVCF DEGRADED | 不可修复 (config) |
| glm5_2_nv ATE (6) | NVCF 上游退化 + budget 不执行 | 不可修复 (config) |
| minimax_m3_nv ATE (6) | NVCF DEGRADED | 不可修复 (config) |
| ms_gw BrokenPipeError | Code 缺陷 | 不可修复 (config) |
| FASTBREAK 不生效 (minimax) | Code 缺陷 | 不可修复 (config) |

### 5.3 铁律验证
- ✅ 改前必有数据: 完整 DB + logs 收集
- ✅ 聚焦 nv_gw: 仅分析 40006 链路
- ✅ 只改 HM1: 本轮无修改
- ✅ 所有修改写入仓库: 本轮 NOP

## ⏳ 轮到HM1优化HM2