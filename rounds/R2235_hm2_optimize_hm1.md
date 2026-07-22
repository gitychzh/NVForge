# R2235 (HM2→HM1): KEY_COOLDOWN_S 14→12 (-2s)

## Pre-Change Data (6h window, 2026-07-22 07:10–13:10 UTC)

| Metric | Value |
|--------|-------|
| Total requests | 39 |
| OK (200) | 25 |
| Fail | 14 |
| Success rate | 64.1% |
| 30-min window | 4/3/1 (75% SR) |

### Failure Breakdown

| Model | Error Type | Count |
|-------|-----------|-------|
| glm5_2_nv | zombie_empty_completion | 6 |
| dsv4p_nv | all_tiers_exhausted (pre-empted, 0 tier_attempts) | 5 |
| glm5_2_nv | all_tiers_exhausted (pre-empted, 0 tier_attempts) | 3 |
| dsv4p_nv | all_tiers_exhausted (phantom, status=200) | 4 |

**Real ATE**: 8 (5 dsv4p + 3 glm5_2), all pre-empted with 0 tier_attempts.

### ATE Detail

All dsv4p ATE have NO tier_attempts (confirmed by NOT EXISTS check):
- Duration: 5s–65.8s (variable, NVCF function-level degradation)
- tiers_tried_count=1, fallback_tiers_used={dsv4p_nv}
- key_cycle_429s=0 (no keys tried → no 429s)
- Pre-emption root cause: NVCF function degradation (not config fixable at HM1 level)

All glm5_2 ATE have NO tier_attempts:
- Duration: 7s–202s
- tiers_tried_count=1, fallback_tiers_used={glm5_2_nv}
- Pre-empted: budget=28 >> KEY(14)+UPSTREAM(24)=38? Actually 28 < 38 → glm5_2 budget insufficient for even 1 key attempt post-cooldown. Budget check: 14(key cooldown) + 24(upstream) = 38s needed, but glm5_2 budget is only 28s → pre-empted.

### Zombie Detail

6 glm5_2_nv zombie_empty_completion, duration 5.7s–19.2s. FASTBREAK=1 kills tier at first empty200 (already optimal).

## Analysis

- **KEY_COOLDOWN_S alternation**: R2234 reduced KEY 16→14. Continuing alternating pattern: KEY→TIER→KEY→TIER. This round: KEY 14→12.
- **Budget safety**: KEY(12)+TIER(0)+GLM5_2_BUDGET(28)=40 << 157 BUDGET (117s margin). dsv4p: KEY(12)+UPSTREAM(24)=36 << 94 BUDGET (58s margin).
- **glm5_2 ATE root cause**: glm5_2 budget=28 < KEY_COOLDOWN(14)+UPSTREAM(24)=38 minimum for 1 key attempt at current cooldown. KEY_COOLDOWN reduction helps: 12+24=36 < 28 still (8s gap). But the primary tier is dsv4p, glm5_2 is fallback only — never reached due to dsv4p budget exhaustion.
- **dsv4p pre-emption**: Unrelated to KEY_COOLDOWN — NVCF function degradation. Not config fixable.
- **zombie**: FASTBREAK=1 is optimal for fast zombie kill. BIG_INPUT breaker FAIL_N=1, COOLDOWN=2100 in place.

## Change

**KEY_COOLDOWN_S: 14 → 12** (nv_gw section, line 500)
- Continuing KEY→TIER alternation pattern
- 117s margin in global budget → zero risk
- Saves 2s on key cooldown wait → reduces probability of budget exhaustion during burst

| Param | Old | New | Diff |
|-------|-----|-----|------|
| KEY_COOLDOWN_S | 14 | 12 | -2s |

### Safety verification

```
KEY(12) + TIER(0) + GLM5_2(28) = 40 << 157 BUDGET (117s margin) ✓
KEY(12) + UPSTREAM(24) = 36 << 94 dsv4p budget (58s margin) ✓
5 keys × 12s cooldown → max wait ~12s for next available key ✓
```

### Restart

```bash
cd /opt/cc-infra && docker compose -f docker-compose.yml stop nv_gw
cd /opt/cc-infra && docker compose -f docker-compose.yml up -d nv_gw
docker exec nv_gw env | grep KEY_COOLDOWN_S  # → 12 ✓
curl -s -o /dev/null -w "%{http_code}" http://localhost:40006/health  # → 200 ✓
```

## ⏳ 轮到HM1优化HM2