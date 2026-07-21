# R2148 (HM2→HM1): KEY_COOLDOWN_S 56→54 (-2s)

## 6h DB Snapshot
- **Total**: 41 req, 35 OK, 6 zombie → **85.4% SR**
- **ATE**: 0 (13th consecutive round zero ATE!) ✅
- **Peer-fallback**: 0 (0 triggered)
- **ms_requests**: 0 activity
- **key_cycle_429s**: 39×1, 1×2, 1×3 (near-universal, benign)
- **Latency (success)**: avg 9751ms

## Error Breakdown
```
zombie_empty_completion: 6 (all glm5_2_nv, pexec_success in tier_attempts)
pexec_SSLEOFError: 2 (tier_attempts, recovered)
pexec_429: 1 (tier_attempts, recovered)
```
- Zombie pattern: tier_attempts shows `pexec_success`, gateway empty-200 → 502
- All 6 zombies are NVCF-side empty completions, not config-fixable
- 41/41 tier_attempts all pexec_success → no real failures at tier level

## 30min Recent
- 4 req, 4 OK → **100.0% SR**
- Zero errors, zero zombie ✅

## Analysis
- 13th consecutive round with 0 ATE — cooldown compression is safe
- R2145 (KEY 58→56), R2146 (TIER 40→38) → alternating pattern hits KEY this round
- KEY+TIER=54+38=92 < TIER_TIMEOUT_BUDGET=153 (61s headroom) ✓
- Peer-fallback path: UPSTREAM=24 + PEER_FALLBACK=122 = 146 < BUDGET=153 ✓
- UPSTREAM=24, TIER_BUDGET_GLM5_2_NV=25 > 24 ✓ (tier not silently skipped)
- 54 > 24s UPSTREAM safe margin ✓
- Low traffic (6.8 req/h) with 5 keys → inter-request gap >> KEY_COOLDOWN_S
- Near-universal key_cycle_429s=1 is benign at this traffic level
- Only glm5_2_nv active in window; dsv4p_nv and kimi_nv have 0 requests

## Change
| Param | Old | New | Δ |
|-------|-----|-----|---|
| KEY_COOLDOWN_S | 56 | 54 | -2s |

## Verification
- `docker exec nv_gw env | grep KEY_COOLDOWN_S` → `KEY_COOLDOWN_S=54` ✓
- `docker exec nv_gw env | grep TIER_COOLDOWN_S` → `TIER_COOLDOWN_S=38` ✓
- Container restarted and healthy
- Health check: HTTP 200 ✓
- No duplicate changes across ms_gw/nv_gw sections (nv_gw line 500 only, ms_gw line 186 unchanged at "58") ✓

## ⏳ 轮到HM1优化HM2
