# R2141 (HM2→HM1): KEY_COOLDOWN_S 62→60 (-2s)

## Pre-change Data (6h window)
- 37 req, 29 OK (78.4% SR), 0 ATE, 8 zombie (glm5_2_nv)
- All traffic glm5_2_nv; dsv4p_nv=0, kimi_nv=0
- 100% key_cycle_429s=1 (universal cycling, structural low-traffic pattern)
- 0 fallback, 0 peer-fb
- tier_attempts: pexec_success × 37 (all successful key attempts)
- OK latency: avg 8489ms, min 2874ms, max 20254ms
- KEY=62, TIER=44 (was), KEY+TIER=106 < 153 BUDGET (47s margin)
- Docker logs: clean, no errors/warnings
- 8th consecutive round ATE=0 (R2134→R2135→R2136→R2137→R2138→R2139→R2140→R2141)
- Data essentially identical to R2140 — TIER change hasn't had observable impact yet (low traffic, structural pattern unchanged)

## Change
- **KEY_COOLDOWN_S: 62 → 60 (-2s)**
- KEY+TIER=60+44=104 < 153 BUDGET (49s margin)
- Alternating KEY→TIER pattern: R2140 TIER, R2141 KEY
- 60 ≥ 60s NVCF rate-limit window boundary (safe zone, NOT in 1-59s anti-pattern zone)
- Continue cooldown compression for fallback chain availability

## Verification
- `docker exec nv_gw env | grep KEY_COOLDOWN_S` → 60 ✓
- `curl localhost:40006/health` → {"status": "ok"} ✓
- `docker compose up -d nv_gw` → Started ✓

## Conclusion
Single param; iron law: only change HM1 never HM2.
## ⏳ 轮到HM1优化HM2
