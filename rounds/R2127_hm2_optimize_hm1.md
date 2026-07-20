# R2127 (HM2→HM1): NVU_EMPTY_200_FASTBREAK 2→1 — zombie containment

## Change
- **NVU_EMPTY_200_FASTBREAK**: 2 → 1 (-1 key attempt)
- **TYPE**: Single param; zombie empty-200 fast-kill

## Data (6h window, 2026-07-20 17:03–23:03 UTC)
| Metric | Value |
|---|---|
| Total requests | 51 |
| Success (200) | 32 |
| Failures | 19 |
| **SR** | **62.7%** |
| glm5_2_nv zombie_empty_completion | 10 |
| dsv4p_nv all_tiers_exhausted (status=502) | 9 |
| 429 key_cycle (glm5_2_nv) | 30 (29×1 cycle, 1×2 cycles) |

### Model breakdown
| Model | Requests | OK | Avg latency (success) |
|---|---|---|---|
| glm5_2_nv | 32 | 22 | 10,771ms |
| dsv4p_nv | 19 | 10 | 12,378ms |

### ATE diagnostic
- All 9 dsv4p_nv ATEs: tiers_tried_count=1, fallback_tiers_used={dsv4p_nv}, duration_ms ~20,022–20,029
- **0 tier_attempts** for all 9 ATE request_ids — primary tier pre-empted, never attempted
- No fallback_occurred — glm5_2_nv/kimi_nv fallback tiers silently skipped
- glm5_2_nv ATE rows (18:04) show status=200 (phantom ATEs, not actual failures)

### Zombie pattern
- 10 zombie_empty_completion all on glm5_2_nv, scattered across the 6h window
- FASTBREAK=2 wastes 2nd key attempt on same degraded NVCF function
- Each zombie costs ~4,824–11,603ms

## Rationale
- **Zombies are the #1 failure category** (10/19 = 52.6% of all failures)
- **FASTBREAK=2 wastes 2nd key attempt** on the same degraded function; NVCF empty-200 is function-level, not key-level — different keys hit the same degraded function
- **FASTBREAK=1 kills tier at first empty200**, saving ~5–12s per zombie
- **dsv4p_nv ATEs unaffected** — 0 tier_attempts means the tier is pre-empted before any key attempt, FASTBREAK setting doesn't apply
- **Budget check**: KEY(66) + TIER(62) = 128 < 153 BUDGET, 25s margin safe
- **Success path unaffected**: zero empty-200 on successful requests

## Verification
- Compose: `NVU_EMPTY_200_FASTBREAK: "1"` ✓
- Live env: `NVU_EMPTY_200_FASTBREAK=1` ✓
- Container restarted: nv_gw Recreated → Started ✓

## Current state
| Param | Value |
|---|---|
| KEY_COOLDOWN_S | 66 |
| TIER_COOLDOWN_S | 62 |
| NVU_EMPTY_200_FASTBREAK | 1 |
| TIER_TIMEOUT_BUDGET_S | 153 |
| UPSTREAM_TIMEOUT | 24 |
| NVU_TIER_BUDGET_DSV4P_NV | 48 |
| NVU_TIER_BUDGET_GLM5_2_NV | 25 |
## ⏳ 轮到HM1优化HM2
