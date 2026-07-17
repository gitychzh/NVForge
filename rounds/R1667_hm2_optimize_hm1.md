# R1667: HM2→HM1 — KEY_COOLDOWN_S 65→60, TIER_COOLDOWN_S 65→60 (-5s each)

## 24h Data (HM1 DB)
- Total: 189 OK / 160 fail (54.2% SR)
- glm5_2_nv: 171 OK / 143 fail (54.5% SR), 127 zombie_empty_completion, 33 all_tiers_exhausted
- dsv4p_nv: 18 OK / 17 fail (51.4% SR)
- 6h window: 15 OK / 12 fail (55.6% SR), 12 zombie, 0 ATE
- Tier attempts: 288 pexec_success, 90 pexec_429 (22.4%), 13 SSLEOFError, 10 empty_200
- 429 cascading: 289 requests with key_cycle_429s (225 single=1, 34×2, 16×3, 8×4, 4×5, 2×6)
- Fallback: 0 occurred, 64 attempted — all failed (ms_gw dsv4p_ms sync defect, no peer-fb triggers)
- Peer-fb: 0 used (no ATE in post-R1666 regime)

## Analysis
R1666's FASTBREAK=3 eliminated ATEs (0 in last 6h). The bottleneck is now pure zombie_empty_completion
(~79% of failures). Zombie is a stream-level detection: NVCF returns HTTP 200 with finish_reason=stop
but empty content_chars. The key cycle sees a success and never retries — FASTBREAK has no opportunity
to fire because the tier loop never sees a key-level failure.

R1657 raised KEY_COOLDOWN_S 60→65 (+5s) and TIER_COOLDOWN_S 60→65 (+5s) for 429-cascading margin.
But 24h data shows 22.4% 429 rate persisted (89/405 tier attempts), and 5s extra cooldown reduces
key availability by ~8% per key. With NVCF ai-glm-5_2 function ~50% zombie rate (5 keys, ~2-3 zombie
at any time), slower key recovery means the zombie keys stay cooling longer → healthy keys get hammered
harder → potentially more zombie from overuse.

Budget: KEY=60 + TIER=60 = 120 << 195 BUDGET ✓.
60s aligns with NVCF per-key 429 window floor (no buffer, but the window is rate-based not time-based).
KEY=TIER=60 per iron law.

## Change
- Parameter: NVU_KEY_COOLDOWN_S (compose line 498)
- Old: 65
- New: 60
- Also: NVU_TIER_COOLDOWN_S (compose line 502): 65→60 (aligned per iron law)
- Container: nv_gw restarted, env verified `KEY_COOLDOWN_S=60`, `TIER_COOLDOWN_S=60` ✓
- Health: `{"status":"ok"}` ✓

## Budget
- KEY_COOLDOWN_S=60 + TIER_COOLDOWN_S=60 = 120 << 195 ✓
- UPSTREAM_TIMEOUT=66, FASTBREAK=3, EMPTY_200_FASTBREAK=3 ✓
- BUDGET_GLM5=120, BUDGET_DSV4P=70 ✓
- PEER_FALLBACK_TIMEOUT=72 ✓
- 铁律:只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
