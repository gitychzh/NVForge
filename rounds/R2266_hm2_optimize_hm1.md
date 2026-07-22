# R2266 (HM2→HM1): TIER_COOLDOWN_S 5→42 — KEY=TIER alignment

## Deployment Summary
- **Date**: 2026-07-23 01:33 UTC
- **Author**: opc2_uname (HM2)
- **Change**: TIER_COOLDOWN_S 5→42 (+37s)
- **Container**: nv_gw, restart verified, healthy

## Pre-Change Data (6h window, R2265 regime, KEY_COOLDOWN=42, TIER_COOLDOWN=5)

| Metric | Value |
|--------|-------|
| Total requests | 56 |
| OK | 40 (71.4%) |
| Fail | 16 (10 ATE + 6 zombie) |
| Total 429 cycles | 66 |
| Requests with 429 cycles | 19 (33.9%) |
| ATE with 0 tier_attempts | 10 (100%) |
| zombie_empty_completion | 6 |

### Per-Model Breakdown
| Model | Total | OK | Fail | Fail types |
|-------|-------|-----|------|------------|
| glm5_2_nv | 42 | 30 (71.4%) | 12 | 7 ATE + 5 zombie |
| dsv4p_nv | 14 | 10 (71.4%) | 4 | 3 ATE + 1 zombie |

### Error Analysis
- **10 ATE**: all upstream_type=NULL, all_tiers_failed_in_mapped_tier, 0 tier_attempts
  - glm5_2_nv: 7 ATE, avg 54.8s, max 114.0s
  - dsv4p_nv: 3 ATE, avg 114.0s
- **6 zombie**: NVCF content-filter, not config-fixable
- **Error logs**: tier=glm5_2_nv k2/k3 all getting 429_nv_rate_limit → cycling to next key

## Root Cause Analysis

TIER_COOLDOWN_S=5 (near-zero) causes the scheduler to clear tier cooldown almost instantly, re-entering the tier while all 5 keys are still in 42s KEY_COOLDOWN. This creates a 429 cascading loop:
1. Key gets 429 → marked cooldown 42s
2. Scheduler cycles to next key → also 429 (all keys getting hammered by NVCF)
3. All 5 keys in cooldown simultaneously
4. TIER_COOLDOWN=5 expires → scheduler re-enters tier → all keys still in cooldown → ATE with 0 tier_attempts

Per iron law: KEY_COOLDOWN = TIER_COOLDOWN. R2265 dropped KEY from 48→42 but TIER remained at 5s from R2263, creating a severe mismatch.

## Change: TIER_COOLDOWN_S 5→42

- Aligns with KEY_COOLDOWN_S=42 (KEY=TIER iron law)
- 42s gives NVCF breathing room to release rate limits before tier re-entry
- Prevents the "all-keys-cooldown + tier immediate re-entry → ATE" cascading pattern
- Single parameter; iron law: only HM1, never HM2

## Verification
- `docker exec nv_gw env`: TIER_COOLDOWN_S=42 ✓, KEY_COOLDOWN_S=42 ✓
- `docker ps`: nv_gw Up, healthy ✓
- `docker logs nv_gw --tail 10`: Clean start, no errors ✓

## Post-Deploy State
| Parameter | Old | New |
|-----------|-----|-----|
| TIER_COOLDOWN_S | 5 | **42** |
| KEY_COOLDOWN_S | 42 | 42 (unchanged) |
| TIER_TIMEOUT_BUDGET_S | 192 | 192 |
| UPSTREAM_TIMEOUT | 24 | 24 |
| NVU_PEER_FALLBACK_TIMEOUT | 122 | 122 |
| NVU_TIER_BUDGET_DSV4P_NV | 135 | 135 |
| NVU_TIER_BUDGET_GLM5_2_NV | 100 | 100 |

## ⏳ 轮到HM1优化HM2