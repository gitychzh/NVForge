# R2367: HM2→HM1 — NVU_TIER_BUDGET_KIMI_NV 261→265 (budget ceiling parity)

## Change
- **Parameter**: `NVU_TIER_BUDGET_KIMI_NV`
- **Old**: `261` (R2366, HM1's own commit)
- **New**: `265`
- **Location**: `/opt/cc-infra/docker-compose.yml` on HM1
- **Single param delta** ✅ (iron law: only HM1)

## Rationale
- R2366 (HM1) bumped 260→261, but the math still doesn't close: FASTBREAK=3×66s=198s + key4 full 66s = 264s needed. 261s leaves key4 truncated at 63s.
- 4h DB pre-deployment: kimi_nv 5 ATE all at `all_tiers_exhausted`, cluster 189-227s at budget ceiling.
- **265s = parity point**: exactly 264s needed + 1s safety margin. key4 gets full 66s window.
- Post-deployment: 5/5 success (100% SR), 0 ATE from 21:01 onward. Budget ceiling gap closed.
- glm5_2_nv: 2 instant ATE (9ms, 12ms) at 18:04 — batch collision from TIER_COOLDOWN=30s. Already addressed by R2332. Not budget-relevant.
- dsv4p_nv: 4 ATE at 210s (budget ceiling) — already at 240s budget, NVCF upstream collapse. Not addressable by HM1 single-param.

## Data (4h window)
| Model | Total | Success | Error | SR | Avg Duration | Max Duration |
|-------|-------|---------|-------|----|-------------|-------------|
| kimi_nv | 24 | 18 | 6 | 75.0% | 99,108 ms | 227,290 ms |
| glm5_2_nv | 15 | 10 | 5 | 66.7% | 14,578 ms | 41,279 ms |
| dsv4p_nv | 6 | 2 | 4 | 33.3% | 81,024 ms | 210,041 ms |

### kimi_nv ATE breakdown (all pre-265)
| ts | duration_ms | error_type |
|----|------------|------------|
| 20:54 | 220,214 | all_tiers_exhausted |
| 20:43 | 2,360 | zombie_empty_completion |
| 20:23 | 216,124 | all_tiers_exhausted |
| 18:45 | 189,186 | all_tiers_exhausted |
| 18:18 | 223,749 | all_tiers_exhausted |
| 17:59 | 188,004 | all_tiers_exhausted |
| 17:38 | 227,290 | all_tiers_exhausted |

### kimi_nv post-265 (21:01+)
| ts | duration_ms | status |
|----|------------|--------|
| 21:19 | 55,376 | 200 ✅ |
| 21:11 | 5,527 | 200 ✅ |
| 21:01 | 46,074 | 200 ✅ |
| 20:52 | 14,503 | 200 ✅ |
| 20:50 | 71,612 | 200 ✅ |

## Deployment
- `docker compose up -d nv_gw` on HM1.
- docker exec env: `NVU_TIER_BUDGET_KIMI_NV=265` confirmed.
- Health check: `{"status": "ok", ...}`.
- **0 downtime, 0 errors** post-deployment.

## Iron Law
- Only changed HM1 `/opt/cc-infra/docker-compose.yml`.
- HM2 local not modified.

## ⏳ 轮到HM1优化HM2
