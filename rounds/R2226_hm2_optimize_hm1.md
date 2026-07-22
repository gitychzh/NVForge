# R2226 (HM2→HM1): KEY_COOLDOWN_S 38→36 (-2s)

**Date**: 2026-07-22 08:05 UTC
**Author**: opc2_uname (HM2)
**Type**: Single parameter, alternating KEY→KEY pattern (skip TIER=0)

## Pre-Optimization Data (6h window to 08:05 UTC)

| Metric | Value |
|--------|-------|
| Total requests | 37 |
| Success (200) | 30 (81.1% SR) |
| Failures | 7 (all zombie_empty_completion) |
| ATE (all_tiers_exhausted) | 0 |
| Model | glm5_2_nv only (single model traffic) |
| Avg success latency | 14,312ms |
| Key cycling (429s=1) | 29/37 (78.4%) |
| Key cycling (429s=2) | 4/37 |
| Key cycling (429s=3) | 3/37 |
| Key cycling (429s=4) | 1/37 |

### Tier attempts (6h)
- pexec_success: 37
- pexec_429: 10
- pexec_timeout: 2
- pexec_SSLEOFError: 1

### Zombie failures
7 glm5_2_nv zombie_empty_completion at 3.2-19.2s. Classic NVCF empty-200 issue - not config-fixable.

## Analysis

All traffic is glm5_2_nv via pexec_us_rr single-tier chain. No dsv4p_nv or kimi_nv traffic observed. The 7 zombie failures are NVCF-side (empty-200 with status=200, not triggering fallback). Universal key cycling (key_cycle_429s=1 on 29/37 requests) means first key is always in cooldown at ~6 req/h with KEY_COOLDOWN=38 — the cooldown timer always outlasts the inter-request gap.

## Change

- **KEY_COOLDOWN_S**: 38 → 36 (-2s)

## Budget Safety

- KEY(36) + TBUD_0(0) + GLM5_2_BUDGET(28) = 64 << 157 (93s margin)
- dsv4p constraint: 36 + 24 = 60 << 94 (34s3 margin)
- Single param; alternating KEY→KEY pattern; iron law: only change HM1 never HM2

## Deployment

1. sed -i line 500 on /opt/cc-infra/docker-compose.yml
2. docker compose stop nv_gw && docker compose up -d nv_gw
3. Verified: docker exec nv_gw env → KEY_COOLDOWN_S=36 ✓
4. Health check: curl localhost:40006/health → 200 ✓

## ⏳5 轮到HM1优化HM2