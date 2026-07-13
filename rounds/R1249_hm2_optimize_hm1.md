# HM2 Optimize HM1 — Round R1249

## 触发分析
- cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 GitHub commit: 308f02a (R1248: cleanup — add previously untracked CLAUDE.md.bak.pre-R1245)
- R1248 为 HM2 自提交 (NOP false trigger)
- 判定: **FALSE TRIGGER** — 误触发

## 数据收集 (改前必有数据)

### 容器状态
- 容器: nv_gw, Up 46 minutes (healthy)
- 重启时间: 2026-07-13T14:33:57Z (与 R1248 相同, 无新重启)
- compose md5: 6e23559de1376d2d638f98f34a544139 (与 R1248 相同, 连续 2 轮不变)

### 6h 总体
- 111req/89OK/22fail=80.2% SR (R1248: 79.5%, 几乎一致)

### 6h 错误分解
| error_type | cnt |
|---|---|
| zombie_empty_completion | 18 |
| all_tiers_exhausted | 3 |
| NVStream_IncompleteRead | 1 |

### 6h 按模型
| model | cnt | ok | fail | sr_pct | avg_dur |
|---|---|---|---|---|---|
| glm5_2_nv | 107 | 85 | 22 | 79.4% | 21086ms |
| dsv4p_nv | 4 | 4 | 0 | 100.0% | 28308ms |

### 6h 按 upstream
| upstream_type | cnt | ok | fail | avg_ttfb | avg_dur | max_dur |
|---|---|---|---|---|---|---|
| nv_integrate | 99 | 81 | 18 | 18085 | 19590 | 86107 |
| nvcf_pexec | 9 | 8 | 1 | 45960 | 45961 | 137213 |
| (NULL) | 3 | 0 | 3 | 767 | 5449 | 7524 |

### 6h hourly SR
| hour (UTC) | total | ok | fail | sr_pct |
|---|---|---|---|---|
| 09:00 | 17 | 15 | 2 | 88.2% |
| 10:00 | 42 | 33 | 9 | 78.6% |
| 11:00 | 8 | 6 | 2 | 75.0% |
| 12:00 | 27 | 22 | 5 | 81.5% |
| 13:00 | 6 | 5 | 1 | 83.3% |
| 14:00 | 8 | 6 | 2 | 75.0% |
| 15:00 | 3 | 2 | 1 | 66.7% |

### zombie_empty_completion 详情 (最近 10 条)
- 全部 glm5_2_nv integrate, input_chars 109K-172K, output_tokens 6-18
- 持续时间 3972-37413ms (中位数 ~7.4s)
- 代码级 zombie 检测功能 (R1107 引入) — 快速中断 ≥ 旧 96s 超时等待

### all_tiers_exhausted 详情 (3 条)
- 全部 glm5_2_nv, 单 tier (tiers_tried_count=1), fallback_actually_attempted=false
- 持续时间 3845-7524ms (中位数 4978ms)
- 特征: upstream_type=NULL → 404 NVCF DEGRADED (R1241 pattern)
- tier_chain=['glm5_2_nv'] (no fallback, 3model) — FALLBACK_GRAPH={} 预期状态

### ms_gw 信号
- 6req/0OK (BrokenPipeError, 连续 2 轮)
- ms_gw 日志: glm5_2_ms 正常流式成功 (MS-STREAM-DONE), dsv4p_ms BrokenPipeError
- 非 nv_gw fallback 触发 — 0 fallback_occurred 在 nv_requests

### tier_attempts
- 仅 2 条 IntegrateTimeout (glm5_2_nv, avg 90.8s, max 91.1s)
- 0 pexec 错误, 0 NVCFPexecTimeout, 0 SSLEOFError

### nv_gw 日志 (tail 100)
- 活跃: 5 条 NV-INTEGRATE-SUCCESS (k1-k5 轮流, 8-20s 完成)
- 1 条 NV-ZOMBIE-EMPTY + NV-ZOMBIE-ERROR-CHUNK (zombie 检测+中断)
- 0 NV-TIER-FAIL, 0 NV-MS-FB, 0 NV-EMPTY-FASTBREAK
- tier_chain: 全部 `['glm5_2_nv']` (no fallback, 3model) — 预期状态

### env 关键参数
| 参数 | 值 | 状态 |
|---|---|---|
| UPSTREAM_TIMEOUT | 66 | floor |
| TIER_TIMEOUT_BUDGET_S | 210 | 充裕 |
| TIER_COOLDOWN_S | 15 | floor |
| KEY_COOLDOWN_S | 25 | floor |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | defensive |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | optimal |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | optimal |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal |
| NVU_MS_GW_FALLBACK_TIMEOUT | 200 | generous |
| NVU_PEER_FB_SKIP_MODELS | (empty) | peer-fb enabled |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | floor |

## 决策

**NOP — 零参数变更, 零 compose 编辑, 零容器重启.**

所有 22 个失败均为代码级/上游级, 无可配置参数修复:
1. **18 zombie_empty_completion**: 代码级 zombie 检测功能 (R1107), 快速中断 3-37s 优于旧 96s 超时. 功能正确, 无参数可影响.
2. **3 all_tiers_exhausted**: 404 NVCF DEGRADED (R1241 pattern), NVCF glm5_2 函数间歇返回 404. NVCF 侧问题, 不可配置修复. NONCYCLE 正确 (不浪费 key cycling).
3. **1 NVStream_IncompleteRead**: 网络级错误, 不可配置修复.
4. **ms_gw 6req/0OK**: BrokenPipeError 流式同步缺陷, 代码级, 不可��置修复.

所有参数在 floor/optimal. BUDGET=210 充裕. compose md5 连续 2 轮不变. 数据与 R1248 高度一致 (80.2% vs 79.5% SR, 相同错误模式). 无 peer-fallback 或 ms_gw-fallback 触发.

铁律: 只改 HM1 不改 HM2.

## ⏳ 轮到HM1优化HM2
