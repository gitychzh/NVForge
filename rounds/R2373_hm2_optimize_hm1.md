# R2373 (HM2→HM1): TIER_TIMEOUT_BUDGET_S 415→475 — kimi_nv ATE fallback gap

## 数据概览 (2026-07-26 02:34 UTC, 12h)

| 指标 | kimi_nv | glm5_2_nv | dsv4p_nv |
|---|---|---|---|
| 12h 总量 | 79 | 61 | 14 |
| 12h SR | 78.5% (62/79) | 45.9% (28/61) | 28.6% (4/14) |
| 主要 ATE | 11 all_tiers_exhausted @~210s | 24 instant ATE + 9 zombie | 10 ATE @~154s |

### kimi_nv ATE 详情 (12h)

- 11 个 ATE: `all_tiers_exhausted, tiers_tried_count=1, fallback_occurred=false`
- 聚类: duration 185s–222s, 无 fallback_tiers_used
- 根源: kimi_nv 预算 265s 耗尽后, 剩余 `415-265=150s` 不足 glm5_2_nv(210s) 或 dsv4p_nv(265s)
- 后果: 11 个请求在 kimi_nv 耗尽后无 fallback 尝试, 直接返回 502

## 优化决策

| 参数 | 旧值 | 新值 | 理由 |
|---|---|---|---|
| `TIER_TIMEOUT_BUDGET_S` | 415 | 475 | +60s. kimi_nv ATE 后剩余 475-265=210s, 刚好容纳 glm5_2_nv(210s) 作为 fallback |

- 数学: 475-265=210 ≥ 210 (glm5_2_nv budget), 精确匹配
- 总预算: 475 < 500 (PROXY_TIMEOUT), 安全
- dsv4p_nv 仍不能做 kimi 的 fallback (475-265=210 < 265), 但 glm5_2_nv 可做
- 不影响 glm5_2_nv→dsv4p_nv 路径: 475-210=265 ≥ 265 (dsv4p_nv budget), 已有的 fallback 保留
- 单参数; 铁律: 只改 HM1

## 部署验证

- `docker compose up -d nv_gw` → Recreated → Started
- `docker exec nv_gw env | grep TIER_TIMEOUT_BUDGET` → `TIER_TIMEOUT_BUDGET_S=475` ✅
- curl `http://localhost:40006/health` → 200 ✅

## 预期结果

- kimi_nv ATE 后 glm5_2_nv 获得 210s budget, 有机会 fallback 成功
- 11 个无 fallback 的 ATE 中部分可转为 glm5_2_nv 尝试, 提升整体 SR
- glm5_2_nv 自身 SR 偏低 (45.9%), 但作为 fallback 仍比直接 502 好

## ⏳ 轮到 HM1 优化 HM2