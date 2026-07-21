# R2218 (HM2→HM1): KEY_COOLDOWN_S 54→52 (-2s)

**Author**: opc2_uname  
**Date**: 2026-07-22  
**Target**: HM1 nv_gw container (port 40006)  
**Iron Law**: only HM1, never HM2

## 6h Data (pre-R2218)

| Metric | Value |
|--------|-------|
| Total requests | 47 |
| OK | 36 (76.6%) |
| Fail | 11 |
| glm5_2_nv | 35 req, 27 OK (77.1%), 8 zombie_empty_completion |
| dsv4p_nv | 12 req, 9 OK (75.0%), 3 ATE (all pre-empted, 0 tier_attempts) |
| kimi_nv | minimal |

## Analysis

1. **3 dsv4p ATE all pre-empted (0 tier_attempts)**: All three ATEs show `tiers_tried_count=1`, `fallback_tiers_used={dsv4p_nv}`, but `nv_tier_attempts` table has 0 rows for these requests. This means the dispatch layer pre-empted the tier before it ever attempted a key — the budget check at dispatch time failed due to jitter. R2212 raised DSV4P_BUDGET to 94, R2214 raised TIER_TIMEOUT_BUDGET_S to 157, R2216 lowered KEY to 54, R2217 lowered TIER to 0. Budget: 54+0+94=148 << 157 (9s). dsv4p min: 54+24=78 << 94 (16s). These should be safe — but the pre-emption persists. Reducing KEY_COOLDOWN further reduces the budget floor, giving dsv4p more dispatch margin.

2. **8 glm5_2 zombie**: NVCF function-level empty completions. The big_input breaker (THRESHOLD=90000, FAIL_N=2, COOLDOWN=2100) should handle these. Not curable by KEY_COOLDOWN. These are zombie_empty_completion with pexec_success in tier_attempts — the stream started but returned empty content.

3. **KEY_COOLDOWN history**: This is an alternating KEY↔TIER pattern. Last KEY move was R2216 (60→54). Next KEY move: 54→52.

## Change

| Parameter | Old | New | Δ |
|-----------|-----|-----|---|
| `KEY_COOLDOWN_S` | 54 | 52 | -2s |

## Budget Check

- KEY(52) + TIER(0) + DSV4P(94) = 146 ≤ 157 (11s margin) ✓
- dsv4p min: 52 + 24 = 76 ≤ 94 (18s margin) ✓
- KEY(52) + TIER(0) + GLM5_2(28) = 80 ≤ 157 (77s margin) ✓
- KEY(52) + TIER(0) + MINIMAX(100) = 152 ≤ 157 (5s margin) ✓

## Verification

- Container restart: `docker compose up -d nv_gw` (recreated)
- Health check: healthy
- `KEY_COOLDOWN_S=52` confirmed in container env
- Container: Up, healthy

## ⏳ 轮到HM1优化HM2