# R1659: HM2→HM1 — NOP (zero dsv4p_nv traffic post-R1658, FASTBREAK=2 unevaluable)

**决策**: NOP — R1658 (FASTBREAK 1→2) 尚未有流量测试。所有 5 个 dsv4p_nv ATE 均为 pre-R1658 (July 16 18:00-18:04 UTC)。zombie 为 NVCF 服务端内容过滤，不可配置修复。无新数据，无参数可改。

## 数据摘要

### 6h 窗口 (37req/20OK/17fail = 54.1% SR)

| 模型 | 请求 | OK | 失败 | SR | avg_ok_ms |
|------|------|-----|------|-----|-----------|
| dsv4p_nv | 12 | 7 | 5 | 58.3% | 24,555 |
| glm5_2_nv | 25 | 13 | 12 | 52.0% | 6,105 |

### 错误分解

| error_type | error_subcategory | cnt |
|---|---|---|
| zombie_empty_completion |  | 12 |
| all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 5 |

### dsv4p_nv ATE 详情 (全部 pre-R1658)

| ts | tiers_tried | fallback_tiers_used | fallback_occurred | duration_ms |
|---|---|---|---|---|
| 2026-07-16 18:04:07 | 1 | {dsv4p_nv} | f | 64,280 |
| 2026-07-16 18:03:58 | 1 | {dsv4p_nv} | f | 61,652 |
| 2026-07-16 18:02:56 | 1 | {dsv4p_nv} | f | 61,533 |
| 2026-07-16 18:01:45 | 1 | {dsv4p_nv} | f | 61,822 |
| 2026-07-16 18:00:40 | 1 | {dsv4p_nv} | f | 62,107 |

- 全部单key尝试 (tiers_tried_count=1), 无 peer-FB, 无 ms-gw fallback
- 持续时间 61.5-64.3s — NVCF func 74f02205 504_nv_gateway_timeout @ ~62s
- 全部发生在 R1658 之前 (R1658 applied 2026-07-17 06:30 UTC)

### 30min 窗口 (post-R1658)

- 仅 glm5_2_nv 流量: 3req/2OK/1zombie
- **dsv4p_nv: 0 req** — R1658 FASTBREAK=2 完全未测试
- nv_gw 日志: 仅 glm5_2_nv pexec_us_rr 成功 + zombie

### zombie_empty_completion (代码级，不可配置)

- glm5_2_nv: 12× (avg input 243,895 chars, content_chars=14 < 50)
- 日志: `[NV-ZOMBIE-EMPTY] finish_reason=stop but content_chars=14 < 50`
- NVCF 返回空 completion，gateway 正确检测+快速 abort
- 触发 cc4101 zombie→api_error→CC retry

### tier_attempts

- glm5_2_nv pexec_success: 28× (avg 6,148ms)
- 无 pexec 错误, 无 429, 无 timeout

### peer-FB 约束验证

```
HM1 PEER_FALLBACK_TIMEOUT=72 ≥ HM2 BUDGET_DSV4P_NV=70 + 2 = 72 ✓ (tight)
HM1 BUDGET=90 + PEER_FB_TIMEOUT=72 = 162 < 195 ✓
```

- HM2 peer-FB 约束: HM2 PEER_FALLBACK_TIMEOUT=25 << HM1 BUDGET_DSV4P_NV=90 + 2 = 92 ✗
  - HM2→HM1 peer-FB 必然 timeout，但这是 HM2 的问题，铁律不碰 HM2

## 参数状态

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | 最优 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 2 | R1658 新值，未测试 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | 触底 |
| NVU_EMPTY_200_FASTBREAK | 2 | 最优 |
| TIER_TIMEOUT_BUDGET_S | 195 | 最优 (R1647) |
| NVU_TIER_BUDGET_DSV4P_NV | 90 | R1652 新值 (compose line 646 注释说78但实际值90 ✓) |
| NVU_TIER_BUDGET_GLM5_2_NV | 120 | 最优 |
| TIER_COOLDOWN_S | 65 | R1657 |
| KEY_COOLDOWN_S | 65 | R1657 |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | 触底 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | 最优 |
| NVU_PEER_FALLBACK_TIMEOUT | 72 | 最优 (R1646) |
| NVU_PEER_FB_SKIP_MODELS | (空) | 最优 (R1646) |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms | 最优 |
| NVU_CONNECT_RESERVE_S | 0 | 触底 |
| NVU_SSLEOF_RETRY_DELAY_S | 0.5 | 触底 |

## 铁律验证

- ✅ 只改HM1: 本轮无修改
- ✅ 改前必有数据: 6h DB + 30min post-R1658 + tier_attempts + peer-FB constraint
- ✅ 改后必有验证: N/A
- ✅ 聚焦 nv_gw: 仅分析 nv_gw 链路
- ✅ 所有修改写入仓库: 本轮 NOP 仍记录

## 分析

**R1658 尚未测试**: FASTBREAK 1→2 后零 dsv4p_nv 流量，无法评估效果。R1658 的假设是 k2 在剩余 ~28s budget 内尝试第二键，但 NVCF func 74f02205 504_nv_gateway_timeout 需要 ~62s，28s 远不足以完成。如果 post-R1658 数据仍显示 ATE，可能需要增加 BUDGET_DSV4P_NV 给第二键更多时间 (如 66+62=128)，但这需要同步增加 TIER_TIMEOUT_BUDGET_S (128+72=200，需要 BUDGET≥205)。

**待下次有流量后评估**: 需要至少 3-5 个 dsv4p_nv 请求才能判断 R1658 是否有效。
## ⏳ 轮到HM1优化HM2
