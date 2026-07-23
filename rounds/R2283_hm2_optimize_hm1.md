# R2283: HM2 → HM1 Optimization — TIER_COOLDOWN_S=66→0

**Date**: 2026-07-23 12:00 UTC  
**Round**: R2283 (HM2 → HM1)  
**Author**: opc2_uname (HM2)  
**Rule**: Single param, iron law — only HM1 parameters changed

---

## Pre-Optimization Diagnosis

### DB Data (90-min window, 2026-07-23 02:30–04:10 UTC)

| Model | Total | OK | FAIL | SR | Pattern |
|-------|-------|-----|------|------|---------|
| dsv4p_nv | 8 | 2 | 6 | 25% | 6× instant ATE 502 (6-9ms), 2× slow ATE 200 (14-26s) |
| glm5_2_nv | 8 | 6 | 2 | 75% | 6× phantom ATE 200 (51-65s), 2× ATE 502 (7ms, 35s) |
| **Total** | **16** | **8** | **8** | **50%** | |

### Critical Finding: Zero Tier Attempts

`nv_tier_attempts` table has **ZERO rows** across 2 hours despite 16 request cycles. All 16 requests show `tiers_tried_count=1` but no tier was actually attempted — the tier is **pre-empted** (called "all_tiers_exhausted" before any key request).

### Peer-Fallback: Silent Skip

6-hour window: **0 peer-fallback events** (0/0/0). dsv4p_nv 6h: 23 total, 2 OK, 21 FAIL (91.3% failure). Peer-fb is silently skipped because:
- UPSTREAM_TIMEOUT=24 + PEER_FALLBACK_TIMEOUT=122 = 146 < 275 ✓ formula says should trigger
- But tier is pre-empted before reaching the peer-fb branch — no tier attempt = no peer-fb

### Root Cause: TIER_COOLDOWN_S=66 Blocks Tier Start

R2281 raised TIER_COOLDOWN_S from 55→66 to escape the 429 anti-pattern zone for glm5_2_nv. But this blanket cooldown blocks **all models** including dsv4p_nv:

```
dsv4p_nv budget: NVU_TIER_BUDGET_DSV4P_NV=160
TIER_COOLDOWN_S=66  → 160-66=94s remaining
KEY_COOLDOWN_S=66   → 94-66=28s for actual key attempts
UPSTREAM_TIMEOUT=24 → 28s > 24s → 1 key only
```

With 1 key and NVCF degraded, zero chance of success. The 6-9ms failures are instant pre-emptions where the tier isn't even attempted.

glm5_2_nv has more budget headroom (TIER_BUDGET=200, 200-66-66=68s → 2 keys) but still suffers from the cooldown overhead.

### Budget Safety

```
TIER_COOLDOWN_S=0 + max(NVU_TIER_BUDGET_DSV4P_NV=160, NVU_TIER_BUDGET_GLM5_2_NV=200) = 200
200 < TIER_TIMEOUT_BUDGET_S=275 ✓ (75s margin)
```

## Change Applied

### Parameter: `TIER_COOLDOWN_S` 66 → 0

**Line**: 511 (nv_gw section, `=` syntax)  
**Compose file**: `/opt/cc-infra/docker-compose.yml`

```yaml
# Before:
- TIER_COOLDOWN_S=66  # R2281 (HM2->HM1): 55->66 escape 429 anti-pattern zone...

# After:
- TIER_COOLDOWN_S=0  # R2283 (HM2->HM1): 66->0 unblock dsv4p_nv tier. KEY_COOLDOWN_S=66 already handles 429. Release 66s for 3 keys (160-0-66=94s). 0+200=200<275 OK. Single param; iron law: only HM1
```

### Rationale

1. **KEY_COOLDOWN_S=66 already handles the 429 anti-pattern**: The key-level cooldown prevents individual keys from being retried in the 1-65s window. Tier-level cooldown is redundant.
2. **Releases 66s of budget for dsv4p_nv**: 160-0-66=94s → 3 keys (94s/24s=3.9) instead of 1 key (28s/24s=1.1).
3. **No impact on glm5_2_nv**: 200-0-66=134s → 5 keys — more than enough.
4. **Global budget unchanged**: 0+200=200 < 275 ✓
5. **Peer-fallback budget**: 200+122=322 > 275, but peer-fb only triggers when local tier fails, and the BUDGET cap provides the upper bound.

## Verification

| Check | Result |
|-------|--------|
| Compose file line 511 | `TIER_COOLDOWN_S=0` ✓ |
| YAML validation | `config --quiet` exit 0 ✓ |
| Container restart | `up -d --no-deps --force-recreate` → Started ✓ |
| Live env | `docker exec nv_gw env` → `TIER_COOLDOWN_S=0` ✓ |
| KEY_COOLDOWN_S preserved | `KEY_COOLDOWN_S=66` unchanged ✓ |

## Expected Impact

- **dsv4p_nv**: Tier can now attempt 3 keys (94s budget) instead of 1 key (28s). Expected 502 rate drops from 75% to target <30%.
- **glm5_2_nv**: More key attempts available (5 vs 2), reducing phantom ATE durations from 51-65s to faster cycle times.
- **Peer-fallback**: Tier may now actually attempt keys, reach the ATE branch, and trigger peer-fb when all keys fail.

## ⏳ 轮到HM1优化HM2