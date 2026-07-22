# R2242: NVU_TIER_BUDGET_DSV4P_NV 94→96 (+2s)

## Role: HM2 → HM1 optimization

## 6h Data (2026-07-22 09:15–15:15 UTC)
- **Total**: 43 req, 30 OK (69.8% SR), 13 fail
- **dsv4p_nv**: 14 req, 8 OK (57.1% SR), 6 ATE
  - 5 phantom ATE (status=200, saved by peer-fb to HM2): 5-47s durations
  - 1 real ATE (status=502): 94,038ms — exactly hit BUDGET=94, exhausted after 3 keys
- **glm5_2_nv**: 29 req, 22 OK (75.9% SR), 4 zombie + 3 ATE. 89.7% key cycling (26/29 with key_cycle≥1)
- **Peer-fb**: dsv4p ATE → peer-fb to HM2 saved 5/6 (log shows NV-PEER-FB peer fallback OK: status=200 bytes=1567)

## Key ATE Analysis
The real dsv4p ATE (94,038ms) exactly exhausted BUDGET=94:
```
attempt 1 (k1): 29,590ms success → phantom ATE later
attempt 2 (k2): 504 gateway timeout → cycle
attempt 3 (k3): timeout 28,270ms → budget exceeded at 94,053ms total
```
With KEY_COOLDOWN=10, each key attempt costs UPSTREAM_TIMEOUT=24s. 
KEY(10)+UPSTREAM(24)×3=102 > BUDGET(94) → 3rd key gets only 94−68=26s (just 2s above UPSTREAM=24). 
BUDGET=96 → 3rd key gets 96−68=28s (4s above UPSTREAM, +14s total margin).

## Change
**NVU_TIER_BUDGET_DSV4P_NV: 94 → 96 (+2s)** at line 658

- Budget check: KEY(10)+TIER(0)+DSV4P(96)=106 << TIER_BUDGET(157) (51s margin ✓)
- Per-key headroom: UPSTREAM(24)+KEY(10)=34 → 3 keys = 102; BUDGET=96 → 3rd key = 30s (6s above UPSTREAM ✓)
- Single param; iron law: only change HM1 never HM2

## Live Verification
- `docker exec nv_gw env | grep NVU_TIER_BUDGET_DSV4P_NV` → **96** ✓
- `curl http://localhost:40006/health` → **200** ✓
- `docker compose config` → **valid** ✓

## ⏳ 轮到HM1优化HM2