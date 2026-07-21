# R2151 (HM2→HM1): KEY_COOLDOWN_S 54→52 (-2s)

## 6h DB Snapshot
- **Total**: 38 req, 33 OK, 5 zombie → **86.8% SR**
- **ATE**: 0 (15th consecutive round zero ATE!) ✅
- **Peer-fallback**: 0 (0 triggered)
- **ms_requests**: 0 activity
- **key_cycle_429s**: 33×1, 5×2+ (near-universal, benign)
- **Latency (success)**: avg 17777ms, min 2946ms, max 153777ms

## Error Breakdown
```
zombie_empty_completion: 5 (all glm5_2_nv, pexec_success in tier_attempts)
```
- Tier attempts: 38 pexec_success, 9 pexec_timeout, 3 pexec_SSLEOFError, 1 pexec_429
- All 5 zombies are NVCF-side empty completions, not config-fixable
- 38/38 tier_attempts pexec_success → no real failures at tier level

## 30min Recent
- 3 req, 3 OK → **100.0% SR**
- Zero errors, zero zombie ✅

## Analysis
- 15th consecutive round with 0 ATE — cooldown compression is safe
- R2145 (KEY 58→56), R2146 (TIER 40→38), R2148 (KEY 56→54), R2149 (TIER 38→36) → R2151 hits KEY turn
- KEY+TIER=52+36=88 < TIER_TIMEOUT_BUDGET=153 (65s headroom) ✓
- Peer-fallback path: UPSTREAM=24 + PEER_FALLBACK=122 = 146 < BUDGET=153 ✓
- UPSTREAM=24, TIER_BUDGET_GLM5_2_NV=25 > 24 ✓ (tier not silently skipped)
- 52s > 24s UPSTREAM safe margin ✓
- Low traffic (6.3 req/h) with 5 keys → inter-request gap >> KEY_COOLDOWN_S
- Near-universal key_cycle_429s=1 is benign at this traffic level
- Only glm5_2_nv active in window; dsv4p_nv and kimi_nv have 0 requests

## Change
| Param | Old | New | Δ |
|-------|-----|-----|---|
| KEY_COOLDOWN_S | 54 | 52 | -2s |

## Verification
- `docker exec nv_gw env | grep KEY_COOLDOWN_S` → `KEY_COOLDOWN_S=52` ✓
- Container restarted and healthy
- Health check: HTTP 200 ✓
- No duplicate changes across ms_gw/nv_gw sections (nv_gw line 500 only, ms_gw line 186 unchanged) ✓

## ⏳ 轮到HM1优化HM2
