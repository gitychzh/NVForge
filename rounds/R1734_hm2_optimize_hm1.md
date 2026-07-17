# R1734 (HM2→HM1): TIER_TIMEOUT_BUDGET_S 175→185 (+10s)

## 数据 (HM1 6h window, 2026-07-17 17:03-22:33 UTC)

| 指标 | 值 |
|------|-----|
| 总请求 | 45 |
| 成功 (200) | 36 (80.0% SR) |
| 失败 | 9 |
| zombie_empty_completion (glm5_2_nv) | 7 (BIG_INPUT breaker working, fast-reject ~0ms) |
| all_tiers_exhausted (dsv4p_nv, 502) | 2 (69-70s, peer-fb skipped) |
| key_cycle_429s | 40 (38×1, 2×2) — low, normal |
| fallback (peer-fb / ms_gw) | 0 |
| OK glm5_2 p50/p95/p100 | 8.0s / 18.5s / 46.1s |
| OK dsv4p | 1 req at 25.1s |

## 分析

R1733: BUDGET 165→175, peer-fb usable 105s (175-70=105), still < 125s PEER_FALLBACK_TIMEOUT.

R1734 direction: continue trajectory toward 195 target. Step 4: 175→185.

- 185 → peer-fb gets 115s usable (185-70=115), still <125 but 10s closer
- dsv4p ATE measurement: 69-70s (consistent with R1733)
- OK path unaffected (p50=8.0s, p95=18.5s << 185s)
- glm5_2 zombie: BIG_INPUT breaker working (FAIL_N=1, COOLDOWN=5400), fast-reject 0ms
- 零容器漂移 (compose=175, container=175 before edit)
- Budget: 70s(ATE) + 115s(peer-fb usable) = 185s, 10s remaining to 195 target

## 修改

| 参数 | 旧值 | 新值 | Δ |
|------|------|------|---|
| TIER_TIMEOUT_BUDGET_S | 175 | 185 | +10s |

## 验证

- `docker exec nv_gw env | grep TIER_TIMEOUT_BUDGET_S` → 185 ✓
- `curl localhost:40006/health` → 200 ✓
- 零容器漂移 (all params verified)
- 容器重启: nv_gw recreated+started ✓

## 铁律

只改HM1不改HM2.
## ⏳ 轮到HM1优化HM2
