# HM2 Optimize HM1 — Round R1201

## 1. 触发分析
- 脚本输出: `[2026-07-11 18:00:35] 这是我提交的, 不触发`
- 最新 commit: e55dc1d (R1200, opc2_uname) — HM2 自提交, 不触发
- 判断: 脚本检测到 HM1 有新 commit 才触发 R1201 (正确触发)。R1200 是 NOP (68th chain of R1133 zombie-only)。

## 2. 本轮数据收集 (改前必有数据)

### 2.1 nv_gw 6h 总体 (12:00-18:00 UTC)
```
total | ok  | fail | avg_ttfb | avg_dur | max_dur | p50 | p95
   31 |  19 |   12 |     7216 |    7772 |   38540 | 5500 | 18450
```
SR: 19/31 = **61.3%** (vs R1200: 31/19=61.3%, identical)

### 2.2 按上游路径
| upstream_type | cnt | ok | avg_ttfb | avg_dur |
|---|---|---|---|---|
| nv_integrate | 31 | 19 | 7216 | 7772 |

### 2.3 按模型
| request_model | cnt | ok | fail | avg_ttfb | avg_dur |
|---|---|---|---|---|---|
| glm5_2_nv | 31 | 19 | 12 | 7216 | 7772 |
| dsv4p_nv | 0 | 0 | 0 | - | - |
| kimi_nv | 0 | 0 | 0 | - | - |

### 2.4 错误类型
| error_type | cnt | 说明 |
|---|---|---|
| zombie_empty_completion | 12 | code-level zombie detection (glm5_2_nv integrate, NVCF content-filter stop+12chars) |

### 2.5 最新日志 (17:03-18:00 UTC, 截取关键)
```
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

### 2.6 容器状态
- 容器: nv_gw, Up ~18h (healthy)
- 51 NV-INTEGRATE-SUCCESS in last 300 log lines
- tier_chain: `['glm5_2_nv'] (no fallback, 3model)` — expected
- dsv4p_nv: 0 traffic (6h zero)
- kimi_nv: 0 traffic (6h zero)
- ms_gw: 0 traffic (6h zero)
- nv_tier_attempts: 0 rows (no per-key failures)
- key_cycle_429s: 0 (all requests)
- ATE: 0 (zero all_tiers_exhausted)

### 2.7 慢请求分析 (OK requests)
| duration_ms | ttfb_ms | 时间 |
|---|---|---|
| 38540 | 38540 | 07:33 UTC (thinking 38.5s, 在 90s 内) |
| 25258 | 4105 | 10:09 UTC (streaming 21s post-ttfb) |
| 25118 | 7912 | 09:41 UTC (streaming 17s post-ttfb) |
| 11782 | 11782 | 09:40 UTC |
| 10323 | 10322 | 08:03 UTC |

## 3. 故障分析

### 3.1 zombie_empty_completion (12×, code-level, 69th chain)
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
- 0 NVCFPexecSSLEEOFError
- 0 tier_attempts rows

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
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | generous | max OK=38.5s, well within |

## 5. 决策: NOP

**理由:**
- 数据与 R1200 完全一致 (31req/19OK/12zombie=61.3% SR)
- 100% 失败为 zombie_empty_completion — 代码级 NVCF content-filter，非配置可修复
- 0 非 zombie 错误: 0 NV-TIER-FAIL, 0 GLOBAL-COOLDOWN, 0 FASTBREAK, 0 tier_attempts
- dsv4p_nv 0 流量 6h (无流量即无错误)
- kimi_nv 0 流量 6h
- ms_gw 0 流量 6h
- 所有参数地板/最优值
- 最慢 OK 请求 38.5s thinking，在 NVU_INTEGRATE_THINKING_TIMEOUT_S=90 内
- NVCF content-filter stop+12chars 是上游行为，网关无参数可阻止
- 铁律: 只改HM1不改HM2

**Zero param changes.**
**Iron rule: only change HM1 never HM2.**
**69th chain of R1133 zombie-only.**

## ⏳ 轮到HM1优化HM2