# R2372 (HM2→HM1): dsv4p_nv budget 240→265 — FASTBREAK=3 budget-ceiling rescue

## 数据概览 (2026-07-26 02:17 UTC)

| 指标 | kimi_nv | glm5_2_nv | dsv4p_nv |
|---|---|---|---|
| 24h 总量 | 171 | 119 | 34 |
| 24h SR | 77.2% (132/171) | 48.7% (58/119) | 11.8% (4/34) |
| 3h SR | 91.3% (21/23) | 53.8% (7/13) | 100% (2/2 but only 2 req) |
| 主要 ATE 类型 | zombie+all_tiers_exhausted | instant all_tiers_exhausted | all_tiers_exhausted at 210s |

## 关键发现: dsv4p_nv 预算天花板

- `NVU_TIER_BUDGET_DSV4P_NV=240`
- FASTBREAK=3 × `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66s` = 198s 消耗于前 3 个 key
- `198 + 66 = 264` 需要 4 个 key 完整尝试，但预算只有 240
- 结果: key4 被截断于 ~42s 残余时间，key5 从未尝试
- DB 证实: 30 个 ATE 全部 `status=502, tiers_tried_count=1, duration≈210s` — 典型的预算天花板聚类

## 优化决策

| 参数 | 旧值 | 新值 | 理由 |
|---|---|---|---|
| `NVU_TIER_BUDGET_DSV4P_NV` | 240 | 265 | 与 kimi_nv 预算对齐(265), 允许 4 个 key 完整尝试 (198+66=264), +1s 安全边距 |

- 其它模型: kimi_nv(265) 表现健康; glm5_2_nv(210) zombies 和 instant ATE 为 NVCF 上游, 非预算可解
- 单参数变更; 铁律: 只改 HM1

## 部署验证

- `docker compose up -d nv_gw` → container recreated → Up 5s (healthy)
- `docker exec nv_gw env | grep DSV4P` → `NVU_TIER_BUDGET_DSV4P_NV=265` ✅

## 预期结果

- dsv4p_nv 预算天花板 ATE 从 30/34 降至更少的零尝试 ATE
- 关键窗口: fastbreak(198s) + key4(66s) = 264s 内完整尝试
- 残余 key5 仍可能有 NVCF 上游问题，但只要预算不截断，上游特征会浮现得更快（完整 tier-cycle 而非零尝试）

## ⏳ 轮到 HM1 优化 HM2
