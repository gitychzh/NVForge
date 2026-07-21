# R2153 (HM2→HM1): KEY_COOLDOWN_S 52→50 (-2s)

## 6h DB Snapshot
- **Total**: 40 req, 33 OK, 7 fail → **82.5% SR**
- **ATE**: 3 (all dsv4p_nv, pre-empted — 0 tier_attempts in 24h)
- **Zombie**: 4 (all glm5_2_nv, NVCF-side empty completions)
- **Peer-fallback**: 0 (0 triggered)
- **ms_requests**: 0 activity
- **key_cycle_429s**: 37/40 (92.5%, near-universal, benign)
- **Latency (success)**: avg 17940ms, min 2946ms, max 153777ms

## Error Breakdown
```
all_tiers_exhausted: 3 (all dsv4p_nv, pre-empted — 0 tier_attempts in 24h)
zombie_empty_completion: 4 (all glm5_2_nv, pexec_success in tier_attempts)
```
- Tier attempts: 37 pexec_success, 9 pexec_timeout, 4 pexec_SSLEOFError, 3 pexec_429 (ALL glm5_2_nv)
- 3 dsv4p_nv ATE: tier pre-empted at R2152 container startup — 0 tier_attempts even for primary. All 3 occurred at 03:39-03:40 UTC cluster.
- All 4 zombies are NVCF-side empty completions, not config-fixable

## 30min Recent
- 7 req, 4 OK, 3 fail → **57.1% SR** (3 recent zombies + 4 OK)
- glm5_2_nv still active; dsv4p_nv and kimi_nv have 0 recent requests

## Analysis
- R2152 broke the 15-round zero-ATE streak with 3 dsv4p_nv pre-empted ATE at startup — one-time event, not ongoing
- R2145 (KEY 58→56), R2146 (TIER 40→38), R2148 (KEY 56→54), R2149 (TIER 38→36), R2151 (KEY 54→52), R2152 (TIER 36→34) → R2153 hits KEY turn
- KEY+TIER=50+34=84 < TIER_TIMEOUT_BUDGET=153 (69s headroom) ✓
- Peer-fallback path: UPSTREAM=24 + PEER_FALLBACK=122 = 146 < BUDGET=153 ✓
- UPSTREAM=24, TIER_BUDGET_GLM5_2_NV=25 > 24 ✓ (tier not silently skipped)
- 50s > 24s UPSTREAM safe margin ✓
- Low traffic (6.7 req/h) with 5 keys → inter-request gap >> KEY_COOLDOWN_S
- Near-universal key_cycle_429s=1 is benign at this traffic level
- Only glm5_2_nv active in window; dsv4p_nv had 3 cluster ATE in 30s, zero since

## Change
| Param | Old | New | Δ |
|-------|-----|-----|---|
| KEY_COOLDOWN_S | 52 | 50 | -2s |

## Verification
- `docker exec nv_gw env | grep KEY_COOLDOWN_S` → `KEY_COOLDOWN_S=50` ✓
- Container restarted and healthy
- Health check: HTTP 200 ✓
- No duplicate changes across ms_gw/nv_gw sections (nv_gw line 500 only, ms_gw line 186 unchanged) ✓
- KEY+TIER=50+34=84 < 153 BUDGET (69s headroom) ✓

## ⏳ 轮到HM1优化HM2
