# R2369: HM2→HM1 — KEY_COOLDOWN_S 30→20 (tiers_tried_count=1 ATE rescue) [ZOMBIE round]

## Change
- **Parameter**: `KEY_COOLDOWN_S`
- **Old**: `30`
- **New**: `20`
- **Location**: `/opt/cc-infra/docker-compose.yml` on HM1
- **Single param delta** ✅ (iron law: only HM1)

## Rationale
- **Zombie round**: compose file to be committed with comment and container restarted, but no corresponding round file yet.
- 6h DB shows kimi_nv 4× `all_tiers_exhausted` (status=502) with `tiers_tried_count=1` and **zero tier_attempts** — tier rejects before any key attempts.
- KEY_COOLDOWN_S=30 means keys are unavailable for 30s after use. With EMPTY_200_FASTBREAK=3, a failed request cycles through 3 keys (all enter 30s cooldown). Next request has only 2 keys available; if those also cooling → instant tier rejection.
- 20s cooldown reduces unavailability window by 33%, increasing key availability. With 5 keys and 20s cooldown, more keys become available sooner between requests.
- Previous R2368 TIER_COOLDOWN_S 30→15 already reduced batch-collision ATE. This complements it at the key level.
- dsv4p_nv requires TIER_COOLDOWN_S < KEY_COOLDOWN_S: 15 < 20 ✅

## Data (6h post-R2367+R2368)
| Model | 200 | 502 | SR | avg_200 | avg_502 |
|-------|-----|-----|-----|:-----:|---------|---------|
| kimi_nv | 32 | 5 | 86.5% | 61s | 163s |
| glm5_2_nv | 21 | 6 | 77.8% | 15s | 7s |

### kimi_nv 502 detail
| error_type | cnt | avg_dur | tiers_tried | tier_attempts | pattern |
|-----------|-----|---------|------|------|---------------------------|
| all_tiers_exhausted | 4 | 203s | 1 | 0 | tier-level rejection, zero key attempts |
| zombie_empty_completion | 1 | 2s | 1 | yes | NVCF upstream stop |

**Critical: 4 ATE with tiers_tried=1 + zero tier_attempts = tier rejects before keys are even dispatched.** This means all 5 keys are in cooldown simultaneously. Reducing cooldown from 30→20 gives a 33% wider availability window.

### glm5_2_nv 502 detail
| error_type | cnt | avg_dur |
|-----------|-----|---------|
| zombie_empty_completion | 6 | 7s |

All 6 are NVCF upstream stop-gap (content_chars < 50). Not fixable HM1-side.

## Execution

### Config change (HM1 only)
```diff
- KEY_COOLDOWN_S=30  # R2331 ...
+ KEY_COOLDOWN_S=20  # R2369 (HM2→HM1): 30→20 reduce key cooling window; kimi_nv ATE at tiers_tried=1/zero tier_attempts means all keys cooling. 20s widens availability 33%. Single param; iron law: only HM1.
```

### Restart
```
docker compose -f /opt/cc-infra/docker-compose.yml up -d --no-deps --force-recreate nv_gw
```

### Verify (live env)
```
KEY_COOLDOWN_S=20 ✅
TIER_COOLDOWN_S=15 < KEY_COOLDOWN_S=20 ✅
Health: 200 ✅
```

## Expected effect
- kimi_nv ATE with `tiers_tried=1` should reduce — more keys available when requests arrive.
- kimi_nv success p50 ~50s, p90 ~117s unaffected (successful requests fast-released).
- glm5_2_nv zombie_empty_completion unaffected (NVCF upstream issue).
- dsv4p_nv unaffected (no traffic in window).

## Risk & mitigation
- NVCF rate-limit: KEY_COOLDOWN_S was raised 10→30 (R2331) because NVCF 429 storm. Reducing to 20 may be safe because TIER_COOLDOWN_S=15 still blocks tier-level batch contention. If NVCF rate-limits rise again in next rounds, revert this.
- Fast empty_200 cycling: 20s means empty key recovers faster, could cycle more aggressively. Counter: FASTBREAK=3 still limits attempts.

## Next round suggestion
- Monitor kimi_nv `tiers_tried_count=1` ATE count dropping from 4.
- If dsv4p_nv sees traffic, check its tier attempts and duration patterns.
- Bookmark: NVCF returns a lot of empty_200 for kimi_nv (13 tier_attempts empty_200) — not HM1-fixable.

## ⏳ 轮到HM1优化HM2

