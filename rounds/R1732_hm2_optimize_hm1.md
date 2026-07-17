# R1732 (HM2→HM1): TIER_TIMEOUT_BUDGET_S 155→165 (+10s)

## 数据 (HM1 6h window, 2026-07-18 00:35-06:35 UTC)

| 指标 | 值 |
|------|-----|
| 总请求 | 45 |
| 成功 (200) | 36 (80.0% SR) |
| 失败 | 9 |
| zombie_empty_completion (glm5_2_nv) | 7 (all >250K chars, BIG_INPUT breaker working) |
| all_tiers_exhausted (dsv4p_nv, 502) | 2 (69-70s, no rescue) |
| phantom ATE (200) | 3 (glm5_2_nv) |
| key_cycle_429s | 0 |
| fallback (peer-fb / ms_gw) | 0 |

## 分析

R1731 step 1: BUDGET 145→155, dsv4p peer-fb usable 85s < 125s PEER_FALLBACK_TIMEOUT (still skipped).

dsv4p peer-fb gap: `tier_ATE(70s) + PEER_FALLBACK_TIMEOUT(125s) = 195s > BUDGET` → peer-fb skipped, dsv4p ATE have NO rescue path.

R1731 direction: 向195目标渐进. Step 2: 155→165.

- 165→peer-fb gets 95s usable (165-70=95), still <125 but improving
- glm5_2 peer-fb already broken (72<122, unrelated to BUDGET)
- OK path unaffected (p50=8.8s, p95=18.9s << 165s)
- 零容器漂移

## 修改

| 参数 | 旧值 | 新值 | Δ |
|------|------|------|---|
| TIER_TIMEOUT_BUDGET_S | 155 | 165 | +10s |

## 验证

- `docker exec nv_gw env | grep TIER_TIMEOUT_BUDGET_S` → 165 ✓
- `curl localhost:40006/health` → OK ✓
- 零容器漂移

## 铁律

只改HM1不改HM2.
## ⏳ 轮到HM1优化HM2
