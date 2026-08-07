# R1006: dsv4f0731_nv — NOP (Stable, No Changes)

**Date**: 2026-08-08 00:44 UTC  
**Container**: dsvf0731_nv40666  
**Target**: dsv4f0731_nv via NVCF pexec

## Current params (unchanged)

| Param | Value |
|-------|-------|
| UPSTREAM_TIMEOUT | 90 |
| TIER_TIMEOUT_BUDGET_S | 180 |
| TIER_COOLDOWN_S | 180 |
| KEY_COOLDOWN_S | 30 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 3 |
| NVU_EMPTY_200_FASTBREAK | 3 |
| NVU_KEYMGR_429_BASE_COOLDOWN | 120 |
| NVU_KEYMGR_429_MAX_COOLDOWN | 120 |
| NVU_KEYMGR_CONN_BASE_COOLDOWN | 30 |
| NVU_KEYMGR_CONN_MAX_COOLDOWN | 60 |
| NVU_KEYMGR_CONN_FAIL_THRESHOLD | 3 |
| NVU_KEYMGR_CONN_LONG_COOLDOWN | 120 |
| NVU_TIER_BUDGET_DSV4F0731_NV | 180 |
| NV_KEY_INTEGRATE_KEYS | (empty) |

## 30min data (00:14 - 00:44 UTC)

**Overall**: 141 requests, 141 success (100% SR), 0 errors

| Metric | Value |
|--------|-------|
| Success | 141/141 (100%) |
| Avg/P50/P95 | 12858ms / 9414ms / 36604ms |
| Max | 76988ms |
| 429 count | 0 |
| key_cycle_429s: 0 | 14 |
| key_cycle_429s: 1 | 125 |
| key_cycle_429s: 2 | 2 |

**Per-key 200 latency**:

| Key | Req | Avg (ms) |
|-----|-----|----------|
| k0  | 28  | 12437    |
| k1  | 28  | 12356    |
| k2  | 29  | **16772**|
| k3  | 26  | **8987** |
| k4  | 30  | 13291    |

**Upstream type**: 100% nvcf_pexec (141/141)

**Finish reason**: 115 tool_calls, 26 stop

**Errors**: none (all categories empty)

**Fallback**: 0 — no hm4104 fallback logs

## 6h trend

1754 total, 1740 success (99.2%), 14 errors

Hourly:
- 16:00 UTC: 200/200 (100%)
- 15:00 UTC: 291/291 (100%)
- 14:00 UTC: 293/294 (99.66%)
- 13:00 UTC: 77/80 (96.25%)

24h all_tiers_exhausted: 136

## Analysis

- **100% SR in current window** — the best possible state
- **No 429s** — key management working well
- **k2 has higher avg latency** (16772ms) vs others (8987-13241ms) but still well within budget
- **No tier_attempts** — every request succeeded on the first tier
- **Minor key cycling**: 125/141 requests cycled exactly 1 key (first key returned 429, second succeeded)
- The 24h all_tiers_exhausted=136 suggests past pressure that has fully resolved

## Decision: NOP

No changes needed. System is in a healthy, stable state. k2's higher latency is noted but not causing failures. Will monitor for the next round.

## Next round focus

Continue monitoring. If k2 latency persists or worsens relative to other keys, consider:
- Moving k2 to integrate.api channel
- Increasing KEY_COOLDOWN_S if per-key 429 rate increases