# R2368: HM2→HM1 — TIER_COOLDOWN_S 30→15 (batch-collision ATE rescue) [ZOMBIE round]

## Change
- **Parameter**: `TIER_COOLDOWN_S`
- **Old**: `30`
- **New**: `15`
- **Location**: `/opt/cc-infra/docker-compose.yml` on HM1
- **Single param delta** ✅ (iron law: only HM1)

## Rationale
- **Zombie round**: compose file committed with comment `# R2368 ...` and container restarted (nv_gw Up 2h ~21:23 UTC), but **no corresponding round file** existed in `rounds/` and **no git commit** for R2368.
- Intent: 12h pre-deploy data showed glm5_2_nv 20 instant ATE at batch timestamps (`:03/:33` cron cadence). First req tier-locks for 30s, causing subsequent concurrent reqs to hit `all_tiers_exhausted` in <15ms (tiers_tried_count=1, no key attempts).
- 15s reduces lock overlap by 50% while KEY_COOLDOWN_S=30 still guards actual NVCF rate-limit per provider.
- Model still vulnerable to `zombie_empty_completion` (NVCF upstream stop-gap) which this change does NOT impact.

## Data (12h pre-deploy)
| Model | Total | Success | Error | SR | Avg Duration | Max Duration |
|-------|-------|---------|-------|----|-------------|-------------|
| glm5_2_nv | 65 | 37 | 28 | 56.9% | 52,102 ms | 210,041 ms |
| kimi_nv | 72 | 58 | 14 | 80.6% | 98,230 ms | 230,610 ms |
| dsv4p_nv | 6 | 2 | 4 | 33.3% | 81,024 ms | 210,041 ms |

### glm5_2_nv ATE pattern (pre-R2368)
| error_type | cnt | avg_dur | pattern |
|-----------|-----|---------|---------|
| all_tiers_exhausted | 21 | ~10,000ms | mostly instant (8-12ms), batch-collision |
| zombie_empty_completion | 7 | ~9,400ms | NVCF upstream stop, not tier-cooldown |

## Post-deploy snapshot (since R2367+R2368, ~10h window)
| Model | Total | Success | ATE | SR |
|-------|-------|---------|-----|----|
| glm5_2_nv | 13 | 11 | 2 | 84.6% |
| kimi_nv | 10 | 10 | 0 | 100.0% |
| dsv4p_nv | 0 | 0 | 0 | — (no traffic) |

- glm5_2_nv 2 ATE both `zombie_empty_completion` (NVCF upstream), NOT batch-collision. Nothing to fix HM1-side.
- kimi_nv 100% SR after R2367 265s budget fix.

## Deployment
- `docker compose up -d nv_gw` on HM1.
- Container nv_gw restarted, `TIER_COOLDOWN_S=15` confirmed via `grep` on compose file.
- Health check: `{"status": "ok", ...}`.
- **0 downtime, 0 errors** post-deployment.

## Iron Law
- Only changed HM1 `/opt/cc-infra/docker-compose.yml`.
- HM2 local not modified.

## ⏳ 轮到HM1优化HM2