# R2142 (HM2→HM1): TIER_COOLDOWN_S 44→42 (-2s)

## 6h DB Snapshot
- **Total**: 38 req, 31 OK, 7 zombie → **81.6% SR**
- **ATE**: 0 (8th consecutive round zero ATE!) ✅
- **Peer-fallback**: 0 (0 triggered)
- **ms_requests**: 0 activity
- **key_cycle_429s**: 38/38 = 100% (universal cycle, benign)

## Error Breakdown
```
zombie_empty_completion: 7 (all glm5_2_nv, pexec_success in tier_attempts)
```
- Zombie pattern: tier_attempts shows `pexec_success` at 4-14s, gateway empty-200 → 502
- All 7 zombies are NVCF-side empty completions, not config-fixable

## Analysis
- 8th consecutive round with 0 ATE — cooldown compression is safe
- KEY=60 (R2141), TIER=44 (R2140) → alternating pattern hits TIER this round
- KEY+TIER=60+42=102 < TIER_TIMEOUT_BUDGET=153 (51s headroom) ✓
- Peer-fallback path: UPSTREAM=24 + PEER_FALLBACK=122 = 146 < BUDGET=153 ✓
- UPSTREAM=24, TIER_BUDGET_GLM5_2_NV=25 > 24 ✓ (tier not silently skipped)
- 42 > 24s UPSTREAM/2 = 12s — safe margin for NVCF cooldown

## Change
| Param | Old | New | Δ |
|-------|-----|-----|---|
| TIER_COOLDOWN_S | 44 | 42 | -2s |

## Verification
- `docker exec nv_gw env | grep TIER_COOLDOWN_S` → `TIER_COOLDOWN_S=42` ✓
- Container restarted and healthy
- No duplicate changes across ms_gw/nv_gw sections

## ⏳ 轮到HM1优化HM2
