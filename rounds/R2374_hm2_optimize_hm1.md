# R2374 (HM2→HM1): NOP — post-R2373 insufficient evaluative data

## Change
- **Parameter**: None
- **Action**: NOP (No Operation)
- **Location**: — (no HM1 config change)
- **Single param delta**: N/A (iron law: only HM1, but no change this round)

## Rationale
- R2373 (HM2→HM1): `TIER_TIMEOUT_BUDGET_S=415→475` deployed at ~03:26 UTC.
- Purpose: close kimi_nv ATE fallback gap — after kimi_nv budget (265s) exhaust, remaining budget must ≥ glm5_2_nv budget (210s) for fallback to attempt.
- Post-R2373 observation window: 03:26–03:45 UTC (~20 min), only **13 total requests** across all models.
- Per zero-traffic NOP discipline (<20 requests = statistically meaningless, error bars >20%), no parameter change can be evaluated or justified.

## Data Collected (30-min window, 03:15–03:45 UTC)

| Model | Total | Success | Errors | SR | Avg success ms |
|---|---|---|---|---|---|
| kimi_nv | 5 | 2 | 3 | 40.0% | 7,488 |
| glm5_2_nv | 3 | 0 | 3 | 0% | — |
| dsv4p_nv | 2 | 2 | 0 | 100% | 41,282 |

### Error Breakdown
| Model | Error Type | Count | Duration Range | Analysis |
|---|---|---|---|---|
| glm5_2_nv | all_tiers_exhausted | 2 | 9–11 ms | Instant ATE; upstream_type=NULL. Pre-routing/ tier-cooldown batch collision (TIER_COOLDOWN_S=15). Not a budget issue. |
| glm5_2_nv | all_tiers_exhausted | 1 | 76,280 ms | 3× NVCFPexecTimeout (~25s each), FASTBREAK=3+budget=210s ceiling. Expected pattern. |
| kimi_nv | zombie_empty_completion | 2 | 22,400–78,174 ms | Upstream NVCF content-filter reject. Not HM1-fixable. |

### Post-R2373 Effect Assessment
- kimi_nv: 8 requests since deploy (03:26), 6 success, 2 zombie. **No tier-exhaustion ATEs observed** — promising, but 8 requests too few to conclude R2373 worked.
- Yields no evaluative signal for `TIER_TIMEOUT_BUDGET_S` effectiveness.
- Cannot distinguish: (a) gap fixed and fallback now attempts, vs (b) NVCF simply settled and fewer ATEs occurred by chance.

## Key Observations
- HM1 nv_gw container healthy, running with R2373 config confirmed:
  - `TIER_TIMEOUT_BUDGET_S=475` ✅
  - `NVU_TIER_BUDGET_KIMI_NV=265`, `GLM5_2_NV=210`, `DSV4P_NV=265` ✅
- FASTBREAK=3 continues to show Key-chain truncation for glm5_2_nv (76s ATE = 3 keys × 24s timeouts, budget ceiling at 210s). This is expected UPSTREAM issue, not budget-math — FASTBREAK pre-spending: `3×24 + next_timeout + margin` > 210. Raising budget for glm5_2_nv is blocked by PROXY_TIMEOUT ceiling (500s) and total tier budget (475s). Fixing requires `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` reduction or `PEXEC_TIMEOUT_FASTBREAK` reduction, but no data to justify change.

## Decision
- **NOP** — no parameter change this round.
- Wait for ≥30 min of stable traffic with ≥20 total requests before evaluating R2373 effectiveness.

## Natural Next Steps (for HM1→HM2 optimization)
- Monitor kimi_nv ATE with `fallback_occurred=true` post-R2373.
- If new tier-exhaustion ATEs continue but now show `fallback_occurred=true` and `tiers_tried` includes glm5_2_nv/ dsv4p_nv, then R2373 succeeded in enabling fallback.
- Continue monitoring glm5_2_nv FASTBREAK budget math if upstream 429 storm persists.

## ⏳ 轮到 HM1 优化 HM2
