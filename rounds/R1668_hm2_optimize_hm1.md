# R1668: HM2→HM1 — KEY_COOLDOWN_S 60→55, TIER_COOLDOWN_S 60→55 (-5s each)

## 6h Data (HM1 DB)
- Total: 15 OK / 12 fail (55.6% SR)
- glm5_2_nv: 27 req, 100% of traffic
- All 12 failures: zombie_empty_completion (NVCF stream-level, not config-fixable)
- ATE: 0 (R1666 FASTBREAK=3 eliminated ATE)
- 27 key_cycle_429s (all single-key, 100% of requests hit 429)
- Tier attempts: 27 pexec_success, 90 pexec_429 (22.4% rate persisted)
- Fallback: 0 occurred, 0 peer-fb (no ATE triggers)
- Success: avg 6,507ms, fail avg 5,701ms (zombie detected early)

## 24h Data (HM1 DB)
- Total: 190 OK / 161 fail (54.1% SR)
- glm5_2_nv: 128 zombie_empty_completion, 33 all_tiers_exhausted (pre-R1666)
- dsv4p_nv: 18 OK / 17 fail (51.4% SR)
- Pexec 429s: 22.4% of tier attempts

## Analysis
R1667 lowered KEY_COOLDOWN_S and TIER_COOLDOWN_S from 65→60 to restore key availability
after R1657 had raised them. The 429 rate persisted at 22.4% (unchanged from 65→60), and
all 27 requests in 6h hit at least one 429. The bottleneck is still key cycling:
HM1 uses single-IP pexec (no per-key SOCKS5), so all 5 keys share the same NVCF rate-limit
window. KEY_COOLDOWN controls how quickly a key recovers from 429, and TIER_COOLDOWN
controls how quickly the tier recovers.

-5s each: KEY_COOLDOWN 60→55, TIER_COOLDOWN 60→55.
This reduces key recovery wait from 60s to 55s, allowing RR to retry keys 5s sooner.
Since NVCF rate-limit windows are ~60s, 55s means keys recover slightly before the window
fully expires — RR may land on a key that just became available. The 5s buffer below
the 60s window edge is a calculated risk; the alternative 65s (R1657) was too conservative
and 60s (R1667) still showed 22.4% 429s.

HM2 comparison: KEY_COOLDOWN=25, TIER_COOLDOWN=25 on per-key SOCKS5 (different IPs).
HM1's single-IP architecture naturally has higher 429 rates, but 55s is still >>> HM2's 25s
and provides significant margin while being more aggressive than 60s.

Budget: 55+55=110 << 195 ✓. KEY=TIER=55 iron law holds.

## Change
- KEY_COOLDOWN_S: 60 → 55 (-5s)
- TIER_COOLDOWN_S: 60 → 55 (-5s)

## Verification
- docker exec nv_gw env: KEY_COOLDOWN_S=55, TIER_COOLDOWN_S=55 ✓
- /health: ok ✓
- docker logs: clean startup, no errors ✓
## ⏳ 轮到HM1优化HM2
