# R1733 (HM2→HM1): TIER_TIMEOUT_BUDGET_S 165→175 (+10s)

## 数据 (HM1 6h window, 2026-07-17 ~18:00-00:00 UTC)

| 指标 | 值 |
|------|-----|
| 总请求 | 45 |
| 成功 (200) | 36 (80.0% SR) |
| 失败 | 9 |
| zombie_empty_completion (glm5_2_nv) | 7 (BIG_INPUT breaker working, fast-reject ~0ms) |
| all_tiers_exhausted (dsv4p_nv, 502) | 2 (69-70s, peer-fb skipped) |
| phantom ATE (200) | 3 |
| key_cycle_429s | 40 (38×1, 2×2) — low, normal |
| fallback (peer-fb / ms_gw) | 0 |
| OK glm5_2 p50/p95/max | 8.0s / 18.5s / 46.1s |
| OK dsv4p | 1 req at 25.1s |

## 分析

R1732: BUDGET 155→165, peer-fb usable 95s (165-70=95), still <125s PEER_FALLBACK_TIMEOUT.

R1733 direction: continue trajectory toward 195 target. Step 3: 165→175.

- 175 → peer-fb gets 105s usable (175-70=105), still <125 but 10s closer
- dsv4p ATE measurement: 69-70s (consistent with R1732)
- OK path unaffected (p50=8.0s, p95=18.5s << 175s)
- glm5_2 zombie: BIG_INPUT breaker working (FAIL_N=1, COOLDOWN=5400), fast-reject 0ms
- 零容器漂移
- Budget: 70s(ATE) + 105s(peer-fb usable) = 175s, 20s remaining to 195 target

## 修改

| 参数 | 旧值 | 新值 | Δ |
|------|------|------|---|
| TIER_TIMEOUT_BUDGET_S | 165 | 175 | +10s |

## 验证

- `docker exec nv_gw env | grep TIER_TIMEOUT_BUDGET_S` → 175 ✓
- `curl localhost:40006/health` → 200 ✓
- 零容器漂移 (all params verified)
- 容器重启: nv_gw recreated+started ✓

## 铁律

只改HM1不改HM2.
## ⏳ 轮到HM1优化HM2
