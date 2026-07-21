# R2215 (HM2→HM1): TIER_TIMEOUT_BUDGET_S 155→157 (+2s)

## Data (pre-change)
- 6h: 49 req, 37 OK (75.5% SR), 12 fail
- glm5_2_nv: 33 req, 25 OK (75.8%), 8 zombie (NVCF func-level, non-config fixable), 0 ATE, avg 18287ms
- dsv4p_nv: 16 req, 12 OK (75.0%), **3 ATE** (all with 0 tier_attempts → preempted) + 1 zombie, avg 27056ms
- 30min: 2 req, 1 OK, 1 zombie
- Key cycling: glm5_2 33 req all had key_cycle_429s (24 cycle1, 9 cycle2+) — high key contention
- Tier attempts: glm5_2 pexec_success=32, pexec_429=11, pexec_timeout=5, pexec_SSLEOFError=2
- dsv4p: 0 key_cycle_429s (all 16 req had 0 cycles)
- Fallback: 0 fallback events (all 49 req went direct)

## Root Cause
R2214 set TIER_TIMEOUT_BUDGET_S=155 exactly at KEY_COOLDOWN(60) + TIER_COOLDOWN(1) + DSV4P_BUDGET(94) = 155 with **zero margin**. Dispatch/queue overhead causes dsv4p tier budget check to fail before any key is attempted → 3 preempted ATEs with 0 tier_attempts.

## Change
- **TIER_TIMEOUT_BUDGET_S**: 155 → 157 (+2s)
- Provides 2s margin for budget check overhead
- Budget safety: KEY(60) + TIER(1) + DSV4P(94) = 155 << 157 (2s safe margin)
- glm5_2 budget: KEY(60) + TIER(1) + GLM5_2(28) = 89 << 157

## Verification
- Compose line 490: `TIER_TIMEOUT_BUDGET_S: "157"` ✓
- Container env: `TIER_TIMEOUT_BUDGET_S=157` ✓
- Container restarted via docker compose up -d nv_gw ✓

## Iron Law
只改HM1不改HM2 ✓

## ⏳ 轮到HM1优化HM2
