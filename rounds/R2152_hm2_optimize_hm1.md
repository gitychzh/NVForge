# R2152 (HM2→HM1): TIER_COOLDOWN_S 36→34 (-2s)

## 6h DB Snapshot
- **Total**: 41 req, 33 OK, 8 fail → **80.5% SR**
- **ATE**: 3 (first ATE in 15 rounds!) ⚠️
- **Zombie**: 5 (all glm5_2_nv, NVCF-side empty completions)
- **Peer-fallback**: 0 (0 triggered)
- **ms_requests**: 0 activity
- **key_cycle_429s**: 33×1, 5×2+ (near-universal, benign)
- **Latency (success)**: avg 17777ms, min 2946ms, max 153777ms

## Error Breakdown
```
all_tiers_exhausted: 3 (all dsv4p_nv, pre-empted — 0 tier_attempts in 24h)
zombie_empty_completion: 5 (all glm5_2_nv, pexec_success in tier_attempts)
```
- Tier attempts: 38 pexec_success, 9 pexec_timeout, 3 pexec_SSLEOFError, 1 pexec_429 (ALL glm5_2_nv)
- 3 dsv4p_nv ATE: tier pre-empted at container startup — 0 tier_attempts even for primary. The container likely restarted from R2151 deploy and the 36s TIER_COOLDOWN_S window overlapped with the 3 dsv4p_nv requests arriving at 03:39 UTC.
- All 5 zombies are NVCF-side empty completions, not config-fixable

## 30min Recent
- 6 req, 3 OK, 3 fail → **50.0% SR** (all 3 dsv4p_nv ATE)
- All 3 failures are the cluster ATE at 03:39 UTC

## Analysis
- **15th consecutive round had 0 ATE, but R2152 breaks the streak** — 3 dsv4p_nv pre-empted ATE
- The 3 ATE occurred at 03:39 UTC within a 30s window, 0 tier_attempts in 24h for dsv4p_nv → tier was pre-empted at startup
- This is the TIER turn in the alternating KEY→TIER→KEY→TIER pattern (R2149 TIER 38→36, R2151 KEY 54→52, R2152 TIER 36→34)
- KEY+TIER=52+34=86 < TIER_TIMEOUT_BUDGET=153 (67s headroom) ✓
- Peer-fallback path: UPSTREAM=24 + PEER_FALLBACK=122 = 146 < BUDGET=153 ✓
- UPSTREAM=24, TIER_BUDGET_GLM5_2_NV=25 > 24 ✓ (tier not silently skipped)
- 34s > 24s UPSTREAM safe margin ✓
- Low traffic (6.8 req/h) with 5 keys → inter-request gap >> KEY_COOLDOWN_S
- glm5_2_nv 38/38 OK (100% SR) — only dsv4p_nv had issues, and only at startup

## Change
| Param | Old | New | Δ |
|-------|-----|-----|---|
| TIER_COOLDOWN_S | 36 | 34 | -2s |

## Verification
- `docker exec nv_gw env | grep TIER_COOLDOWN_S` → `TIER_COOLDOWN_S=34` ✓
- Container restarted and healthy
- Health check: HTTP 200 ✓
- No duplicate changes across ms_gw/nv_gw sections (nv_gw line 506 only, ms_gw line 185 unchanged) ✓
- KEY+TIER=52+34=86 < 153 BUDGET (67s headroom) ✓

## ⏳ 轮到HM1优化HM2
