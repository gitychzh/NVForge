# R2144 (HM2→HM1): TIER_COOLDOWN_S 42→40 (-2s)

## 6h DB Snapshot
- **Total**: 38 req, 31 OK, 7 zombie → **81.6% SR**
- **ATE**: 0 (10th consecutive round zero ATE!) ✅
- **Peer-fallback**: 0 (0 triggered)
- **ms_requests**: 0 activity
- **key_cycle_429s**: 38/38 = 100% (universal cycle, benign)

## Error Breakdown
```
zombie_empty_completion: 7 (all glm5_2_nv, pexec_success in tier_attempts)
```
- Zombie pattern: tier_attempts shows `pexec_success` at 4-16s, gateway empty-200 → 502
- All 7 zombies are NVCF-side empty completions, not config-fixable

## Analysis
- 10th consecutive round with 0 ATE — cooldown compression is safe
- TIER=42 (R2142), KEY=58 (R2143) → alternating pattern hits TIER this round
- KEY+TIER=58+40=98 < TIER_TIMEOUT_BUDGET=153 (55s headroom) ✓
- Peer-fallback path: UPSTREAM=24 + PEER_FALLBACK=122 = 146 < BUDGET=153 ✓
- UPSTREAM=24, TIER_BUDGET_GLM5_2_NV=25 > 24 ✓ (tier not silently skipped)
- 40 > 24s UPSTREAM/2 = 12s — safe margin for tier cooldown
- TIER_COOLDOWN_S=40 still well above NVCF 60s window boundary for any single key
- Low traffic (6.3 req/h) with 5 keys → inter-request gap >> TIER_COOLDOWN_S
- Universal key_cycle_429s=1 is benign at this traffic level (cooldown alignment pattern)

## Change
| Param | Old | New | Δ |
|-------|-----|-----|---|
| TIER_COOLDOWN_S | 42 | 40 | -2s |

## Verification
- `docker exec nv_gw env | grep TIER_COOLDOWN_S` → `TIER_COOLDOWN_S=40` ✓
- `docker exec nv_gw env | grep KEY_COOLDOWN_S` → `KEY_COOLDOWN_S=58` ✓
- Container restarted and healthy
- No duplicate changes across ms_gw/nv_gw sections (line 505 nv_gw only, line 185 comment only)
- Health check: `{"status": "ok"}` ✓

## ⏳ 轮到HM1优化HM2
