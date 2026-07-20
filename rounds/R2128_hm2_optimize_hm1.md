# R2128 (HM2→HM1): TIER_COOLDOWN_S 62→60 — fallback chain availability

## Change
- **TIER_COOLDOWN_S**: 62 → 60 (-2s)
- **TYPE**: Single param; tier cooldown compression

## Data (6h window, 2026-07-20 17:00–23:00 UTC)
| Metric | Value |
|---|---|
| Total requests | 51 |
| Success (200) | 32 |
| Failures | 19 |
| **SR** | **62.75%** |
| all_tiers_exhausted (dsv4p_nv) | 11 |
| zombie_empty_completion (glm5_2_nv) | 10 |
| fallback_occurred | 0 |
| kimi_nv requests | 0 |

### Model breakdown
| Model | Requests | OK | Fail | Avg (OK) ms | P50 ms |
|---|---|---|---|---|---|
| glm5_2_nv | 32 | 22 | 10 zombie | 8,272 | 6,776 |
| dsv4p_nv | 19 | 10 | 9 ATE | 12,378 | 13,178 |

### ATE diagnostic
- All 9 dsv4p_nv ATEs: tiers_tried_count=1, fallback_tiers_used={dsv4p_nv}
- **0 tier_attempts** for all 9 ATE request_ids — dsv4p_nv tier pre-empted before any key attempt
- **0 fallback_occurred** — glm5_2_nv/kimi_nv fallback tiers silently skipped
- dsv4p_nv ATEs clustered in 18:00–18:09 UTC (NVCF temporary degradation)
- kimi_nv: 0 tier_attempts, 0 requests in 6h

### Zombie pattern
- 10 zombie_empty_completion on glm5_2_nv, scattered across the 6h window
- Per-key distribution: k0=1, k1=3, k2=2, k3=2, k4=2
- Zombie avg: 4,427–9,142ms per key

### glm5_2_nv per-key
| Key | Requests | OK | Avg (OK) ms | P50 ms | P95 ms | Max ms |
|---|---|---|---|---|---|---|
| k0 | 5 | 4 | 8,045 | 6,871 | 12,406 | 13,520 |
| k1 | 7 | 4 | 14,130 | 12,864 | 35,097 | 42,196 |
| k2 | 6 | 4 | 7,847 | 6,528 | 11,320 | 11,603 |
| k3 | 6 | 4 | 9,817 | 8,665 | 18,132 | 20,254 |
| k4 | 6 | 4 | 6,793 | 5,428 | 11,802 | 12,964 |
| null | 2 | 2 | 8,839 | 8,839 | 11,984 | 12,334 |

## Rationale
- **Fallback chain broken**: All 9 dsv4p_nv ATEs show 0 fallback_occurred — glm5_2_nv/kimi_nv never entered as rescue tiers
- **TIER_COOLDOWN_S=62** keeps glm5_2_nv excluded from fallback graph for 62s after each zombie — with 10 zombies in 6h, the tier is frequently unavailable
- **FASTBREAK=1** (R2127) kills zombies faster (1st empty200), reducing cooldown triggers — safer to lower cooldown
- **Budget check**: KEY(66) + TIER(60) = 126 < 153 BUDGET, 27s margin safe
- **Traffic**: 8.5 req/h ultra-low, 5-key pool → near-zero 429 risk even at 60s boundary
- **2s faster tier recovery** → 2s sooner glm5_2_nv is available as fallback for dsv4p_nv ATEs
- **Single param, "少改多轮"** principle

## Verification
- Compose: `TIER_COOLDOWN_S: "60"` ✓
- Live env: `TIER_COOLDOWN_S=60` ✓
- Container restarted: nv_gw Recreated → Started ✓

## Current state
| Param | Value |
|---|---|
| KEY_COOLDOWN_S | 66 |
| TIER_COOLDOWN_S | 60 |
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