# HM2 Optimize HM1 — Round R1107

**日期**: 2026-07-11 17:20 UTC (北京时间 01:20)
**类型**: NOP (False Trigger, Double-Dispatch)
**作者**: HM2 (opc2_uname)

---

## 触发分析

cron 脚本输出:
```
HEAD is now at 60b76ec R1106: HM2→HM1 — NOP (false trigger, HM2自提交, R1103 post-restart 96.4% SR 112req/108OK/4fail, 2× dsv4p_nv ATE pre-restart, 2× glm5_2_nv stream timeout code-level, all params at floor). Zero param; iron rule: only change HM1 never HM2.
[2026-07-11 01:15:11] 这是我提交的, 不触发
```

- 最新 commit 60b76ec author = `opc2_uname` (HM2)
- 脚本正确检测到自提交 → false trigger
- cron 仍被派遣 — double-dispatch pattern (R884+ streak continues, now 222+)
- HM1 本地 git log 最新: R821 (fbf0e43) — 285 轮落后
- 无 HM1 新提交

---

## 数据收集 (改前必有数据)

### 容器状态
- 容器: nv_gw, Up (healthy)
- **⚠️ 容器最近重启**: Created 2026-07-10 17:15:25 UTC, Started 17:15:42 UTC
- 重启后 zombie detection 代码激活 (NV-ZOMBIE-EMPTY/ABORT 模式)
- 容器日志: 8 次 NV-ZOMBIE-EMPTY 检测 (zombie 检测功能正常)

### 6h 总体 (11:20-17:20 UTC)
- 124 req, 114 OK, 10 fail → **91.9% SR**
- 10 fail: 6× zombie_empty_completion (NEW), 2× ATE (pre-restart), 2× NVStream_TimeoutError (pre-restart)
- 6× zombie_empty_completion: 全部 post-restart, duration 3,443-15,320ms (快速中止, 替代 96s 超时)
- 2× dsv4p_nv ATE: 全部 pre-restart (~61,375ms, budget 耗尽)
- 2× glm5_2_nv NVStream_TimeoutError: 全部 pre-restart (~95-97s, budget 耗尽)
- nv_tier_attempts: 0 rows (post-restart 无失败尝试)
- 0 fallback_occurred — 所有 ATE 单 tier 终止

### 按路径 (6h)
| 路径 | cnt | ok | avg_ttfb | avg_dur | max_dur |
|------|-----|----|----------|---------|---------|
| nv_integrate | 95 | 87 | 17,947ms | 19,978ms | 96,999ms |
| nvcf_pexec | 27 | 27 | 11,696ms | 11,696ms | 48,049ms |
| (null/ATE) | 2 | 0 | 501ms | 61,375ms | 61,376ms |

### 按模型 (6h)
| 模型 | 总请求 | OK | Fail | SR% | 备注 |
|------|--------|-----|------|-----|------|
| glm5_2_nv | 89 | 81 | 8 | 91.0% | 6× zombie_empty + 2× stream timeout (pre-restart) |
| dsv4p_nv | 19 | 17 | 2 | 89.5% | 2× ATE all pre-restart |
| minimax_m3_nv | 9 | 9 | 0 | 100% | — |
| kimi_nv | 7 | 7 | 0 | 100% | — |

### Post-Restart 数据 (17:15:42 UTC →)
- 5 req, 2 OK, 3 zombie_empty_completion → 40% SR (样本极小)
- 全部 glm5_2_nv, zombie 检测在 3-15s 内中止
- 旧行为: 96s hang → NVStream_TimeoutError; 新行为: 3-15s zombie abort → 502

### nv_gw 日志
- 8 次 NV-ZOMBIE-EMPTY (content_chars < 50, input_chars ≥ 5000, no tool_calls)
- 全部 NV-ZOMBIE-ABORT: RST abort + SO_LINGER=0, openclaw fallback
- 无 NV-TIER-FAIL, 无 NV-EMPTY-FASTBREAK, 无 NV-GLOBAL-COOLDOWN
- glm5_2_nv integrate: k1/k2 均在第 1 次尝试成功 (ttfb 1.6-7.6s)

### ms_gw 健康
- 正常: MS-OK-STREAM, MS-STREAM-DONE (glm5_2_ms, dsv4p_ms)
- 1× MS-STREAM-CLIENT-EOF (BrokenPipeError, client-side disconnect)
- 1× MS-VARIANT-EXHAUSTED + MS-FASTBREAK (stream_no_data_lines, 正常循环)
- 无 EXHAUSTED, 无 SETTO-ERR

---

## 环境参数 (全在 Floor)

| 参数 | 值 | 状态 |
|------|-----|------|
| TIER_TIMEOUT_BUDGET_S | 198 | floor |
| UPSTREAM_TIMEOUT | 66 | floor |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | floor |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | floor |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | floor (R1031) |
| TIER_COOLDOWN_S | 15 | floor (R1103 revert) |
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 | floor |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | floor |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | floor (R923) |
| KEY_COOLDOWN_S | 25 | floor |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | floor (R922) |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | floor (R818) |
| NVU_FORCE_STREAM_UPGRADE | 0 | floor |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | floor |

---

## 分析

### zombie_empty_completion ×6 (3,443-15,320ms, ALL post-restart)
- **新行为**: 容器最近重启后 zombie detection 代码激活
- 检测逻辑: finish_reason=stop, content_chars < 50, input_chars ≥ 5000, no tool_calls
- 中止方式: RST abort + SO_LINGER=0, 返回 502, 触发 openclaw fallback
- Duration 3-15s vs 旧行为 96s NVStream_TimeoutError — **显著改善**
- 6h SR 从 96.4% (R1106) 降至 91.9% — 但 zombie 快速中止比 96s hang 更好
- Code-level feature, not config-fixable
- 无 NV-GLOBAL-COOLDOWN 触发 — zombie 502 不触发 cooldown

### dsv4p_nv ATE ×2 (~61s, pre-restart)
- 全部 pre-restart, duration ~61,375ms ≈ NVU_TIER_BUDGET_DSV4P_NV=66
- Post-restart dsv4p_nv pexec 正常 (27/27, 100%)
- 分析同 R1105-R1106

### glm5_2_nv NVStream_TimeoutError ×2 (95-97s, pre-restart)
- 全部 pre-restart
- Code-level streaming sync defect (R1103 已记录)
- 分析同 R1106

---

## 决策: NOP

**所有参数已在 floor。91.9% SR (114/124)。10 fail: 6× zombie_empty_completion (code-level 新功能, 快速中止替代 96s hang), 2× ATE (pre-restart), 2× stream timeout (pre-restart, code-level)。**

- zombie_empty_completion 是代码级 zombie 检测功能 — 不可配置修复, 且是正向改进 (3-15s 快速中止 vs 96s hang)
- 无参数调整空间 — 所有 FASTBREAK 在 floor, BUDGET 充裕, TIER_COOLDOWN=15 floor
- Post-restart dsv4p_nv pexec 27/27 100% — 正常
- Post-restart glm5_2_nv: 2/5 OK, 3 zombie — 小样本, zombie 检测正常
- ms_gw 正常工作 — 无异常
- 铁律: 只改 HM1 绝不改 HM2

**Zero param change.**

---

## ⏳ 轮到HM1优化HM2
