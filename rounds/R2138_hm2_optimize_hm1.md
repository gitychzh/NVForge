# R2138 (HM2→HM1): TIER_COOLDOWN_S 48→46 (-2s)

## Pre-change Data (6h window)
- 36 req, 28 OK (77.8% SR), 0 ATE, 8 zombie (glm5_2_nv)
- All traffic glm5_2_nv; dsv4p_nv=24 in 24h (very low)
- 100% key_cycle_429s=1 (universal cycling, structural low-traffic pattern)
- 0 fallback, 0 peer-fb
- tier_attempts: pexec_success×36 (all successful key attempts)
- KEY=64, TIER=48 (was), KEY+TIER=112 < 153 BUDGET (41s margin)

## Change
- **TIER_COOLDOWN_S: 48 → 46 (-2s)**
- KEY+TIER=64+46=110 < 153 BUDGET (43s margin)
- 6th consecutive round ATE=0, zombie-only failures
- Cooldown compression continues for fallback chain availability
- 46s still > 24s UPSTREAM (22s margin) — safe for key attempt window

## Verification
- `docker exec nv_gw env | grep TIER_COOLDOWN_S` → 46 ✓
- `curl localhost:40006/health` → {"status": "ok"} ✓
- docker compose up -d nv_gw → Started ✓

## Conclusion
Single param; iron law: only change HM1 never HM2.
## ⏳ 轮到HM1优化HM2
