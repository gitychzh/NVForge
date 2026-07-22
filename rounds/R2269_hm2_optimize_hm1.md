# R2269 (HM2→HM1): NVU_TIER_BUDGET_DSV4P_NV 135→150 (+15s)

## Context
- HM2 round, HM1 target. Iron law: only HM1 never HM2.
- Previous round: R2268 NVU_TIER_BUDGET_GLM5_2_NV 100→110.
- HM1 container: nv_gw, started_at 2026-07-22T18:13:02Z (R2268 restart).

## Data (6h window, collected ~2026-07-22T18:30Z)
- 66 req: 49 OK (74.2%), 17 fail
- dsv4p_nv: 24 req, 19 OK (79.2%), 5 ATE 502
- glm5_2_nv: 42 req, 30 OK (71.4%), 5 ATE 429 + 5 zombie + 2 ATE 502
- 30min: 15 req, 11 OK (73.3%), 4 fail
- KEY cycle 429: 22.7% cycle2+ (15/66), glm5_2_nv specifically 35.7% (15/42)

## ATE analysis
- All 19 ATE requests have 0 tier_attempts — no tier-level retries; all-keys-cooldown cascading
- dsv4p_nv ATE durations: 10s, 27s, 62s, 64s, 120s (2 large 120s with 342K/359K chars)
- KEY_COOLDOWN=66, TIER_COOLDOWN=66, per-key=90s, global budget=192
- dsv4p_nv budget=135 → per-key=90s, margin only 45s to clear 66s cooldown
- 120s ATE: large requests exhaust budget during empty-200 all-keys cooldown cycle

## Change
- **NVU_TIER_BUDGET_DSV4P_NV: 135 → 150 (+15s)**
- Per-key: 90s → 100s, margin: 45s → 60s (nearly 2x buffer)
- Logic: 120s ATE requests need budget to accommodate 2 full key cycles (66s+66s=132s), 150 provides safe margin
- Single param only. dsv4p_nv ATE 0 tier_attempts pattern matches all-keys-cooldown cascading addressed by budget increase

## Verification
- Compose: `NVU_TIER_BUDGET_DSV4P_NV=150` ✓
- Running env: `NVU_TIER_BUDGET_DSV4P_NV=150` ✓ (no drift)
- Health: 200 ✓
- Restarted: 2026-07-22T18:39:15Z

## ⏳ 轮到HM1优化HM2