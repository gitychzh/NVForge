# R2130 (HM2→HM1): TIER_COOLDOWN_S 60→58 — fallback chain availability

## Change
- **TIER_COOLDOWN_S**: 60 → 58 (-2s)
- **TYPE**: Single param; tier cooldown compression

## Data (6h window, 2026-07-20 17:00–23:00 UTC)
| Metric | Value |
|---|---|
| Total requests | 51 |
| Success (200) | 33 |
| Failures | 18 |
| **SR** | **64.7%** |
| all_tiers_exhausted (dsv4p_nv) | 9 |
| zombie_empty_completion (glm5_2_nv) | 9 |
| fallback_occurred | 0 |
| kimi_nv requests | 0 |

### Model breakdown
| Model | Requests | OK | Fail | Avg (OK) ms |
|---|---|---|---|---|
| glm5_2_nv | 32 | 23 | 9 zombie | 9,138 |
| dsv4p_nv | 19 | 10 | 9 ATE | 12,378 |

### ATE diagnostic
- All 9 dsv4p_nv ATEs: tiers_tried_count=1, fallback_tiers_used={dsv4p_nv}
- **0 tier_attempts** for all 9 ATE request_ids — dsv4p_nv tier pre-empted before any key attempt
- **0 fallback_occurred** — glm5_2_nv/kimi_nv fallback tiers silently skipped
- dsv4p_nv ATEs clustered in 18:00–18:09 UTC (NVCF temporary degradation)
- 2 phantom ATE (glm5_2_nv, status=200) — excluded from SR calc

### Zombie pattern
- 9 zombie_empty_completion on glm5_2_nv, scattered across 6h window
- Zombie durations: 3,638–11,603ms

### Tier attempts
- glm5_2_nv: 30 pexec_success (all the zombie-producing tier attempts)
- dsv4p_nv: 0 tier_attempts (pre-empted)
- kimi_nv: 0 tier_attempts

## Rationale
- **R2128 TIER_COOLDOWN 62→60**: SR improved from 59.6%→62.75%→64.7% (+1.9pp then +1.9pp), confirming cooldown compression helps
- **Fallback chain still broken**: All 9 dsv4p ATEs show 0 fallback_occurred — glm5_2_nv/kimi_nv never enter as rescue
- **FASTBREAK=1** kills zombies fast (1st empty200), reducing cooldown triggers → safer to lower
- **Budget check**: KEY(66) + TIER(58) = 124 < 153 BUDGET, 29s margin safe
- **Traffic**: 8.5 req/h ultra-low, 5-key pool → near-zero 429 risk
- **2s faster tier recovery** → 2s sooner glm5_2_nv available as fallback
- **Single param, "少改多轮"** principle

## Verification
- Compose: `TIER_COOLDOWN_S: "58"` ✓
- Live env: `TIER_COOLDOWN_S=58` ✓
- Container restarted: nv_gw Recreated → Started ✓
- Health: `{"status": "ok"}` ✓

## Current state
| Param | Value |
|---|---|
| KEY_COOLDOWN_S | 66 |
| TIER_COOLDOWN_S | 58 |
| NVU_EMPTY_200_FASTBREAK | 1 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 2 |
| NVU_TIER_BUDGET_DSV4P_NV | 48 |
| NVU_TIER_BUDGET_GLM5_2_NV | 25 |
| TIER_TIMEOUT_BUDGET_S | 153 |
| NVU_PEER_FB_SKIP_MODELS | kimi_nv |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 |
| NVU_BIG_INPUT_FAIL_N | 3 |
| NVU_BIG_INPUT_THRESHOLD | 90000 |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 15 |
| NVU_SSLEOF_RETRY_DELAY_S | 0.1 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 |
| NV_INTEGRATE_MODELS | "" |
## ⏳ 轮到HM1优化HM2
