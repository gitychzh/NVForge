# R1006: dsv4f0731_nv40666 — NOP (stable, no action needed)

**Date**: 2026-08-07 18:38 UTC
**Container**: dsvf0731_nv40666 (port 40666, DeepSeek V4 Pro via NVCF)
**Model**: dsv4f0731_nv

## Current Parameters (unchanged)

| Parameter | Value |
|-----------|-------|
| UPSTREAM_TIMEOUT | 90 |
| TIER_TIMEOUT_BUDGET_S | 180 |
| NVU_TIER_BUDGET_DSV4F_NV | 180 |
| KEY_COOLDOWN_S | 30 |
| TIER_COOLDOWN_S | 90 |
| NVU_KEYMGR_429_BASE_COOLDOWN | 120 |
| NVU_KEYMGR_429_MAX_COOLDOWN | 120 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 3 |
| NVU_EMPTY_200_FASTBREAK | 3 |
| NVU_BUFFER_TIMEOUT_STAIRS | 90,90,90,90,90 |
| NVU_PROBE_TIMEOUT | 10 |

## Data (30-min window, 18:08–18:38 UTC)

| Metric | Value |
|--------|-------|
| Total requests | 176 |
| Success | 174 |
| Failed | 2 |
| **SR%** | **98.9%** |
| Avg latency | 9826ms |
| P50 latency | 8330ms |
| P95 latency | 23102ms |
| Max latency | 30379ms |
| 429 count | 0 |
| fallback_occurred | 0 |
| all_tiers_exhausted | 0 (in window) |

## Error Distribution

| Error Type | Count | Avg elapsed |
|------------|-------|-------------|
| zombie_empty_completion | 2 | 3047ms |

Minimal errors — 2 `zombie_empty_completion` (empty 200 responses) on keys 0 and 2, both under 3s. Non-recurring, within normal noise.

## Upstream Type

- **nvcf_pexec**: 176/176 requests (100%) — no integrate routing active

## Finish Reason

- tool_calls: 145 (82.4%)
- stop: 29 (16.5%)
- (weighted shift ratio = tool_calls/stop ≈ 5:1 — expected for this model)

## Per-Key Performance

| Key | Requests | Avg (ms) | P95 (ms) |
|-----|----------|----------|----------|
| 0 | 35 | 9536 | 17917 |
| 1 | 32 | 8056 | 14623 |
| 2 | 35 | 9716 | 27924 |
| 3 | 36 | 10121 | 22122 |
| 4 | 36 | 11867 | 24076 |

Key 2 has slightly elevated P95 (27.9s vs 14.6–24.1s range), but no errors on it in current window. Minor variance — no single key shows persistent degradation.

## Trends

- **6h SR**: 97.6% (1691/1733)
- **3h hourly**: 98.7% → 98.6% → 96.5% → 98.0% — stable, no degradation
- **24h all_tiers_exhausted**: 301 (across all tiers, not specific to this model)
- **Fallback (hm4104)**: 0 fallback events in last 5min — model is healthy

## Assessment: NOP

All indicators are green:
1. **SR 98.9%** — well above 95% threshold
2. **Zero 429s** — no rate limiting pressure
3. **Zero pexec timeouts** — upstream stable
4. **Zero integrate routing** — pexec is handling everything fine
5. **Zero fallback** — hm4104 adapter sees no issues
6. **Stable latency** — avg ~10s/P50 ~8s/P95 ~23s, consistent with NVCF pexec profile
7. **No at-risk keys** — minor variance but no persistent failures

No parameter changes needed. The current configuration is working well.

## Next Round Suggestion

Monitor and re-evaluate in next cycle. If SR drops below 95% or new error types emerge, investigate:
- `zombie_empty_completion` frequency increase → consider lowering `NVU_EMPTY_200_FASTBREAK` from 3 to 2
- P95 latency creep above 30s → consider lowering `UPSTREAM_TIMEOUT` from 90 to 75 (matching P95 + buffer)