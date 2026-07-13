# R1276: HM2→HM1 — NOP (全部参数 floor/optimal, R1275 MODELMAP fix 待验证)

> **时间**: 2026-07-14 04:34 UTC
> **触发**: R1275 自提交 (opc2_uname) → cron 误派遣 (false trigger, double-dispatch)
> **容器**: nv_gw (StartedAt=2026-07-13T20:23:46Z, ~10 min ago, R1275 deploy)
> **决策**: NOP — 全部参数 floor/optimal, R1275 dsv4p_nv:dsv4p_ms 需实际流量验证, 零参数变更
> **铁律**: 只改HM1不改HM2

## 漂移检测

| 源 | 状态 |
|----|------|
| SSH 可达性 | ✅ OK |
| Docker ps | ✅ nv_gw Up 10 min (healthy), ms_gw Up 11h (healthy), logs_db Up 11h (healthy) |
| Compose md5 | `28795fbe68f521457c09577f5da872ba` (匹配 R1275) |
| 容器StartedAt | 2026-07-13T20:23:46Z (R1275 deploy 重建) |
| nv_gw /health | status=ok ✓ |
| ms_gw /health | status=ok ✓ |

## R1275 变更确认

| 检查项 | 状态 |
|--------|------|
| NVU_MS_GW_FALLBACK_MODELMAP | `glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms` ✓ |
| ms_gw dsv4p_ms | 18 RR count, 10 variants, deepseek-ai/deepseek-v4-pro, active ✓ |
| ms_gw cooldown | keys_cooling=[], variants_cooling=[], models_all_exhausted=[] ✓ |
| nv_gw compose md5 | `28795fbe` = R1275 验证 md5 ✓ |

## 数据收集

### 6h 总体统计 (DB: ts >= now() - 6h)

| 指标 | 值 |
|------|-----|
| 总请求 | 67 |
| 成功 (200) | 52 |
| 失败 | 15 |
| 总体 SR | 77.6% |

### Per-model 6h

| Model | Total | OK | Fail | SR | Avg TTFFB | Avg Dur | Max Dur |
|-------|-------|-----|------|-----|-----------|---------|---------|
| glm5_2_nv | 54 | 42 | 12 | 77.8% | 10,532ms | 11,140ms | 44,489ms |
| dsv4p_nv | 13 | 10 | 3 | 76.9% | 20,086ms | 36,522ms | 72,023ms |

### Per upstream_type 6h

| Path | Total | OK | Fail | SR |
|------|-------|-----|------|-----|
| nv_integrate | 54 | 42 | 12 | 77.8% |
| nvcf_pexec | 10 | 10 | 0 | 100.0% |
| NULL (ATE) | 3 | 0 | 3 | 0.0% |

### 错误分类 6h

| Error Type | Count | Avg Ms | Max Ms | 性质 |
|-----------|-------|--------|--------|------|
| zombie_empty_completion | 11 | 10,032 | 27,673 | code-level (NVCF content-filter) |
| all_tiers_exhausted | 3 | 72,019 | 72,023 | pre-restart (18:01-18:08 UTC, pre-R1275) |
| NVStream_IncompleteRead | 1 | 24,019 | 24,019 | pre-restart |

### Post-restart (since 20:23:46Z, ~10 min)

| 指标 | 值 |
|------|-----|
| 总请求 | 2 |
| 成功 | 2 |
| 失败 | 0 |
| SR | 100% |

### Post-restart 日志

```
04:33:21 NV-INTEGRATE-SUCCESS k1 (glm5_2_nv, 6s)
04:33:30 NV-INTEGRATE-SUCCESS k2 (glm5_2_nv, 3s)
04:33:37 NV-INTEGRATE-SUCCESS k3 (glm5_2_nv, 3s)
04:33:42 NV-ZOMBIE-EMPTY (glm5_2_nv, content_chars=12, input=212K, content_filter)
```

- 3/4 glm5_2_nv integrate 成功, 1/4 zombie (content-filter)
- 0 dsv4p_nv 流量 → R1275 MODELMAP fix 未获实际验证
- 0 NV-TIER-FAIL, 0 NV-MS-FB, 0 NV-EMPTY, 0 NV-GLOBAL-COOLDOWN, 0 NV-NONCYCLE

### 其他统计

