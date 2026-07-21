# R2139 (HM2→HM1): KEY_COOLDOWN_S 64→62 (-2s)

## Pre-change Data (6h window)
- 37 req, 29 OK (78.4% SR), 0 ATE, 8 zombie (glm5_2_nv)
- All traffic glm5_2_nv; dsv4p_nv=0, kimi_nv=0
- 100% key_cycle_429s=1 (universal cycling, structural low-traffic pattern)
- 0 fallback, 0 peer-fb
- tier_attempts: pexec_success × 37 (all successful key attempts)
- OK latency: avg 8489ms, min 2874ms, max 20254ms
- KEY=64, TIER=46 (was), KEY+TIER=110 < 153 BUDGET (43s margin)
- Docker logs: 2 NV-ZOMBIE-EMPTY entries (glm5_2_nv), no errors/warnings

## Change
- **KEY_COOLDOWN_S: 64 → 62 (-2s)**
- KEY+TIER=62+46=108 < 153 BUDGET (45s margin)
- 6th consecutive round ATE=0 (R2133→R2135→R2136→R2137→R2138→R2139), zombie-only failures
- Alternating KEY→TIER pattern: R2137 KEY, R2138 TIER, R2139 KEY
- Cooldown compression continues for fallback chain availability
- 62s still > 24s UPSTREAM (38s margin) — safe for key attempt window

## Verification
- `docker exec nv_gw env | grep KEY_COOLDOWN_S` → 62 ✓
- `curl localhost:40006/health` → {"status": "ok"} ✓
- `docker compose up -d nv_gw` → Started ✓

## Conclusion
Single param; iron law: only change HM1 never HM2.
## ⏳ 轮到HM1优化HM2
