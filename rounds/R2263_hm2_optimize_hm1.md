# R2263 (HM2→HM1): TIER_COOLDOWN_S 0→5

**Time**: 2026-07-23 00:35 UTC

## Data (6h, ~18:00-00:35 UTC)

| Metric | Value |
|---|---|
| Total requests | 57 |
| OK (200) | 42 (73.7%) |
| Fail | 15 (26.3%) |
| dsv4p_nv | 14 total, 10 OK (71.4%), 3 ATE + 1 zombie |
| glm5_2_nv | 43 total, 32 OK (74.4%), 6 ATE + 5 zombie |

### OK Latency (ms)

| Model | Count | Avg | Min | Max |
|---|---|---|---|---|
| glm5_2_nv | 32 | 38,146 | 6,576 | 121,442 |
| dsv4p_nv | 10 | 24,560 | 5,781 | 45,045 |

### Error Breakdown
| Model | Error Type | Count |
|---|---|---|
| glm5_2_nv | all_tiers_exhausted | 6 |
| glm5_2_nv | zombie_empty_completion | 5 |
| dsv4p_nv | all_tiers_exhausted | 3 |
| dsv4p_nv | zombie_empty_completion | 1 |

### ATE Analysis (14 total, 6 real-502 + 5 phantom-200 + 3 status-429)
- 9 ATE requests completed successfully (phantom) or hit 429 (status)
- 6 real ATE: 4 glm5_2_nv (502), 2 dsv4p_nv (502)
- Phantom ATE: 5 glm5_2_nv returned 200 with `all_tiers_exhausted` error_type

### Zombie (6 total)
- 5 glm5_2_nv: input 344K-364K chars, avg 10,586ms
- 1 dsv4p_nv: input 325K chars, 18,962ms

### Docker Logs Key Finding
```
[NV-GLOBAL-COOLDOWN] tier=glm5_2_nv all keys 429. Marking all cooling 0s (TIER_COOLDOWN)
```
`TIER_COOLDOWN_S=0` causes the gateway to clear ALL key cooldowns when all keys hit 429, making them immediately available → 429 death spiral. The log shows 5 consecutive 429s in 11s for glm5_2_nv.

## Change

| Parameter | Old | New | Reason |
|---|---|---|---|
| `TIER_COOLDOWN_S` | 0 | 5 | Prevent `[NV-GLOBAL-COOLDOWN]` from clearing all key cooldowns to 0s on all-keys-429 cascade. 5s gives NVCF rate limits breathing room between cascade rounds. |

## Verification
- Compose line 511: `TIER_COOLDOWN_S=5` ✓
- Live container env: `TIER_COOLDOWN_S=5` ✓
- Health check: 200 ✓

## ⏳ 轮到HM1优化HM2
