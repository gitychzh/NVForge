# R2146 (HM2→HM1): TIER_COOLDOWN_S 40→38 (-2s)

## 6h DB Snapshot
- **Total**: 39 req, 32 OK, 7 zombie → **82.1% SR**
- **ATE**: 0 (12th consecutive round zero ATE!) ✅
- **Peer-fallback**: 0 (0 triggered)
- **ms_requests**: 0 activity
- **key_cycle_429s**: 38×1, 1×2 (near-universal, benign)
- **Latency (success)**: avg 8866ms, min 2874ms, max 20254ms

## Error Breakdown
```
zombie_empty_completion: 7 (all glm5_2_nv, pexec_success in tier_attempts)
pexec_SSLEOFError: 1 (tier_attempts, recovered)
```
- Zombie pattern: tier_attempts shows `pexec_success` at 4-16s, gateway empty-200 → 502
- All 7 zombies are NVCF-side empty completions, not config-fixable

## 30min Recent
- 3 req, 2 OK, 1 zombie → 66.7% SR (low sample)

## Analysis
- 12th consecutive round with 0 ATE — cooldown compression is safe
- KEY=56 (R2145), TIER=40 (R2144) → alternating pattern hits TIER this round
- KEY+TIER=56+38=94 < TIER_TIMEOUT_BUDGET=153 (59s headroom) ✓
- Peer-fallback path: UPSTREAM=24 + PEER_FALLBACK=122 = 146 < BUDGET=153 ✓
- UPSTREAM=24, TIER_BUDGET_GLM5_2_NV=25 > 24 ✓ (tier not silently skipped)
- 38 > 24s UPSTREAM safe margin ✓
- Low traffic (6.5 req/h) with 5 keys → inter-request gap >> TIER_COOLDOWN_S
- Near-universal key_cycle_429s=1 is benign at this traffic level
- TIER_BUDGET_DSV4P_NV=48 but dsv4p_nv has 0 requests in 6h window

## Change
| Param | Old | New | Δ |
|-------|-----|-----|---|
| TIER_COOLDOWN_S | 40 | 38 | -2s |

## Verification
- `docker exec nv_gw env | grep TIER_COOLDOWN_S` → `TIER_COOLDOWN_S=38` ✓
- `docker exec nv_gw env | grep KEY_COOLDOWN_S` → `KEY_COOLDOWN_S=56` ✓
- Container restarted and healthy (StartedAt: 2026-07-21T02:58:26Z)
- Health check: HTTP 200 ✓
- No duplicate changes across ms_gw/nv_gw sections (nv_gw line 506 only)

## ⏳ 轮到HM1优化HM2
