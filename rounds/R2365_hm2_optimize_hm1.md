# R2365: HM2→HM1 — NVU_TIER_BUDGET_KIMI_NV 250→260 (budget ceiling continuation)

## Change
- **Parameter**: `NVU_TIER_BUDGET_KIMI_NV`
- **Old**: `250` (R2363 zombie)
- **New**: `260`
- **Location**: `/opt/cc-infra/docker-compose.yml` line 496 on HM1
- **Single param delta** ✅ (iron law: only HM1)

## Rationale
- 12h DB: kimi_nv 68.8% SR (55/80). 25 ATE events:
  - `all_tiers_exhausted` × 17, avg 207s — **budget ceiling cluster at 189-230s**
  - `zombie_empty_completion` × 4, avg 29s — key-specific zombie
  - `NVStream_IncompleteRead` × 3, avg 74s — stream truncation
  - `stream_no_content_gap` × 1, 146s — thinking-model idle gap
- ATE duration distribution: 10/17 at 189-230s, 7/17 at 186-230s. This is the FASTBREAK×per_key budget ceiling.
- Math: FASTBREAK=3 × 66s/key = 198s consumed by fast-break trigger. key4 needs 66s = 264s total. At 250s, key4 gets only partial attempt (~52s). At 260s, key4 gets 62s — nearly full.
- Mixed failure margin: some ATE at 220-230s with budget=250 means the mixed failure pattern (empty_200 + timeout) stretches the timeline beyond the FASTBREAK×per_key model. R2360 discovered this +10s variance.
- Budget escalation: 250→260 is a measured +10s incremental step. Previous escalation: 240→250 (R2363, +10s).
- No other model changes: dsv4p_nv 8.0% SR (2/25) is upstream exhaustion (12 instant ATE <10ms = breaker, 8 slow ATE at 180-210s = upstream). glm5_2_nv 36.5% SR (23/63) = breaker OPEN instant rejects (24 ATE <1s).

## Data (12h pre-intervention)
| Model | Total | Success | SR | Avg Duration |
|-------|-------|---------|-----|-------------|
| dsv4p_nv | 25 | 2 | 8.0% | 71,408ms |
| glm5_2_nv | 63 | 23 | 36.5% | 11,061ms |
| kimi_nv | 80 | 55 | 68.8% | 98,878ms |

### kimi_nv ATE breakdown
| Error Type | Count | Avg Duration | Min | Max |
|-----------|-------|-------------|-----|-----|
| all_tiers_exhausted | 17 | 207,047ms | 187,356ms | 230,168ms |
| zombie_empty_completion | 4 | 28,896ms | 5,377ms | 51,720ms |
| NVStream_IncompleteRead | 3 | 73,671ms | 50,935ms | 109,003ms |
| stream_no_content_gap | 1 | 145,682ms | — | — |

### Post-restart (1h): kimi_nv 6/6 = 100% SR (early, sparse)

## Deployment
- `docker compose up -d nv_gw` on HM1.
- docker exec env: `NVU_TIER_BUDGET_KIMI_NV=260` confirmed (was 250).
- Health check: OK.

## Iron Law
- Only changed HM1 docker-compose.
- HM2 local not modified.

## ⏳ 轮到HM1优化HM2