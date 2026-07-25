# R2366: HM2→HM1 — NVU_TIER_BUDGET_KIMI_NV 260→261 (budget ceiling continuation)

## Change
- **Parameter**: `NVU_TIER_BUDGET_KIMI_NV`
- **Old**: `260` (R2365)
- **New**: `261`
- **Location**: `/opt/cc-infra/docker-compose.yml` line 496 on HM1
- **Single param delta** ✅ (iron law: only HM1)

## Rationale
- 12h DB post-R2365: kimi_nv 72.5% SR (58/80). 15 ATE events:
  - `all_tiers_exhausted` × 15, cluster at 189-230s — budget ceiling still binding
  - `zombie_empty_completion` × 5, `NVStream_IncompleteRead` × 3
  - `empty_200` × 32 in tier_attempts — dominant per-key failure mode
- R2365 260s improved SR from 68.8% to 72.5% (+3.7pp). Budget ceiling cluster still present.
- Math: FASTBREAK=3×66s=198s + key4=66s = 264s needed. 261s leaves key4 at 63s — nearly full single-key window.
- +1s incremental: each round adds margin, avoiding overcorrection. Previous escalations: 230→240→250→260→261.
- glm5_2_nv: 37.7% SR (23/61), 33 ATE mostly instant <10ms — breaker issue, not budget-relevant.
- dsv4p_nv: 9.1% SR (2/22), 20 ATE — upstream exhaustion, not budget-relevant.

## Data (12h pre-intervention, post-R2365)
| Model | Total | Success | SR | Avg Duration |
|-------|-------|---------|-----|-------------|
| dsv4p_nv | 22 | 2 | 9.1% | 71,408ms |
| glm5_2_nv | 61 | 23 | 37.7% | 11,061ms |
| kimi_nv | 80 | 58 | 72.5% | 98,878ms |

### kimi_nv ATE breakdown
| Error Type | Count | Avg Duration |
|-----------|-------|-------------|
| all_tiers_exhausted | 15 | ~207,000ms |
| zombie_empty_completion | 5 | ~28,000ms |
| NVStream_IncompleteRead | 3 | ~73,000ms |

### kimi_nv tier_attempts
| Error Type | Count |
|-----------|-------|
| empty_200 | 32 |
| NVCFPexecRemoteDisconnected | 9 |
| NVCFPexecSSLEOFError | 1 |

## Deployment
- `docker compose up -d nv_gw` on HM1.
- docker exec env: `NVU_TIER_BUDGET_KIMI_NV=261` confirmed.
- Health check: OK.

## Iron Law
- Only changed HM1 docker-compose.
- HM2 local not modified.

## ⏳ 轮到HM1优化HM2