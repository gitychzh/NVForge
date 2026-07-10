# HM2 Optimize HM1 — Round R1106

**日期**: 2026-07-11 17:08 UTC (北京时间 01:08)
**类型**: NOP (False Trigger, Double-Dispatch)
**作者**: HM2 (opc2_uname)

---

## 触发分析

cron 脚本输出:
```
HEAD is now at de6e3f5 R1105: HM2→HM1 — NOP (false trigger, HM2自提交...
[2026-07-11 01:00:11] 这是我提交的, 不触发
```

- 最新 commit de6e3f5 author = `opc2_uname` (HM2)
- 脚本正确检测到自提交 → false trigger
- cron 仍被派遣 — double-dispatch pattern (R884+ streak continues)
- HM1 本地 git log 最新: R821 (fbf0e43) — 284 轮落后
- 无 HM1 新提交

---

## 数据收集 (改前必有数据)

### 容器状态
- 容器: nv_gw, Up (R1103 post-restart)
- 重启时间: 2026-07-10 16:23:01 UTC (R1103 应用 TIER_COOLDOWN_S 18→15)
- 当前时间: 17:08 UTC

### 6h 总体 (11:08-17:08 UTC)
- 112 req, 108 OK, 4 fail → **96.4% SR**
- 4 ATE: 2× dsv4p_nv all_tiers_exhausted (~61s), 2× glm5_2_nv NVStream_TimeoutError (~95-97s)
- dsv4p_nv ATEs: 全部 pre-restart (15:50, 16:00)
- glm5_2_nv stream timeouts: 1 pre-restart (15:56), 1 post-restart (16:52)
- nv_tier_attempts: 0 rows (post-restart 无失败尝试)
- 0 fallback_actually_attempted — 所有 ATE 单 tier 终止

### 按路径 (6h)
| 路径 | cnt | ok | avg_ttfb | avg_dur | max_dur |
|------|-----|----|----------|---------|---------|
| nv_integrate | 83 | 81 | 19,449ms | 21,738ms | 96,999ms |
| nvcf_pexec | 27 | 27 | 11,696ms | 11,696ms | 48,049ms |
| (null/ATE) | 2 | 0 | 501ms | 61,375ms | 61,376ms |

### 按模型 (6h)
| 模型 | 总请求 | OK | ATE | SR% | 备注 |
|------|--------|-----|-----|-----|------|
| glm5_2_nv | 83 | 81 | 2 | 97.6% | 2× stream timeout (1 pre, 1 post restart) |
| dsv4p_nv | 19 | 17 | 2 | 89.5% | 2× ATE all pre-restart |
| minimax_m3_nv | 9 | 9 | 0 | 100% | — |
| kimi_nv | 7 | 7 | 0 | 100% | — |

### nv_gw 日志
- 容器日志仅 39 行 (R1103 重启后，窗口短)
- 最近 500 行: 无 NV-TIER-FAIL, 无 NV-EMPTY-FASTBREAK, 无 NV-GLOBAL-COOLDOWN
- 1 次 SSL cycle: glm5_2_nv k2 SSLEOFError → k3 成功 (9s 内恢复)
- 所有 glm5_2_nv integrate 均在 1st key 成功，ttfb 1.8-13.8s
- dsv4p_nv pexec 正常: 1/1 成功 (30,897ms)

### ms_gw 健康
- 正常: 15 次 MS-OK/MS-STREAM-DONE
- 1 次 MS-STREAM-CLIENT-EOF (BrokenPipeError, client-side disconnect)
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
| NVU_EMPTY_200_FASTBREAK | 2 | floor (R1031, confirmed by docker exec python3) |
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

## ATE 分析

### dsv4p_nv ×2 (~61s, pre-restart)
- 2× all_tiers_exhausted, tiers_tried_count=1, fallback_actually_attempted=false
- Duration ~61,375ms ≈ NVU_TIER_BUDGET_DSV4P_NV=66 (budget 耗尽)
- Pre-restart artifacts — R1103 容器重启前
- 所有模型健康 ≥ 0.05 (glm5_2 98.4%, kimi 100%, minimax 100%) — FALLBACK_HEALTH_THRESHOLD 未阻塞
- fallback 未触发是 code-level（budget 耗尽路径可能跳过 fallback dispatch）
- No change needed — 同 R1105 分析

### glm5_2_nv ×2 (95-97s, 1 pre + 1 post restart)
- NVStream_TimeoutError, stream=true, integrate path
- 96,999ms ≈ NVU_TIER_BUDGET_GLM5_2_NV=96 (budget 耗尽)
- 95,076ms (post-restart) — 同样 ≈ budget 耗尽
- error_subcategory=NULL — code-level streaming sync defect (R1103 已记录)
- ms_gw streaming sync defect: nv_gw 看不到 ms_gw 的 completion signal
- Code-level defect, not config-fixable
- Post-restart 确认: 缺陷持续存在

---

## 决策: NOP

**所有参数已在 floor。96.4% SR (108/112)。4 ATE: 2× pre-restart dsv4p_nv + 2× glm5_2_nv stream timeout (1 post-restart, code-level)。**

- 无参数调整空间 — 所有 FASTBREAK 在 floor, BUDGET 充裕, TIER_COOLDOWN=15 floor
- Post-restart 唯一 fail (glm5_2_nv 16:52 stream timeout) 是 code-level streaming sync defect，不可配置修复
- dsv4p_nv ATE 全部 pre-restart，post-restart dsv4p_nv pexec 正常
- NVU_EMPTY_200_FASTBREAK=2 已确认生效 (docker exec python3 验证)
- ms_gw 正常工作 — 无 BrokenPipeError 以外异常
- 铁律: 只改 HM1 绝不改 HM2

**Zero param change.**

---

## ⏳ 轮到HM1优化HM2
