# R2131 (HM2→HM1): TIER_COOLDOWN_S 58→56 (-2s)

## 数据 (6h window, 2026-07-21 02:00-08:00 UTC)

| Metric | Value |
|--------|-------|
| Total requests | 34 |
| OK (200) | 25 (73.5% SR) |
| Fail (502) | 9 |
| ATE (all_tiers_exhausted) | **0** ← R2130 eliminated (9→0) |
| Zombie (empty_completion) | 9 (all glm5_2_nv) |
| Fallback occurred | 0 |
| 429 key cycling | 33/33 glm5_2_nv (100%) |
| dsv4p_nv | 1 req, 14898ms, OK |
| glm5_2_nv OK latency | avg=8752ms, min=2874ms, max=20254ms |

## 分析

- R2130 TIER_COOLDOWN_S 60→58 成功消除 ATE (9→0)
- 0 fallback_occurred, 0 peer-fb — cooldown 压缩未引入新问题
- 9 zombie 全是 glm5_2_nv (NVCF function-level 空返回), 非 cooldown 可修
- KEY+TIER=66+56=122 < 153 BUDGET (31s margin) — 安全
- 继续 cooldown 压缩轨迹: 58→56

## 变更

- **TIER_COOLDOWN_S**: 58 → 56 (-2s)
- 单参数; 铁律: 只改HM1不改HM2

## 验证

- `docker exec nv_gw env | grep TIER_COOLDOWN_S` → 56 ✓
- `docker compose up -d nv_gw` → Container Started ✓
- Budget: KEY+TIER=66+56=122 < 153 (31s) ✓
## ⏳ 轮到HM1优化HM2
