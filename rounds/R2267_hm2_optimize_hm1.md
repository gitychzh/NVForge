# R2267 (HM2→HM1): KEY_COOLDOWN_S 42→66, TIER_COOLDOWN_S 42→66 — escape 429 anti-pattern zone

## Deployment Summary
- **Date**: 2026-07-23 02:00 UTC
- **Author**: opc2_uname (HM2)
- **Change**: KEY_COOLDOWN_S 42→66 (+24s), TIER_COOLDOWN_S 42→66 (+24s)
- **Container**: nv_gw, force-recreated, verified healthy
- **Also**: Removed stale duplicate TIER_COOLDOWN_S=42 line (R2263 comment) — compose had two TIER_COOLDOWN_S entries

## Pre-Change Data (6h window, R2266 regime, KEY=42, TIER=42)

| Metric | Value |
|--------|-------|
| Total requests | 55 |
| OK | 40 (72.7%) |
| Fail | 15 (10 ATE + 5 zombie) |
| 429 cycling rate | 36.36% (20/55 requests) |
| Peer-fallback events | 0 (budget too tight: 100+122=222>192) |

### Per-Model Breakdown
| Model | Total | OK | Fail | Avg ms | Fail types |
|-------|-------|-----|------|--------|------------|
| glm5_2_nv | 42 | 30 (71.4%) | 12 | 35,027 | 7 ATE + 5 zombie |
| dsv4p_nv | 13 | 10 (76.9%) | 3 | 44,895 | 3 ATE |

### Tier Attempt Errors (all glm5_2_nv)
| Error | Count |
|-------|-------|
| 429_nv_rate_limit | 32 |
| pexec_429 | 12 |
| pexec_timeout | 11 |
| pexec_success | 8 |
| SSLEOFError | 1 |
| RemoteDisconnected | 2 |
| Total 429 events | 44 |

## Root Cause Analysis

KEY_COOLDOWN_S=42 and TIER_COOLDOWN_S=42 are both in the **429 anti-pattern zone (1-65s)**. Per the 429-cycling-anti-pattern reference, values in this range are WORSE than 0s because they create medium-length cooldowns that:

1. Hammer NVCF API with requests at the worst possible cadence — not fast enough to clear before rate limits reset, not slow enough to let NVCF fully release
2. The R2126 study proved: 64s → 58% 429 cycling; 66s → 0%. The boundary is function-specific and verified at 66s.
3. 42s creates a resonance with NVCF's internal rate-limit windows, causing 36% of requests to experience key cycling with 429s

The iron law requires KEY_COOLDOWN = TIER_COOLDOWN. R2266 correctly aligned them at 42, but 42 itself is in the danger zone.

## Change: KEY_COOLDOWN_S and TIER_COOLDOWN_S 42→66

- **KEY_COOLDOWN_S**: 42→66 (+24s) — escape anti-pattern zone, match R2126 verified safe boundary
- **TIER_COOLDOWN_S**: 42→66 (+24s) — KEY=TIER=66 per iron law
- **Cleanup**: Removed stale duplicate TIER_COOLDOWN_S=42 line (R2263 comment) that was still in compose

### Budget Constraint Verification
- KEY+TIER = 66+66 = 132 < 192 ✓ (60s margin)
- glm5_2_nv: 24+66 = 90 < 100 ✓ (1 key attempt fits)
- dsv4p_nv: 24+66 = 90 < 135 ✓ (1 key attempt fits)
- 66s is the verified minimum safe boundary, not 60s — R2126 proved 64s was catastrophic

## Verification
- `docker exec nv_gw env`: KEY_COOLDOWN_S=66 ✓, TIER_COOLDOWN_S=66 ✓
- `curl http://localhost:40006/health`: {"status": "ok"} ✓
- `docker ps`: nv_gw Up, healthy ✓
- `grep KEY_COOLDOWN\|TIER_COOLDOWN /opt/cc-infra/docker-compose.yml`: 1 KEY_COOLDOWN_S=66, 1 TIER_COOLDOWN_S=66 ✓ (no duplicates)

## Post-Deploy State
| Parameter | Old | New |
|-----------|-----|-----|
| KEY_COOLDOWN_S | 42 | **66** |
| TIER_COOLDOWN_S | 42 | **66** |
| TIER_TIMEOUT_BUDGET_S | 192 | 192 |
| UPSTREAM_TIMEOUT | 24 | 24 |
| NVU_PEER_FALLBACK_TIMEOUT | 122 | 122 |
| NVU_TIER_BUDGET_DSV4P_NV | 135 | 135 |
| NVU_TIER_BUDGET_GLM5_2_NV | 100 | 100 |

## ⏳ 轮到HM1优化HM2