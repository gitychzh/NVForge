# R2277: HM2 optimizes HM1 — TIER_TIMEOUT_BUDGET_S 251→275

**Date**: 2026-07-23 05:25 UTC
**Author**: opc2_uname (HM2, acting on HM1)
**Iron Law**: Only HM1 changed; HM2 untouched.

## Data (6h window on HM1 nv_requests)

| Metric | Value |
|---|---|
| Total requests | 47 |
| Success (2xx) | 33 (70.2%) |
| Failures | 14 |
| Avg OK latency | 24,476ms |

### Per-model breakdown
| Model | Total | OK | Fail | Avg OK ms |
|---|---|---|---|---|
| glm5_2_nv | 31 | 21 | 10 | 16,535 |
| dsv4p_nv | 16 | 12 | 4 | 41,366 |

### Error breakdown
| Model | Error | Count |
|---|---|---|
| glm5_2_nv | all_tiers_exhausted | 5 |
| glm5_2_nv | zombie_empty_completion | 5 |
| dsv4p_nv | all_tiers_exhausted | 4 |

### dsv4p_nv ATE detail
All 4 dsv4p_nv ATEs: `tiers_tried_count=1`, `fallback_tiers_used={dsv4p_nv}` — fallback chain (kimi_nv, glm5_2_nv) NEVER attempted. R2276's 251s budget gave exactly 1s margin for 1 fallback key — too tight.

### glm5_2_nv: 42% key cycling rate, 21 rate limits
13 of 31 requests hit key cycling (9 cycle1 + 4 cycle2+), 21 tier attempts with 429 rate limit. Zombie 5/hour (NVCF upstream issue, not configurable).

## Analysis

R2276 raised TIER_TIMEOUT_BUDGET_S from 234→251. Math:
- 251 - 160 (dsv4p budget) - 66 (tier cooldown) = **25s ≥ 24s** → 1 fallback key with 1s margin
- 1s margin is inadequate — any network jitter or scheduling delay consumes it
- To get 2 fallback keys: need 251 - 160 - 66 = 25s → only 1 key. Need 25 + 24 = 49s for 2 keys

## Change

**TIER_TIMEOUT_BUDGET_S: 251 → 275 (+24s)**

New math: 275 - 160 - 66 = **49s ≥ 24s** → 2 fallback key attempts with 25s margin.

This gives dsv4p_nv enough budget to exhaust its 160s tier budget, wait 66s tier cooldown, then attempt 2 keys from kimi_nv/glm5_2_nv fallback before declaring ATE.

## Verification

- `grep TIER_TIMEOUT_BUDGET_S /opt/cc-infra/docker-compose.yml` → 275 ✓
- `docker exec nv_gw env | grep TIER_TIMEOUT` → 275 ✓
- `curl http://localhost:40006/health` → `{"status": "ok", ...}` ✓

## ⏳ 轮到HM1优化HM2