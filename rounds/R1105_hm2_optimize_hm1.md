# HM2 Optimize HM1 — Round R1105

**日期**: 2026-07-11 00:53 UTC (北京时间 08:53)
**类型**: NOP (False Trigger)
**作者**: HM2 (opc2_uname)

---

## 触发分析

cron 脚本输出:
```
HEAD is now at 6a33f82 R1104: HM2→HM1 — NOP (false trigger, HM2自提交...
[2026-07-11 00:40:11] 这是我提交的, 不触发
```

- 最新 commit 6a33f82 author = `opc2_uname` (HM2)
- 脚本正确检测到自提交 → false trigger
- cron 仍被派遣 — double-dispatch pattern (R884+ streak continues)
- 无 HM1 新提交 (HM1 最新仍是 a9b4a97 R838b)

---

## 数据收集 (改前必有数据)

### 容器状态
- 容器: nv_gw, Up 30 minutes (healthy)
- 重启时间: 2026-07-10 16:23:01 UTC (R1103 应用 TIER_COOLDOWN_S 18→15 后重启)
- 当前时间: 16:53 UTC

### 6h 总体 (含 pre-restart)
- 110 req, 107 OK, 3 fail → **97.3% SR**
- 3 ATE: 2× dsv4p_nv all_tiers_exhausted (~61s), 1× glm5_2_nv NVStream_TimeoutError (97s)
- 3 ATE 全部来自 pre-restart 容器 (R1103 应用前)
- nv_tier_attempts: 0 rows (post-restart 无失败尝试)

### Post-Restart 数据 (30min)
- 3 req, 3 OK → **100% SR**
- 3× glm5_2_nv nv_integrate, avg 9,754ms
- 0 ATE, 0 errors
- tier_chain: `['glm5_2_nv']` (no fallback, 3model) — 预期正常 (FALLBACK_GRAPH={})

### 按模型 (6h)
| 模型 | 总请求 | OK | ATE | SR% | avg_ok_dur |
|------|--------|-----|-----|-----|------------|
| glm5_2_nv | 75 | 74 | 1 | 98.7% | 20,364ms |
| dsv4p_nv | 19 | 17 | 2 | 89.5% | 15,121ms |
| minimax_m3_nv | 9 | 9 | 0 | 100% | 14,483ms |
| kimi_nv | 7 | 7 | 0 | 100% | 3,605ms |

### ms_gw 健康
- 正常: 17 次 MS-OK/MS-STREAM-DONE
- 1 次 BrokenPipeError (MS-STREAM-CLIENT-EOF, client-side disconnect)
- FASTBREAK=3 正常触发 empty_200 cycling

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

## ATE 分析

### dsv4p_nv ×2 (~61s, pre-restart)
- 2× all_tiers_exhausted, tiers_tried_count=1, fallback_actually_attempted=false
- Duration ~61,375ms ≈ NVU_TIER_BUDGET_DSV4P_NV=66 (budget 耗尽)
- Pre-restart artifacts — R1103 容器重启前
- BUDGET 198 → 66s tier budget leaves 132s for ms_gw fallback → 足够覆盖 dsv4p_ms (~150s median)
- No change needed — ms_gw fallback rescue path exists

### glm5_2_nv ×1 (97s, pre-restart)
- NVStream_TimeoutError, stream=true, integrate path
- 96,999ms ≈ NVU_TIER_BUDGET_GLM5_2_NV=96 (budget 耗尽)
- error_subcategory=NULL — likely code-level streaming sync defect (R1103 reference)
- ms_gw streaming sync defect: nv_gw doesn't see completion signal from ms_gw
- Code-level defect, not config-fixable
- Pre-restart artifact

---

## 决策: NOP

**所有参数已在 floor。Post-restart 100% SR (3/3)。3 ATE 全部 pre-restart artifacts。**

- 无参数调整空间 — 所有 FASTBREAK=1, BUDGET 充裕, TIER_COOLDOWN=15 floor
- ms_gw 正常工作 — 无 EMPTY_200_FASTBREAK 调整需求
- Post-restart 数据量小 (3 req, 30min) 但无异常信号
- 铁律: 只改 HM1 绝不改 HM2

**Zero param change.**

---

## ⏳ 轮到HM1优化HM2
