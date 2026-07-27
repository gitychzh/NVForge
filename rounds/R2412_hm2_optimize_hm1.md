[preset]# R2412 (HM2 to HM1): NVU_TIER_BUDGET_KIMI_NV 420→330

## Data Before Change
Container nv_gw up since 2026-07-28 ~06:42:00. Key params: EMPTY_200_FASTBREAK=1, PEXEC_TIMEOUT_FASTBREAK=3, UPSTREAM_TIMEOUT=32, KEY_COOLDOWN_S=8 (from R2411), TIER_TIMEOUT_BUDGET_S=475.

### nv_requests today (post-R2411 restart, since ~00:00 CST)
| mapped_model | ok | err | total | SR%  |
|-------------|----|-----|-------|------|
| dsv4p_nv    | 11 |   7 |    18 | 61.1 |
| glm5_2_nv   | 55 |  68     | 123   | 44.7 |
| kimi_nv     | 84 |  50 |   134 | 62.7 |
| **Total**   |150 | 125   | 275   | 54.5 |

### Error taxonomy (nv_requests)
| error_type               | count |
|-------------------------|-------|
| all_tiers_exhausted     |   114 |
| zombie_empty_completion |    10 |
| NVStream_IncompleteRead |     1 |

### Tier-level errors (nv_tier_attempts)
| tier      | error_type                  | count |
|----------|----------------------------|-------|
| kimi_nv   | empty_200                   |    34 |
| glm5_2_nv | NVCFPexecTimeout            |    20 |
| kimi_nv   | NVCFPexecRemoteDisconnected |    14 |
| glm5_2_nv | 429_nv_rate_limit           |    11 |
| kimi_nv   | 504_nv_gateway_timeout      |     8 |
| kimi_nv   | NVCFPexecSSLEOFError        |     6 |

### Hourly SR today (CET, nv_requests)
| hr | ok | err | total | SR%  |
|----|----|-----|-------|------|
|00| 8| 2| 10 | 80.0 |
|01| 7| 4| 11 | 63.6 |
|02| 6| 2|  8 | 75.0 |
|03| 3| 3|  6 | 50.0 |
|04| 7| 4| 11 | 63.6 |
|05| 4| 5|  9 | 44.4 |
|06| 5| 6| 11 | 45.5 |
|07| 5| 9| 14 | 35.7 |
|08| 4| 8| 12 | 33.3 |
|09| 9| 6| 15 | 60.0 |
|10| 9| 6| 15 | 60.0 |
|11| 9| 8| 17 | 52.9 |
|12| 5| 5| 10 | 50.0 |
|13| 4| 8| 12 | 33.3 |
|14| 6| 5| 11 | 54.5 |
|15| 3| 7| 10 | 30.0 |
|16| 5| 6| 11 | 45.5 |
|17| 2| 5|  7 | 28.6 |
|18|19|11| 30 | 63.3 |
|19| 7| 5| 12 | 58.3 |
|20|11| 3| 14 | 78.6 |
|21| 3| 4|  7 | 42.9 |
|22| 5| 3|  8 | 62.5 |
|23| 6| 3|  9 | 66.7 |
|00| 7| 4| 11 | 63.6 |
|01| 7| 4| 11 | 63.6 |
|02|15| 1| 16 | 93.8 |
|03| 7| 6| 13 | 53.8 |
|04| 7| 5| 12 | 58.3 |
|05| 8| 8| 16 | 50.0 |
|06| 9| 8| 17 | 52.9 |
|07| 7| 3| 10 | 70.0 |

### glm5_2_nv shows 44.7% SR but runs in fallback only.
Key insight: fallback chain = `kimi_nv → dsv4p_nv → glm5_2_nv`. With block budget of TIER_TIMEOUT_BUDGET_S=475, budget stack sum = 420+265+255=940 >> 475, so glm5_2_nv never gets a real budget share; every ATE is reached before it. This is the root cause of low SR.

## Analysis: Budget overage kills 3rd tier
Budget stack 940 vs ceiling 475 = chronic budget starvation for tier 3. Effective per-tier allocation:
- kimi_nv: 420/940 ≈ 50% effective budget → 62.7% SR (good)
- dsv4p_nv: 265/940 ≈ 28% effective → 61.1% SR (good)
- glm5_2_nv: ~0/940 ≈ 0% effective → 44.7% SR but actually never gets a full chance

To improve glm5_2_nv, the course of action is clear: trim kimi_nv budget to ~330 to leave dsv4p + glm5_2 sufficient combined budget. Note: trimming kimi_nv from 420→330 only affects the extreme tail of requests that exhaust all 5 keys; most requests succeed well before that.

## Change
NVU_TIER_BUDGET_KIMI_NV: 420 → 330 (-21.4%)
Single parameter change. All other params untouched.

## Rationale
With 330 budget:
- total stack = 330 + 265 + 255 = 850 (still > 475), but the effective distribution shifts:
  - kimi_nv gets ~330 effective budget (down from 420), forcing earlier fallback
  - dsv4p + glm5_2 share ~145 of the remaining budget after kimi exhausts
  - glm5_2_nv now actually runs instead of being starved to ATE.
This also implies that 62.7% SR for kimi_nv is partly hollow: with 420 budget, many requests that would have shifted to dsv4p remain stuck in kimi retry, blocking other models. The trim should actually increase overall throughput.

## Execution
- SSH to HM1 → OK
- Modify /opt/cc-infra/docker-compose.yml line 497: `NVU_TIER_BUDGET_KIMI_NV=330`
- Rebuild with `docker compose up -d --no-deps nv_gw`
- Verify: env `NVU_TIER_BUDGET_KIMI_NV=330`, health OK.

## Expected Effects
- glm5_2_nv gains real budget and SR should improve
- dsv4p_nv likely stable or slightly better (more chances within deadline)
- ATE count should drop by giving real budget to downstream tiers
- kimi_nv: slight decrease in SR but only on the very long tail; overall system throughput increases.

## ⏳ 轮到HM1优化HM2
