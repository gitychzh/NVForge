# R2206 (HM2→HM1): KEY_COOLDOWN_S 6→0 (-6s)

## Data (6h window)
- 32 req / 22 OK (68.8% SR) / 10 zombie / 0 ATE
- glm5_2_nv: 28 req / 19 OK / 9 zombie | avg OK = 22553ms, max = 93401ms
- dsv4p_nv: 4 req / 3 OK / 1 zombie | avg OK = 27457ms
- 7 pexec_429s / 46 tier attempts = 15.2% 429 rate
- KEY_COOLDOWN_S=6, TIER_COOLDOWN_S=1

## Analysis
KEY_COOLDOWN_S=6 is in the **429 cycling anti-pattern zone** (1-59s). The skill reference documents this: KEY_COOLDOWN_S in 1-59s actively worsens 429 rates; must be either 0s (no cooldown) or ≥60s (above NVCF rate-limit window). At 6s, keys cycle too fast without waiting out the NVCF cooldown, causing 429 amplification (15.2% rate).

The OK max 93401ms with key_cycle_429s=6 confirms severe 429 amplification on outlier requests. TIER_COOLDOWN_S=1 is at floor, so the alternating KEY↔TIER pattern is stuck. Breaking the alternating pattern to fix the 429 anti-pattern is justified.

## Change
- KEY_COOLDOWN_S: 6 → 0 (-6s)
- KEY+TIER+GLM5_2 = 0+1+28 = 29 << 153 BUDGET (124s margin)
- Eliminates artificial cooldown; 5-key pool provides natural 429 protection
- Single param; iron law: only HM1

## Verification
- ✅ Compose: `KEY_COOLDOWN_S: "0"` at line 500
- ✅ Live env: `KEY_COOLDOWN_S=0` in docker exec nv_gw
- ✅ Container restarted successfully
## ⏳ 轮到HM1优化HM2
