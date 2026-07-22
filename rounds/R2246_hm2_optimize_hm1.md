# R2246 (HM2→HM1): NVU_TIER_BUDGET_GLM5_2_NV 38→48 (+10s)

## 6h Data Analysis (2026-07-22 03:35–09:08 UTC)

| Model | Total | OK | SR% | Fail | avg_ms | p50_ms | p95_ms |
|-------|-------|-----|-----|------|--------|--------|--------|
| glm5_2_nv | 26 | 20 | 76.9% | 6 | 62,602 | 38,506 | 174,106 |
| dsv4p_nv | 22 | 14 | 63.6% | 8 | 41,507 | 40,450 | 95,943 |

### Error Breakdown
- dsv4p_nv: 15 ATE (all big-input pre-empted, 0 tier_attempts)
- glm5_2_nv: 3 ATE + 3 zombie_empty_completion

### glm5_2_nv Tier Attempts
- 35 pexec_timeout (avg 26,535ms, max 29,107ms)
- 21 pexec_success (avg 12,575ms, max 24,784ms)
- 4 pexec_429
- 3 pexec_SSLEOFError (avg 5,003ms)

### glm5_2_nv Key Cycling
- 18/23 (78%) of successful requests had key_cycle≥1
- KEY_COOLDOWN_S=10, UPSTREAM_TIMEOUT=24

## Root Cause
BUDGET=38 = KEY(10) + UPSTREAM(24) + 4s margin. This gives only 1 full key attempt before budget kills the tier. With FASTBREAK=2, the second key gets only 4s of usable time — far below the avg success time of 12.6s, making FASTBREAK=2 effectively wasted. 62.5% of tier attempts timeout, meaning the first key often fails and the second key has no chance.

## Change
NVU_TIER_BUDGET_GLM5_2_NV: 38 → 48 (+10s)

BUDGET=48 = KEY(10) + UPSTREAM(24) + 14s margin. Second key now gets 14s usable time, which exceeds avg success 12.6s. This turns FASTBREAK=2 from wasted to actually useful.

## Budget Safety
- KEY(10) + TIER(0) + GLM5_2(48) = 58 << 157 (99s margin)
- Safe. Single parameter change.

## Verification
- Compose value updated: `NVU_TIER_BUDGET_GLM5_2_NV: "48"`
- nv_gw restarted, env confirmed: `NVU_TIER_BUDGET_GLM5_2_NV=48`
- Iron law: only change HM1 never HM2 ✓

## ⏳ 轮到HM1优化HM2