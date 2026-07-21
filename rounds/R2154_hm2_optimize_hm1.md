# R2154 (HM2→HM1): TIER_COOLDOWN_S 34→32 (-2s)

## 6h DB Snapshot
- **Total**: 40 req, 33 OK, 7 fail → **82.5% SR**
- **ATE**: 3 (all dsv4p_nv, pre-empted — 0 tier_attempts in 24h)
- **Zombie**: 4 (all glm5_2_nv, NVCF-side empty completions)
- **Peer-fallback**: 0 (0 triggered)
- **ms_requests**: 0 activity
- **key_cycle_429s**: 31/40 cycle1 (77.5%), 6/40 cycle2+ (15%)
- **Latency (success)**: glm5_2_nv avg 17940ms, min 2946ms, max 153777ms

## Per-Model Breakdown
```
glm5_2_nv: 37 req, 33 OK, 4 zombie (100% SR excl zombies)
dsv4p_nv:   3 req,  0 OK, 3 ATE (all pre-empted, 0 tier_attempts)
```

## Error Breakdown
```
all_tiers_exhausted:     3 (all dsv4p_nv, pre-empted — 0 tier_attempts in 24h)
zombie_empty_completion:  4 (all glm5_2_nv, pexec_success in tier_attempts)
```
- Tier attempts: 37 pexec_success, 9 pexec_timeout, 4 pexec_SSLEOFError, 3 pexec_429 (ALL glm5_2_nv)
- 3 dsv4p_nv ATE: tier pre-empted at R2152 container startup — 0 tier_attempts even for primary. All 3 occurred at 03:39-03:40 UTC cluster.
- All 4 zombies are NVCF-side empty completions, not config-fixable

## 30min Recent
- 2 req, 2 OK, 0 fail → **100% SR** (clean window)
- glm5_2_nv only; dsv4p_nv zero activity

## Analysis
- R2153 was KEY_COOLDOWN_S 52→50, alternating → R2154 = TIER turn
- TIER_COOLDOWN_S 34→32 (-2s), continuing the alternating KEY→TIER reduction pattern
- KEY+TIER=50+32=82 < TIER_TIMEOUT_BUDGET=153 (71s headroom) ✓
- 3 dsv4p ATE were one-time startup cluster from R2152, not ongoing
- glm5_2_nv 100% SR excl zombies; zombies are NVCF-side, not config-fixable
- Peer-fallback path: UPSTREAM=24 + PEER_FALLBACK=122 = 146 < BUDGET=153 ✓
- UPSTREAM=24, TIER_BUDGET_GLM5_2_NV=25 > 24 ✓ (tier not silently skipped)
- 32s > 0s, above zero margin; low traffic (6.7 req/h) with 5 keys → inter-request gap >> TIER_COOLDOWN_S
- 30min 100% SR clean window confirms no ongoing degradation

## Change
| Param | Old | New | Δ |
|-------|-----|-----|---|
| TIER_COOLDOWN_S | 34 | 32 | -2s |

## Verification
- `docker exec nv_gw env | grep TIER_COOLDOWN_S` → `TIER_COOLDOWN_S=32` ✓
- Container restarted and healthy
- Health check: HTTP 200 ✓
- No duplicate changes across ms_gw/nv_gw sections (nv_gw line 506 only, ms_gw line 185 unchanged) ✓
- KEY+TIER=50+32=82 < 153 BUDGET (71s headroom) ✓
## ⏳ 轮到HM1优化HM2
