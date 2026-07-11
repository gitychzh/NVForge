# HM2 Optimize HM1 — Round R1200

## 1. 触发分析
- 脚本输出: `[2026-07-11 17:50:34] 这是我提交的, 不触发`
- 最新 commit: 84fb530 (R1199, opc2_uname) — HM2 自提交
- 判断: R1199 是 false trigger (68th chain of R1133 zombie-only)。脚本检测到 HM1 有新 commit 才触发 R1200 (正确触发)。

## 2. 本轮数据收集 (改前必有数据)

### 2.1 nv_gw 6h 总体 (11:00-17:50 UTC)
```
total | ok  | fail | avg_ttfb | avg_dur | max_dur
   31 |  19 |   12 |     7188 |    7744 |   38540
```
SR: 19/31 = **61.3%** (vs R1199: 31/19=61.3%, identical)

### 2.2 按上游路径
| upstream_type | cnt | ok | avg_ttfb | avg_dur |
|---|---|---|---|---|
| nv_integrate | 31 | 19 | 7188 | 7744 |

### 2.3 错误类型
| error_type | cnt | 说明 |
|---|---|---|
| zombie_empty_completion | 12 | code-level zombie detection (glm5_2_nv integrate, NVCF content-filter stop+12chars) |

### 2.4 最新日志 (15:03-17:41 UTC)
```
[15:03:35] glm5_2_nv integrate k4 -> SUCCESS (2.9s)
[15:03:41] ZOMBIE-EMPTY: content_chars=12 < 50, input_chars=173078 >= 5000 -> abort 2.6s ✓
[15:33:24] glm5_2_nv integrate k5 -> SUCCESS (32.4s)
[15:34:09] glm5_2_nv integrate k1 -> SUCCESS (2.7s)
[15:34:14] ZOMBIE-EMPTY: content_chars=12 < 50, input_chars=173773 -> abort 2.5s ✓
[16:03:24] glm5_2_nv integrate k2 -> SUCCESS (4.3s)
[16:03:40] glm5_2_nv integrate k3 -> SUCCESS (2.0s)
[16:03:45] ZOMBIE-EMPTY: content_chars=12 < 50, input_chars=174364 -> abort 2.4s ✓
[16:33:24] glm5_2_nv integrate k4 -> SUCCESS (3.1s)
[16:33:39] glm5_2_nv integrate k5 -> SUCCESS (2.3s)
[16:33:50] ZOMBIE-EMPTY: content_chars=12 < 50, input_chars=174874 -> abort 2.3s ✓
[17:03:24] glm5_2_nv integrate k1 -> SUCCESS (1.9s)
[17:03:35] glm5_2_nv integrate k2 -> SUCCESS (4.4s)
[17:03:41] ZOMBIE-EMPTY: content_chars=12 < 50, input_chars=175650 -> abort 2.0s ✓
[17:33:24] glm5_2_nv integrate k3 -> SUCCESS (2.6s)
[17:33:34] glm5_2_nv integrate k4 -> SUCCESS (2.3s)
[17:33:38] ZOMBIE-EMPTY: content_chars=12 < 50, input_chars=176160 -> abort 2.2s ✓
[17:40:07] glm5_2_nv integrate k5 -> SUCCESS (1.8s)
[17:40:15] glm5_2_nv integrate k1 -> SUCCESS (2.3s)
[17:40:32] glm5_2_nv integrate k2 -> SUCCESS (1.2s)
[17:40:36] glm5_2_nv integrate k3 -> SUCCESS (5.5s)
[17:40:45] glm5_2_nv integrate k4 -> SUCCESS (1.6s)
[17:40:51] glm5_2_nv integrate k5 -> SUCCESS (3.9s)
[17:41:02] glm5_2_nv integrate k1 -> SUCCESS (4.0s)
```

### 2.5 容器状态
- 容器: nv_gw, Up 15 hours (healthy)
- 重启时间: 2026-07-10T19:03:27Z (15h+ ago)
- tier_chain: `['glm5_2_nv'] (no fallback, 3model)` — expected (FALLBACK_GRAPH={})
- dsv4p_nv: 0 traffic 22h+ (6h zero)
- ms_gw: 0 traffic 6h
- nv_tier_attempts: 0 rows (no per-key failures)

## 3. 故障分析

### 3.1 zombie_empty_completion (12×, code-level)
- 代码级僵尸检测: finish_reason=stop, content_chars=12 < 50, input_chars=173K-176K >= 5000, no tool_calls
- NVCF content-filter 返回 stop+12chars — 上游模型内容过滤
- Gateway检测机制正确: 2-3s 快速 abort (vs 旧版 96s NVStream_TimeoutError hang)
- 日志: `[NV-ZOMBIE-EMPTY]` + `[NV-ZOMBIE-ERROR-CHUNK]` → 触发 openclaw fallback
- **不可配置修复** — 无网关参数可阻止 NVCF content-filter 返回空内容

### 3.2 零非 zombie 错误
- 0 NV-TIER-FAIL
- 0 GLOBAL-COOLDOWN
- 0 FASTBREAK 触发
- 0 NVCFPexecTimeout
- 0 all_tiers_exhausted
- 0 stream timeout
- 0 ms_gw BrokenPipeError
- 0 dsv4p_nv 流量

## 4. 参数状态 (全部处于最优值/floor)

| 参数 | 当前值 | 状态 | 注 |
|---|---|---|---|
| UPSTREAM_TIMEOUT | 66 | floor | R988 +2s buffer |
| TIER_TIMEOUT_BUDGET_S | 198 | generous | R1088 |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor | R638 |
| KEY_COOLDOWN_S | 25 | floor | R162 |
| TIER_COOLDOWN_S | 15 | floor | R1103 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor | R997 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor | R1010 |
| NVU_EMPTY_200_FASTBREAK | 2 | R1031 (R1039 bug: pexec path不honor) | code-level |
| NVU_CONNECT_RESERVE_S | 0 | floor | R657 |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | floor | R543 |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | per-tier | R1116 |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | per-tier | |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | per-tier | R1035 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 | generous | R1036/R1088 |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | matches UPSTREAM | R697 |
| NVU_PEER_FALLBACK_ENABLED | 1 | enabled | |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | R923 | |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | floor | R839 |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | floor | |
| NVU_FORCE_STREAM_UPGRADE | 0 | disabled | R692 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | matches UPSTREAM | R988 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor | R631 |

## 5. 决策: NOP

**理由:**
- 数据与 R1199 完全一致 (31req/19OK/12zombie=61.3% SR)
- 100% 失败为 zombie_empty_completion — 代码级 NVCF content-filter，非配置可修复
- 0 非 zombie 错误: 0 NV-TIER-FAIL, 0 GLOBAL-COOLDOWN, 0 FASTBREAK, 0 tier_attempts
- dsv4p_nv 0 流量 22h+ (无流量即无错误)
- ms_gw 0 流量 6h
- 所有参数地板/最优值
- HM1 git 仍停在 R821 (378 rounds behind, 2026-07-08)
- NVCF content-filter stop+12chars 是上游行为，网关无参数可阻止
- 铁律: 只改HM1不改HM2

**Zero param changes.**
**Iron rule: only change HM1 never HM2.**

## ⏳ 轮到HM1优化HM2
