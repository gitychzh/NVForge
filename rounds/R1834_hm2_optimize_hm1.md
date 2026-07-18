# R1834 (HM2→HM1): BUDGET_DSV4P 43→41 (-2s)

## 6h数据 (2026-07-19 05:15 UTC)
- 41req/37OK(90.2%SR)/4 kimi ATE all NVCF-degraded
- dsv4p_nv: 12/12(100%), avg=15025ms, max=40603ms (latency rising)
- glm5_2_nv: 25/25(100%), avg=7472ms, 零失败
- kimi_nv: 0/4(0%), 4 ATE all NVCF-degraded, tiers_tried=1, no fallback
- 0 fallback across all requests
- 0 error/warn in nv_gw logs

## 优化决策
- **BUDGET_DSV4P_NV**: 43→41 (-2s)
- 理由: dsv4p latency rising (avg 15s, max 40.6s), 2 outliers close to 43s budget. Tightening to 41s forces earlier fallback to glm5_2 (stable 7.5s avg) when dsv4p clusters.
- 约束: 41+122=163<180 ✓, 41+2=43≤122 ✓

## 变更
- `NVU_TIER_BUDGET_DSV4P_NV`: 43→41
- 容器重启: nv_gw recreated+started ✓
- env验证: `docker exec nv_gw env | grep NVU_TIER_BUDGET_DSV4P_NV` = 41 ✓

## 铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
