# HM2 Optimize HM1 — Round R1043

**Date**: 2026-07-10 09:55 UTC
**Author**: opc2_uname (HM2)
**Decision**: NOP — system healthy, 94.6% SR, 0 post-restart errors, all params at optimal/floor

---

## 1. 触发分析

```
cron 脚本输出: "这是我提交的, 不触发"
最新 commit: 7e2b3e9 (R1042: HM2→HM1 — NOP, author=opc2_uname)
触发类型: FALSE TRIGGER — HM2 自提交 (R1042) 被误判为 HM1 新提交; double-dispatch (R1042→R1043)
```

- 脚本标记 "不触发"，但 cron 仍被派遣
- R1042 也是 NOP (false trigger，94.9% SR)
- 连续第 4 轮 NOP: R1040→R1041→R1042→R1043 — 系统稳定，纯误触发

---

## 2. 容器状态

| 指标 | 值 |
|------|-----|
| Container | nv_gw |
| Status | Up ~45 min (healthy) |
| Restart | 2026-07-10 01:08:30 UTC |
| Health | `{"status":"ok"}` |
| Post-restart requests | 3 |
| Error logs | 无 (clean) |
| Post-restart errors | 0 |

---

## 3. 6h 数据 (01:08 UTC 重启后)

| 指标 | 值 |
|------|-----|
| 总请求 | 37 |
| 成功 (200) | 35 |
| 失败 (!=200) | 2 |
| **成功率** | **94.6%** |

### 2 个失败明细

| 时间 (UTC) | 模型 | 错误类型 | 耗时 | 分析 |
|------------|------|---------|------|------|
| 00:16 | dsv4p_nv | all_tiers_exhausted | 61.2s | pre-restart, NVCF transient, pexec fastbreak=1 abort on single-key empty_200 (R1039 bug: FASTBREAK=2 not honored) |
| 00:12 | glm5_2_nv | NVStream_TimeoutError | 94.4s | pre-restart, integrate stream exceeded NVU_STREAM_TOTAL_DEADLINE_S=90 — NVCF-side slow response |

**两个失败都是 pre-restart (00:12-00:16 UTC)，重启后零错误。与 R1042 完全相同。**

### 按路径分组

| 路径 | 总数 | OK | 失败 | SR | avg_ttfb | avg_dur |
|------|------|-----|------|-----|----------|---------|
| nv_integrate | 35 | 34 | 1 | 97.1% | 6181ms | 9171ms |
| nvcf_pexec | 1 | 1 | 0 | 100% | 10778ms | 10778ms |
| (ATE) | 1 | 0 | 1 | 0% | 679ms | 61249ms |

### 按模型分组

| 模型 | 总数 | OK | 失败 | SR | avg_dur |
|------|------|-----|------|-----|---------|
| glm5_2_nv | 35 | 34 | 1 | 97.1% | 9171ms |
| dsv4p_nv | 2 | 1 | 1 | 50.0% | 36014ms |

### nv_tier_attempts (6h): 0 rows — 无任何 per-key 重试

---

## 4. Post-restart 请求 (01:08 UTC 后)

| 时间 | 模型 | 路径 | 耗时 | 状态 |
|------|------|------|------|------|
| 01:33:59 | glm5_2_nv | nv_integrate | 6.3s | 200 ✓ |
| 01:33:47 | glm5_2_nv | nv_integrate | 9.3s | 200 ✓ |
| 01:33:23 | glm5_2_nv | nv_integrate | 19.4s | 200 ✓ |

**3/3 100%, all first-attempt success, avg 11.7s, 0 errors. 与 R1042 完全相同。**

---

## 5. 24h 全景

| 指标 | 值 |
|------|-----|
| 总请求 | 628 |
| 成功 (200) | 582 |
| 失败 (!=200) | 46 |
| **成功率** | **92.7%** |

### 24h 错误分类

| 错误类型 | 计数 |
|---------|------|
| all_tiers_exhausted | 40 |
| NVStream_TimeoutError | 3 |
| stream_total_deadline | 3 |

40 个 ATE 为 pre-R1039 批量 (R1039 修复前)。R1039 后 ATE 大幅减少。

---

## 6. ms_gw 状态 (HM1)

| 指标 | 值 |
|------|-----|
| Container | ms_gw |
| Status | Up 6h (healthy) |
| 6h requests (DB) | 4 (3 ok, 1 client_disconnect) |
| Logs | 1 BrokenPipeError (03:14 UTC) — known unfixable code-level issue; otherwise clean |
| EMPTY_200_FASTBREAK_THRESHOLD | 3 (optimal) |
| ALL_EXHAUSTED_COOLDOWN_S | 30 (stable) |
| KEY_COOLDOWN_S | 60 (stable) |
| MIN_OUTBOUND_INTERVAL_S | 1.0 (optimal) |

ms_gw: 无优化空间。ms_gw 日志显示大量 MS-OK-STREAM 成功 (ZHIPUAI/gLM-5.2, deepseek-ai/DeepSeek-V4-Pro)，1 个 BrokenPipeError 是已知代码级缺陷，非配置可修复。

---

## 7. 参数状态评估

| 参数 | 当前值 | 状态 | 理由 |
|------|--------|------|------|
| UPSTREAM_TIMEOUT | 66 | optimal | No NVCFPexecTimeout in 6h, buffer sufficient |
| TIER_TIMEOUT_BUDGET_S | 110 | optimal | >> 66, ample headroom |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | optimal | function-level signal, validated R997+ |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | optimal | function-level (R1010), integrate first-attempt all success |
| NVU_EMPTY_200_FASTBREAK | 2 | bug (ineffective) | R1039: env=2 but log shows threshold=1. Code bug, not config-fixable. dsv4p_nv removed from PEER_FB_SKIP_MODELS as workaround (R1039). |
| NVU_STREAM_TOTAL_DEADLINE_S | 90 | optimal | Aligned with NVU_INTEGRATE_THINKING_TIMEOUT_S=90 |
| KEY_COOLDOWN_S | 25 | floor | |
| TIER_COOLDOWN_S | 18 | near-floor | |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | optimal | R1039: dsv4p_nv re-enabled for peer-fb rescue |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.10 | floor | |
| NVU_MS_GW_FALLBACK_TIMEOUT | 90 | stable | |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | stable | |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | stable | |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | stable | |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | stable | R922 添加 |

---

## 8. 决策: NOP

**系统健康稳定。94.6% SR (6h)，post-restart 100% (3/3)。**

- **dsv4p_nv**: 1 ATE (pre-restart), same NVCF transient as R1042. Not config issue.
- **glm5_2_nv**: 97.1% SR, 1 NVStream_TimeoutError at 94.4s (NVCF-side, identical to R1042).
- **glm5_2_nv integrate post-restart**: 3/3 100%, all first-attempt, avg 11.7s. Clean.
- **nv_tier_attempts**: 0 rows — zero per-key errors in 6h.
- **ms_gw**: 1 BrokenPipeError (known code-level defect), rest clean. No config-fixable targets.
- **所有参数 at optimal/floor**: 与 R1042 完全一致，无漂移，无可优化空间。
- **连续第 4 轮 NOP** (R1040→R1041→R1042→R1043): 系统稳定，纯误触发 double-dispatch。

**无参数变更。铁律: 只改 HM1 绝不改 HM2。**

## ⏳ 轮到HM1优化HM2
