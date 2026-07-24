# R2342: HM2→HM1 — NOP — Cron 误触发，R2341 dsv4p_nv BUDGET 180s 仅 26min unsettled，0 dsv4p_nv 流量，零参数变更

## 变更
**无参数变更** — NOP。R2341 (HM2→HM1, NVU_TIER_BUDGET_DSV4P_NV 140→180) 部署于 2026-07-24T22:15:19Z，距今仅 26 分钟。Post-restart 流量 6 条，dsv4p_nv 流量 0 条。R2341 效果无法评估，不可叠加变更。

## 触发类型
Cron 误触发。脚本输出 `"这是我提交的, 不触发"` — HM2 自己的 R2341 commit 被正确识别为自提交，但 cron 仍派遣。遵循 cron-false-trigger 规则：完整数据收集 → NOP 决策。

## 容器状态
- Container: nv_gw, StartedAt=2026-07-24T22:15:19.146537256Z (26 min), Status=running (healthy)
- 当前时间: 2026-07-24 22:41 UTC

## Post-restart 数据 (22:15:19Z → 22:41Z, ~26 min)
| tier_model | total | ok | err | avg_ok_s | SR |
|---|---|---|---|---|---|
| kimi_nv | 3 | 3 | 0 | 49.1 | 100% |
| glm5_2_nv | 3 | 2 | 1 | 18.1 | 66.7% |
| dsv4p_nv | 0 | 0 | 0 | — | — |

Post-restart 错误明细:
- glm5_2_nv ×1: zombie_empty_completion (req=b612a1bd, 8s dur, 12 output chars < 50, R852b trigger)

Tier 尝试 (post-restart):
- kimi_nv k3: NVCFPexecRemoteDisconnected (35.6s) → 请求仍成功 (k5 重试成功)

## 3h 数据 (混合 pre/post-restart，含旧 regime 污染)
| tier_model | total | ok | err | SR |
|---|---|---|---|---|
| kimi_nv | 19 | 14 | 5 | 73.7% |
| glm5_2_nv | 17 | 6 | 11 | 35.3% |
| dsv4p_nv | 4 | 2 | 2 | 50.0% |

3h 错误: all_tiers_exhausted ×15 (glm5_2 10, kimi 3, dsv4p 2), zombie_empty_completion ×3 (glm5_2 1, kimi 2)

## 24h 数据 (context only)
| tier_model | total | ok | err | SR | avg_ok_s |
|---|---|---|---|---|---|
| glm5_2_nv | 143 | 42 | 101 | 29.4% | 13.5 |
| dsv4p_nv | 66 | 16 | 51 | 24.2% | 53.5 |
| kimi_nv | 42 | 26 | 16 | 61.9% | 47.9 |

## ATE 根因分析
| 错误类型 | tier | cnt (3h) | 可配置修复 |
|---|---|---|---|
| all_tiers_exhausted | glm5_2_nv | 10 | ❌ NVCF 上游 429/504 风暴 |
| all_tiers_exhausted | kimi_nv | 3 | ❌ NVCF 上游 |
| all_tiers_exhausted | dsv4p_nv | 2 | ❌ NVCF 上游 (pre-restart, 旧 regime) |
| zombie_empty_completion | glm5_2_nv | 1 | ❌ 内容质量问题 (12 output chars) |
| zombie_empty_completion | kimi_nv | 2 | ❌ 内容质量问题 |

Tier 尝试级错误 (3h):
| 错误 | tier | cnt | 可修复性 |
|---|---|---|---|
| empty_200 | kimi_nv | 8 | ❌ NVCF 上游 Content-Length:0 |
| NVCFPexecRemoteDisconnected | kimi_nv | 3 | ❌ NVCF 上游连接断开 |
| NVCFPexecRemoteDisconnected | dsv4p_nv | 1 | ❌ NVCF 上游 |
| NVCFPexecTimeout | glm5_2_nv | 1 | 25s < UPSTREAM=24? 边界 |

## 当前配置快照
| 参数 | 值 | 状态 |
|---|---|---|
| NVU_TIER_BUDGET_DSV4P_NV | 180 | ✅ R2341 新设，待验证 |
| NVU_TIER_BUDGET_GLM5_2_NV | 210 | ✅ |
| NVU_TIER_BUDGET_KIMI_NV | 180 | ✅ |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | ✅ |
| UPSTREAM_TIMEOUT | 24 | ✅ |
| TIER_TIMEOUT_BUDGET_S | 415 | ✅ |
| NVU_EMPTY_200_FASTBREAK | 2 | ✅ R2340 新设 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 2 | ✅ |
| KEY_COOLDOWN_S | 30 | ✅ |
| TIER_COOLDOWN_S | 30 | ✅ |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | ✅ |
| NVU_PEER_FALLBACK_ENABLED | 1 | ✅ |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv,dsv4p_nv,kimi_nv | ⚠️ 全部跳过 peer fallback |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 15 | ✅ |
| NVU_STREAM_TOTAL_DEADLINE_S | 90 | ✅ |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | ✅ |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | ✅ |

## NOP 决策依据
1. **R2341 未验证**: dsv4p_nv BUDGET 180s 部署仅 26min，0 dsv4p_nv 流量 → 不可叠加新变更
2. **Post-restart 数据不足**: 6 条请求，<10 → 遵循 post-restart-evaluation-pitfall 规则
3. **6h 窗口污染**: 含大量 pre-restart 旧 regime 数据，不可用于决策
4. **所有 ATE 上游不可修复**: empty_200, NVCFPexecRemoteDisconnected, all_tiers_exhausted 均为 NVCF 问题
5. **无参数漂移**: 所有参数在 optimal 状态
6. **kimi_nv post-restart 100% SR**: 当前 regime 健康

## 安全分析
- BUDGET (180-210s) >> UPSTREAM (24s) ✓
- FASTBREAK (2) × UPSTREAM (24) = 48s << BUDGET (180s) ✓
- 零变更无风险 ✓
- 下一轮 R2341 应有充足 dsv4p_nv 流量验证 BUDGET 180s 效果

## 铁律
NOP 轮。铁律：只改 HM1 不改 HM2。

## ⏳ 轮到HM1优化HM2