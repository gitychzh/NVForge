# R2125 (HM2→HM1): KEY_COOLDOWN_S 66→64 (-2s)

## Change
- **KEY_COOLDOWN_S**: 66 → 64 (-2s)
- **TYPE**: Single param; storm-recovery walk-back
- **IRON LAW**: Only change HM1, never HM2

## Pre-R2125 Data (6h DB, mostly pre-R2122 since container restart ~9min ago)
| Model | Req | OK | Fail | SR | Note |
|-------|-----|-----|------|-----|------|
| dsv4p_nv | 19 | 10 | 9 | 52.6% | 9 ATE all ~20s all_tiers_exhausted, tiers_tried=1, fallback_occurred=0 |
| glm5_2_nv | 29 | 18 | 11 | 62.1% | 11 zombie_empty_completion, NVCF function-level |
| **Total** | **48** | **28** | **20** | **58.3%** | |

- 0 kimi_nv traffic, 0 peer-fb requests, 0 SSL errors, 0 429 rate limits
- dsv4p ATE all single-tier {dsv4p_nv}, no fallback tiers attempted
- All ATE cluster ~20s, pre-R2122 deployment window

## Budget Analysis
- KEY+TIER = 64+62 = 126 < 153 BUDGET (27s margin)
- Previous: KEY+TIER = 66+62 = 128 < 153 BUDGET (25s margin)
- 27s margin >> actual OK max ~14s (dsv4p) / ~105s (glm5_2), very safe

## Verification
- Container: `docker compose up -d --force-recreate nv_gw` → Recreated/Started ✓
- env: `KEY_COOLDOWN_S=64` ✓
- /health: `{"status":"ok"}` ✓
- StartedAt: 2026-07-20T22:12:??Z (new container)

## Rationale
Continuing storm-recovery walk-back. Storm self-healed (0 429, 0 SSL in 6h window). KEY was raised during storm defense (R2115: 63→66, R2117: 66→70, R2119: 70→73, R2121: 73→68, R2122: 68→66). Now walking back: 66→64. KEY+TIER=64+62=126 << 153 BUDGET with 27s headroom. Single param; iron law: only change HM1 never HM2.