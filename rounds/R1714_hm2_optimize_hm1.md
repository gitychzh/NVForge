# R1714: HM2→HM1 — PEER_FALLBACK_TIMEOUT 72→125 (+53s)

## 数据 (6h window, 2026-07-17 10:33–16:42 UTC)

- 59 requests: 49 OK (83.1%), 10 zombie_empty_completion (16.9%), 0 ATE, 0 fallback
- 100% key_cycle_429s: 55/59 cycle=1, 4/59 cycle=2 — k1/k4 share egress IP 134.195.101.193
- 10 zombies: all glm5_2_nv, all >250K chars (284K-315K), 4.9-13.4s, ~30 min cadence
- All requests: glm5_2_nv (no dsv4p_nv traffic in window)
- Success: p50=9.5s, p95=35.5s, avg=12.5s
- cc4101: 正常, no errors
- peer-fallback: 0 triggered

## 根因分析

R1713 deployed BIG_INPUT breaker (FAIL_N=1, COOLDOWN=1800) to intercept glm5_2_nv zombies. When the breaker is OPEN, it returns `all_tiers_exhausted` immediately, triggering peer-fallback to HM2. But there's a critical constraint violation:

- HM1 `PEER_FALLBACK_TIMEOUT=72`
- HM2 `NVU_TIER_BUDGET_GLM5_2_NV=120`
- Constraint: `PEER_FALLBACK_TIMEOUT ≥ peer's BUDGET + 2s = 122`
- **72 < 122 → peer-fallback guaranteed timeout at 72s, HM2 needs 120s**

R1713's fix is incomplete without fixing this. When BIG_INPUT breaker opens, peer-fallback times out at 72s before HM2 can complete its key cycle — wasting 72s instead of saving time.

## 优化

**NVU_PEER_FALLBACK_TIMEOUT 72→125 (+53s)**

Budget verification:
- BIG_INPUT breaker path: 0s (immediate return) + 125s = 125s < 165s (TIER_TIMEOUT_BUDGET_S) ✓
- dsv4p_nv ATE path: 70s + 125s = 195s, capped at 165s → peer-fb gets 95s > 72s (HM2 dsv4p BUDGET) ✓
- glm5_2_nv path: 120s + 125s = 245s, capped at 165s → but BIG_INPUT breaker returns immediately so total < 165s ✓

125 = 120 (HM2 glm5_2 BUDGET) + 2s (network buffer) + 3s (safety margin).

## 验证

- `docker exec nv_gw env`: PEER_FALLBACK_TIMEOUT=125 ✓
- `curl localhost:40006/health`: {"status":"ok"} ✓
- Restart: Container nv_gw Recreated+Started ✓

## 铁律
只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
