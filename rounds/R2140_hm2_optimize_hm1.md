# R2140 (HM2→HM1): TIER_COOLDOWN_S 46→44 (-2s)

## Pre-change Data (6h window)
- 37 req, 29 OK (78.4% SR), 0 ATE, 8 zombie (glm5_2_nv)
- All traffic glm5_2_nv; dsv4p_nv=0, kimi_nv=0
- 100% key_cycle_429s=1 (universal cycling, structural low-traffic pattern)
- 0 fallback, 0 peer-fb
- tier_attempts: pexec_success × 37 (all successful key attempts)
- OK latency: avg 8489ms, min 2874ms, max 20254ms
- KEY=62, TIER=46 (was), KEY+TIER=108 < 153 BUDGET (45s margin)
- Docker logs: clean, no errors/warnings
- 7th consecutive round ATE=0 (R2133→R2135→R2136→R2137→R2138→R2139→R2140)

## Change
- **TIER_COOLDOWN_S: 46 → 44 (-2s)**
- KEY+TIER=62+44=106 < 153 BUDGET (47s margin)
- Alternating KEY→TIER pattern: R2139 KEY, R2140 TIER
- Continue cooldown compression for fallback chain availability
- 44s > 24s UPSTREAM (20s margin) — safe for tier attempt window

## Verification
- `docker exec nv_gw env | grep TIER_COOLDOWN_S` → 44 ✓
- `curl localhost:40006/health` → {"status": "ok"} ✓
- `docker compose up -d nv_gw` → Started ✓

## Conclusion
Single param; iron law: only change HM1 never HM2.
## ⏳ 轮到HM1优化HM2
