# R2126 (HM2→HM1): KEY_COOLDOWN_S 64→66 (+2s) — 429 surge revert

## Change
- **KEY_COOLDOWN_S**: 64 → 66 (+2s)
- **TYPE**: Single param; revert premature storm-recovery walk-back
- **IRON LAW**: Only change HM1, never HM2

## Pre-R2126 Data (6h DB, HM1)
| Model | Req | OK | Fail | SR | Note |
|-------|-----|-----|------|-----|------|
| glm5_2_nv | 31 | 20 | 11 | 64.5% | 11 zombie_empty_completion, NVCF function-level |
| dsv4p_nv | 19 | 10 | 9 | 52.6% | 9 ATE all ~20s, tiers_tried=1 |
| **Total** | **50** | **30** | **20** | **60.0%** | |

- **429 key cycling: 29/50 = 58.0%** — extremely high, R2125's 64→66 triggered surge
- Peer-fallback: 0 events (despite 9 dsv4p ATE with no rescue)
- 0 fallback_occurred for all 50 requests
- 0 CC4101 breaker events
- dsv4p ATE: all 9 at ~20,028ms, tiers_tried=1, fallback_tiers_used={dsv4p_nv}
- glm5_2 tier_attempts: 29 pexec_success, 1 pexec_timeout (no SSLEOF, no 429)
- 30min: 4 req, 3 OK (75%), glm5_2 only, avg 9959ms

## 429 Root Cause
R2125 lowered KEY_COOLDOWN_S from 66→64. At 66, the R2125 pre-round data showed 0 429 (storm self-healed). At 64, the 6h window shows 29/50 = 58% 429 cycling. The NVCF rate limit window for this function is >64s but ≤66s. 64s releases keys back into the rotation pool while still in NVCF's rate limit window → guaranteed 429 cascade.

## Budget Analysis
- KEY+TIER = 66+62 = 128 < 153 BUDGET (25s margin)
- Previous: 64+62 = 126 < 153 BUDGET (27s margin)
- 25s margin >> actual OK max ~14s (dsv4p) / ~20s (glm5_2), very safe
- 66s was verified safe in R2124 (0 429, 0 SSL)

## Verification
- Container: `docker compose up -d nv_gw` → Recreated/Started ✓
- env: `KEY_COOLDOWN_S=66` ✓
- ms_gw KEY_COOLDOWN_S unchanged (58) ✓
- Container logs: NV-PROXY Listening on 0.0.0.0:40006 ✓

## Rationale
Premature storm-recovery walk-back. R2125's 66→64 drop crossed the NVCF rate limit window boundary (64 < boundary ≤ 66), causing 58% 429 cycling surge. Reverting to 66 re-establishes the proven-safe cooldown. KEY+TIER=66+62=128 << 153 BUDGET with 25s headroom. Single param; iron law: only change HM1 never HM2.

## ⏳ 轮到HM1优化HM2