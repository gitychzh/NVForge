# R2247 (HM2→HM1): NVU_PEXEC_TIMEOUT_FASTBREAK 2→1

## 6h Data Summary
- **47 req / 36 OK (76.6% SR) / 11 fail**
- 6 dsv4p ATE (all preempted, 0 tier_attempts)
- 3 glm5_2 zombie (NVCF function-level, not config-fixable)
- 2 glm5_2 ATE (preempted, 0 tier_attempts)

## Error Breakdown
| Model | Error Type | Count | Details |
|---|---|---|---|
| dsv4p_nv | all_tiers_exhausted | 6 | all preempted, 0 tier_attempts, duration 62-96s, total_input_chars 315-354K |
| glm5_2_nv | zombie_empty_completion | 3 | NVCF function degradation |
| glm5_2_nv | all_tiers_exhausted | 2 | preempted, 0 tier_attempts |

## Tier Attempts (6h)
| Tier | Error Type | Count | Avg ms |
|---|---|---|---|
| glm5_2_nv | pexec_timeout | 40 | 26,564 |
| glm5_2_nv | pexec_success | 22 | 12,399 |
| glm5_2_nv | pexec_429 | 5 | - |
| glm5_2_nv | pexec_SSLEOFError | 3 | 5,003 |
| glm5_2_nv | NVCFPexecTimeout | 1 | 25,460 |

## Key Cycle 429s (6h)
- glm5_2_nv: 1-cycle=11, 2-cycle=3, 4-cycle=3, 7-cycle=3, other=4
- dsv4p_nv: 0 key_cycle_429s (all preempted before any key attempt)

## Success Latency (6h)
| Model | Count | Avg ms | Min ms | Max ms |
|---|---|---|---|---|
| dsv4p_nv | 15 | 34,940 | 14,803 | 65,761 |
| glm5_2_nv | 21 | 58,828 | 5,574 | 174,770 |

## Root Cause Analysis
All 8 dsv4p ATEs have 0 tier_attempts — preempted before any key was attempted. Root cause: budget exhaustion under KEY_AUTHFAIL_COOLDOWN_S=60.

- Per-key cost: KEY_AUTHFAIL_COOLDOWN(60) + KEY_COOLDOWN(10) + UPSTREAM_TIMEOUT(24) = 94s
- FASTBREAK=2 requires 2 keys: 94s + 94s = 188s (but possible overlap on authfail: 60+10+24+10+24 = 128s)
- Tier budget = 96s < 128s → preempted

## Change
**NVU_PEXEC_TIMEOUT_FASTBREAK: 2→1 (-1 key)**
- FASTBREAK=1: 60+10+24 = 94s < 96s budget → 1 key can be attempted
- Unblocks all dsv4p ATE preemptions
- FASTBREAK=1 was stable for 136 rounds (R559-R694)
- R2108 (1→2) was a regression under authfail cooldown regime
- glm5_2 budget (48) also can't fit 2 keys (10+24+10+24=68>48), so FASTBREAK=2 was effectively 1 for glm5_2 anyway

## Budget Safety
- KEY(10)+TIER(0)+DSV4P(96)=106 << 157 BUDGET (51s margin)
- KEY(10)+GLM5_2(48)=58 << 157 BUDGET (99s margin)

## Verification
- Container restarted, env confirmed: NVU_PEXEC_TIMEOUT_FASTBREAK=1
- Single parameter; iron law: only change HM1 never HM2

## ⏳ 轮到HM1优化HM2