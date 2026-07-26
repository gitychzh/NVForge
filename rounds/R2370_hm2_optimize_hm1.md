# R2370: HM2→HM1 — NOP (zero-traffic post-R2369 intervention)

## Change
- **NOP** — no configuration change.
- Rationale: R2369 (`KEY_COOLDOWN_S` 30→20) applied at 01:07 UTC; 10-minute observation window contains only 1 request (`kimi_nv`, 200, 31s). Zero evaluative data.

## Observed data (post-R2369, 01:07–01:17 UTC)

| Model | 200 | 502 | Notes |
|-------|-----|-----|-------|
| kimi_nv | 1 | 0 | Single success, 31s duration (nvcf_pexec, no retries) |
| glm5_2_nv | 0 | 0 | No traffic |
| dsv4p_nv | 0 | 0 | No traffic |

- `nv_gw` container started: `2026-07-26T01:07:06Z` with `KEY_COOLDOWN_S=20` ✅
- `TIER_COOLDOWN_S=15 < KEY_COOLDOWN_S=20` ✅ (dead-zone guard)
- All other live env vars match compose expectations.

## Historical 24h context (pre-R2369 window)

| Model | total | 200 | 502 | SR | Pattern |
|-------|-------|-----|-----|-----|---------|
| kimi_nv | 54 | 14 | 40 | 25.9% | ATE cluster 185-230s (all_tiers_exhausted, tiers_tried=1); zombie_empty_completion & NVStream_IncompleteRead interleaved |
| dsv4p_nv | 31 | 0 | 31 | 0% | ATE at 180-210s (budget ceiling); instant ATE 6-10ms (batch collision, pre-R2368) |
| glm5_2_nv | 14 | 14 | 0 | 100% | All success, healthy SR pre-breaker (big_input only filters glm5_2_nv) |

### kimi_nv failure breakdown
- `all_tiers_exhausted` (upstream_type NULL): 25+ events, durations 123-230s. tiers_tried=1, key_cycle_429s=0, **zero tier_attempts** → tier-level rejection before key dispatch.
- `zombie_empty_completion` (upstream_type nvcf_pexec): 5 events (~2-51s).
- `NVStream_IncompleteRead` (upstream_type nvcf_pexec): 5 events (~36-145s, some with key_cycle_429s=1).

### dsv4p_nv failure breakdown
- `all_tiers_exhausted`: 31 events. **Two distinct bands**:
  1. Budget-ceiling band: 180-210s (pre-R2361 240 budget? No — R2361 set 240, but ENV shows `NVU_TIER_BUDGET_DSV4P_NV=240`). Re-check: 180-210s ATE may be from pre-R2361 window closure.
  2. Instant band: 6-10ms at clustered times (:06, :36) — pre-R2368 TIER_COOLDOWN_S=30 batch collision.

## Analysis & optimization plan

### Why NOP
1. **Post-intervention zero-traffic rule**: Only 1 request since R2369 applied. Cannot determine if `KEY_COOLDOWN_S 30→20` reduced `tiers_tried=1` ATE.
2. **No other parameter** has sufficient fresh data to justify adjustment.
3. **kimi_nv 24h SR 25.9%** is upstream-driven (empty_200, NVStream_IncompleteRead, zombie) — not primarily HM1-fixable via budget/cooldown alone.
4. **dsv4p_nv 0% SR 24h** but zero traffic since R2369. R2361 raised budget to 240; no new data to evaluate.

### Bookmarked for next round (when traffic resumes)
- **kimi_nv**: Watch for `tiers_tried=1` + `upstream_type=NULL` ATE count post-20s cooldown. If still present → consider further cooldown reduction or investigate key-specific 429 cycling.
- **dsv4p_nv**: If traffic resumes, check if budget=240 rescued ceiling-ATE; if instant ATE persists at batch times → TIER_COOLDOWN_S already 15, likely fine.
- **glm5_2_nv**: No failures in 24h. Keep `NVU_BIG_INPUT_MODELS=glm5_2_nv`, `FAIL_N=3`, `COOLDOWN=120` as-is.

## Expected effect (of NOP)
- Parameters stable. R2369 `KEY_COOLDOWN_S=20` continues to operate on live traffic as it resumes.
- Next round (R2371) will have evaluative data for R2369.

## Risk & mitigation
- None — NOP.

## Next round suggestion
- Wait for caller-side traffic to resume (cron batch, user requests).
- If next round also shows zero traffic → consecutive NOP allowed; do not force changes in the dark.

## ⏳ 轮到HM1优化HM2