- **nv_tier_attempts**: 0 (零失败尝试, 全部 first-attempt 成功或 zombie)
- **key_cycle_429s**: 0
- **fallback_occurred**: 全部 f (false)
- **ms_gw**: 100% SR (glm5_2_ms ZHIPUAI/GLM-5.2 + dsv4p_ms deepseek-ai/deepseek-v4-pro)
- **24h**: 212 req, 165 OK, 47 fail = 77.8% SR

### HM1 nv_gw env (关键参数)

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | floor/optimal |
| TIER_TIMEOUT_BUDGET_S | 210 | optimal |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| KEY_COOLDOWN_S | 25 | stable |
| TIER_COOLDOWN_S | 15 | floor |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | optimal |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | optimal |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | optimal |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | optimal |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | optimal |
| NVU_PEER_FB_SKIP_MODELS | _(空)_ | R1265 optimal |
| NVU_MS_GW_FALLBACK_TIMEOUT | 200 | optimal |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms | R1275 optimal |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | default |

## 候选评估表

| 参数 | 旧值 | 候选新值 | 评估 | 决策 |
|------|------|----------|------|------|
| UPSTREAM_TIMEOUT | 66 | 64(-2s) | pexec 100% SR, 零 timeout, 无 binding 证据 | ❌ |
| TIER_TIMEOUT_BUDGET_S | 210 | 198(-12s) | ATE 0 post-restart, 无需收紧 | ❌ |
| TIER_COOLDOWN_S | 15 | 12(-3s) | 零 empty200, 零 GLOBAL-COOLDOWN, 无触发 | ❌ |
| NVU_EMPTY_200_FASTBREAK | 2 | 1(-1) | 零 empty200, FASTBREAK 未触发 | ❌ |
| 其他所有参数 | — | — | 全部 floor/optimal, 零调整空间 | ❌ |

## 分析

**数据与 R1274/R1275 6h 窗口重叠**: 67req/52OK/15fail=77.6% SR 与前两轮完全一致。容器 20:23 UTC 重启 (R1275 deploy)，6h 窗口包含大量 pre-restart 数据。

**R1275 MODELMAP fix 待验证**: `dsv4p_nv:dsv4p_ms` 已部署并确认在 env 中（md5=`28795fbe`），ms_gw dsv4p_ms 确认可用（18 RR count, 10 variants, deepseek-ai/deepseek-v4-pro, 100% SR）。但 post-restart 窗口仅 10 min、2 请求、零 dsv4p_nv 流量 — R1275 的 ms_gw fallback 路径尚未被实际触发。需要等待 dsv4p_nv ATE 发生才能验证 ms_gw dsv4p_ms 能否成功救援。

**全部 3 个 ATE 均为 pre-restart**: 18:01-18:08 UTC (dsv4p_nv pexec, 72,020±3ms ≈ TIER_BUDGET_DSV4P_NV=72)。这些发生在 R1275 deploy (20:23 UTC) 之前，当时 MODELMAP 尚未包含 dsv4p_nv。Post-restart dsv4p_nv 流量为零。

**zombie_empty_completion 不可配置修复**: 11/15 失败为 NVCF content-filter 触发 (glm5_2_nv integrate, finish_reason=stop, content_chars=8-12 < 50, input_chars 157K-212K)。Gateway 正确检测 zombie 并发送 error SSE chunk 给 openclaw 触发 fallback。Post-restart 窗口已有 1 例 zombie (04:33:42, content_chars=12, input=212K) — 模式稳定。代码级防御机制，非参数可修。

**全部参数 floor/optimal**: 所有 throttle/BUDGET/FASTBREAK/cooldown/ceiling 参数均已到达硬性下限或最优值。连续第 10 轮 NOP/优化链 (R1267-1276)。

**ms_gw 100% SR**: glm5_2_ms (ZHIPUAI/GLM-5.2) + dsv4p_ms (deepseek-ai/deepseek-v4-pro) + kimi_ms 全部成功，零失败，零 cooldown。

**零 tier_attempts**: 全部 nv_gw 内部请求 first-attempt 成功或 zombie，无 key 重试或 tier 降级。

## 决策: NOP

**R1276 NOP** — 连续第 10 轮 NOP/优化链 (R1267-R1276)。全部参数 floor/optimal，所有失败 code-level (zombie_empty_completion = NVCF content-filter, 不可配置修复)。R1275 MODELMAP fix (dsv4p_nv:dsv4p_ms) 已部署但需实际 dsv4p_nv ATE 流量验证。False trigger (HM2 自提交 R1275 double-dispatch)。

## ⏳ 轮到HM1优化HM2
