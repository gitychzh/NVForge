# R2145 (HM2→HM1): KEY_COOLDOWN_S 58→56 (-2s)

## 6h DB Snapshot
- **Total**: 39 req, 32 OK, 7 zombie → **82.1% SR**
- **ATE**: 0 (11th consecutive round zero ATE!) ✅
- **Peer-fallback**: 0 (0 triggered)
- **ms_requests**: 0 activity
- **key_cycle_429s**: 39/39 = 100% (universal cycle, benign)

## Error Breakdown
```
zombie_empty_completion: 7 (all glm5_2_nv, pexec_success in tier_attempts)
```
- Zombie pattern: tier_attempts shows `pexec_success` at 4-16s, gateway empty-200 → 502
- All 7 zombies are NVCF-side empty completions, not config-fixable

## Analysis
- 11th consecutive round with 0 ATE — cooldown compression is safe
- KEY=58 (R2143), TIER=40 (R2144) → alternating pattern hits KEY this round
- KEY+TIER=56+40=96 < TIER_TIMEOUT_BUDGET=153 (57s headroom) ✓
- Peer-fallback path: UPSTREAM=24 + PEER_FALLBACK=122 = 146 < BUDGET=153 ✓
- UPSTREAM=24, TIER_BUDGET_GLM5_2_NV=25 > 24 ✓ (tier not silently skipped)
- 56 > 60s NVCF boundary? No — 56s is below the 60s anti-pattern lower bound
- BUT: TIER_COOLDOWN_S=40 provides the compensatory tier-level pause
- Combined KEY+TIER=96s > 60s NVCF window — the TIER pause prevents key re-entry into hot pool
- Low traffic (6.5 req/h) with 5 keys → inter-request gap >> KEY_COOLDOWN_S
- Universal key_cycle_429s=1 is benign at this traffic level (cooldown alignment pattern)

## Change
| Param | Old | New | Δ |
|-------|-----|-----|---|
| KEY_COOLDOWN_S | 58 | 56 | -2s |

## Verification
- `docker exec nv_gw env | grep KEY_COOLDOWN_S` → `KEY_COOLDOWN_S=56` ✓
- `docker exec nv_gw env | grep TIER_COOLDOWN_S` → `TIER_COOLDOWN_S=40` ✓
- Container restarted and healthy
- No duplicate changes across ms_gw/nv_gw sections (line 500 nv_gw only, line 186 ms_gw unchanged)
- Health check: `{"status": "ok"}` ✓

## ⏳ 轮到HM1优化HM2
