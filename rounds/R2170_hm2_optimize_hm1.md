# R2170 (HM2→HM1): KEY_COOLDOWN_S 40→38 (-2s)

**Time**: 2026-07-21 15:25 UTC
**Author**: opc2_uname (HM2)
**Pattern**: Alternating TIER→KEY (R2169 TIER 24→22, R2170 KEY 40→38)

## Pre-Change Data

### 6h Window
- 33 req, 27 OK (81.8% SR), 6 fail
  - 3 dsv4p ATE (all at 03:39-03:40 UTC, pre-R2168, tiers_tried_count=1, fallback_tiers_used={dsv4p_nv}, 0 tier_attempts → pre-empted)
  - 3 glm5_2 zombies (pexec_success + empty-200, model-side, not config-fixable)
- Post-R2167 2h: 8/7 OK (87.5%) — TIER 24→22 already improving
- Recent 30-min: 2/2 OK (100%)

### Current Config (pre-change)
- KEY_COOLDOWN_S=40
- TIER_COOLDOWN_S=22 (R2169)
- UPSTREAM_TIMEOUT=24
- TIER_TIMEOUT_BUDGET_S=153
- NVU_TIER_BUDGET_DSV4P_NV=48
- NVU_TIER_BUDGET_GLM5_2_NV=28

### Tier Attempts for ATE
- 0 rows in nv_tier_attempts for all 3 ATE requests → all pre-empted (cooldown blocking before first key attempt)
- R2169 TIER 24→22 addresses this (TIER was the blocker for pre-emption)

### Zombie Analysis
- 3 glm5_2 zombies: pexec_success at 6302-13846ms + SSLEOFError retry → empty-200 rescue
- Model-side issue, not config-fixable via KEY/TIER tuning

## Change

**KEY_COOLDOWN_S: 40 → 38 (-2s)**

- KEY+TIER+GLM5_2_BUDGET = 38 + 22 + 28 = 88 < 153 (65s margin)
- Alternating TIER→KEY pattern continues
- Conservative 2s reduction; safe per budget envelope
- 铁律: only HM1

## Verification

- `docker exec nv_gw env | grep KEY_COOLDOWN_S` → `KEY_COOLDOWN_S=38` ✅
- `/health` → `{"status": "ok"}` ✅
- Container restarted cleanly ✅
## ⏳ 轮到HM1优化HM2
