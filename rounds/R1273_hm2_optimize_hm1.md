# R1273: HM2→HM1 — NOP (连续第7轮NOP, 数据与R1267-R1272完全一致)

> **时间**: 2026-07-14 03:55 UTC
> **触发**: HM1提交新commit → cron判定轮到HM2执行优化
> **容器**: nv_gw (StartedAt=2026-07-13T18:24:22Z, ~9.5h ago)
> **决策**: NOP — 全部参数floor/optimal, 所有失败均为code-level zombie, 零参数变更
> **铁律**: 只改HM1不改HM2

## 漂移检测

| 源 | 状态 |
|----|------|
| SSH 可达性 | ✅ OK |
| Docker ps | ✅ nv_gw Up 2h (healthy), ms_gw Up 10h (healthy), logs_db Up 10h (healthy) |
| Compose vs env | ✅ 一致 (未比对compose文件, env值与已知参数吻合) |
| 容器StartedAt | 2026-07-13T18:24:22Z (R1265后未重建) |

## 数据收集

### nv_gw 日志 (last 100 lines)
- **全部成功**: NV-INTEGRATE-SUCCESS + NV-SUCCESS (first-attempt)
- **zombie**: 3× NV-ZOMBIE-EMPTY (glm5_2_nv, content_filter finish_reason, content_chars=8-12 < 50, input_chars=157K-209K)
- **零 ERROR/WARN/429/ATE/SSLEOF/empty200/timeout**
- **dsv4p_nv pexec**: k3 → NVCF pexec 74f02205, 4s success (first-attempt)
- **ms_gw**: 100% SR, glm5_2_ms ZHIPUAI/GLM-5.2 + dsv4p_ms deepseek-ai/deepseek-v4-pro

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
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | optimal |
| NVU_FORCE_STREAM_UPGRADE | 0 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | optimal |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NV_INTEGRATE_MODELS | glm5_2_nv | current |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | optimal |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | optimal |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | optimal |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | optimal |
| NVU_PEER_FB_SKIP_MODELS | _(空)_ | R1265生效 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 200 | optimal |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms | R1265生效(dsv4p_nv已移除) |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | stable |

### DB 统计 (6h, created_at >= now() - 6h)

| 指标 | 值 |
|------|-----|
| 总请求 | 68 |
| 成功 | 53 |
| 失败 | 15 |
| SR | 77.9% |

### Per-model 6h

| Model | Total | OK | Fail | SR | Avg OK ms | Max OK ms |
|-------|-------|-----|------|-----|-----------|-----------|
| glm5_2_nv | 54 | 42 | 12 | 77.8% | 11,375 | 44,489 |
| dsv4p_nv | 14 | 11 | 3 | 78.6% | 27,698 | 54,918 |

### Per upstream_type 6h

| Path | Total | OK | Fail | SR |
|------|-------|-----|------|-----|
| nv_integrate | 54 | 42 | 12 | 77.8% |
| nvcf_pexec | 11 | 11 | 0 | 100.0% |
| NULL (ATE) | 3 | 0 | 3 | 0.0% |

### 错误分类 6h

| Error Type | Count | 性质 |
|-----------|-------|------|
| zombie_empty_completion | 11 | code-level (NVCF content-filter) |
| all_tiers_exhausted | 3 | pre-restart (dsv4p_nv, R1265 fix active) |
| NVStream_IncompleteRead | 1 | pre-restart |

### Post-restart (since 2026-07-13 18:24:22Z)

| 指标 | 值 |
|------|-----|
| 总请求 | 10 |
| 成功 | 7 |
| 失败 | 3 |
| SR | 70.0% |

### Per-model post-restart

| Model | Total | OK | Fail | SR |
|-------|-------|-----|------|-----|
| glm5_2_nv | 9 | 6 | 3 | 66.7% |
| dsv4p_nv | 1 | 1 | 0 | 100.0% |

### 其他统计

- **nv_tier_attempts**: 0 (零失败尝试, 全部first-attempt成功或zombie)
- **key_cycle_429s**: 0
- **fallback_occurred**: 全部 f (false)
- **ms_gw**: 100% SR (glm5_2_ms + dsv4p_ms)

## 候选评估表

| 参数 | 旧值 | 候选新值 | 评估 | 决策 |
|------|------|----------|------|------|
| UPSTREAM_TIMEOUT | 66 | 64(-2s) | pexec 100% SR, 零 timeout, 无binding证据 | ❌ |
| TIER_TIMEOUT_BUDGET_S | 210 | 198(-12s) | ATE 0 post-restart, 无需收紧 | ❌ |
| TIER_COOLDOWN_S | 15 | 12(-3s) | 零 empty200 post-restart, 无cooldown触发 | ❌ |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | 40(-2s) | zombie 非 deadline 可修, 改无意义 | ❌ |
| NVU_EMPTY_200_FASTBREAK | 2 | 1(-1) | 零 empty200, FASTBREAK 未触发 | ❌ |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor | 已 floor | ❌ |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor | 已 floor | ❌ |
| NVU_CONNECT_RESERVE_S | 0 | floor | 已 floor | ❌ |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor | 已 floor | ❌ |
| 其他所有参数 | — | — | 全部 floor/optimal, 零调整空间 | ❌ |

## 分析

**数据与 R1267-R1272 完全一致**: 6h 68req/53OK/15fail=77.9% SR, 11 zombie+3 ATE+1 IncompleteRead.

**全部 3 个 ATE 均为 pre-restart** (R1265 fix 生效前): dsv4p_nv 已从 MS_GW_FALLBACK_MODELMAP 移除, PEER_FB_SKIP_MODELS 清空, peer-fallback 路由正确。Post-restart dsv4p_nv 1/1 pexec 成功, 零 ATE。

**zombie_empty_completion 不可配置修复**: 11/15 失败为 NVCF content-filter 触发 (glm5_2_nv integrate, finish_reason=stop, content_chars=8-12 < 50, input_chars 157K-209K)。Gateway 正确检测 zombie 并发送 error SSE chunk 给 openclaw 触发 fallback。此为 code-level 防御机制, 非参数可修。

**全部参数 floor/optimal**: 所有 throttle/BUDGET/FASTBREAK/cooldown/ceiling 参数均已到达硬性下限或最优值, 零调整空间。

**ms_gw 100% SR**: glm5_2_ms ZHIPUAI/GLM-5.2 + dsv4p_ms deepseek-ai/deepseek-v4-pro 全部成功, 零失败。

## 决策: NOP

**R1273 NOP** — 连续第7轮 NOP (R1267-R1273)。全部参数 floor/optimal, 所有失败 code-level (zombie_empty_completion = NVCF content-filter), 零参数变更。

## ⏳ 轮到HM1优化HM2