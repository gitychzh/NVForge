# R1006: dsv4f0731_nv NOP — all clear

**Date**: 2026-08-07 18:50 UTC
**Round type**: NOP (No modification)

## Data Summary (30min window)

| Metric | Value |
|--------|-------|
| Total requests | 146 |
| Success | 145 |
| SR | 99.3% |
| Avg latency | 10,945ms |
| P50 | 9,325ms |
| P95 | 23,841ms |
| P99 | 45,002ms |
| 429s | 0 |
| tier_attempts | 0 (all first-pass) |
| Fallback (hm4104) | 0 |
| Zombie_empty | 1 (key 0, 2958ms) |

### Per-key health

| Key | Success | Avg(ms) | P95(ms) |
|-----|---------|---------|---------|
| 0 | 30 | 10,156 | 23,632 |
| 1 | 29 | 10,251 | 16,568 |
| 2 | 30 | 11,319 | 24,507 |
| 3 | 25 | 8,558 | 13,776 |
| 4 | 31 | 14,180 | 27,442 |

### Upstream type: 100% nvcf_pexec (0 integrate)

### 6h trend: 1,727 req, SR=97.7%, 0 ATE

## Decision
No parameters changed. All indicators healthy:

- SR > 99%
- Zero 429 errors
- Zero tier-level failures
- Zero fallback to ms_gw
- Per-key latencies balanced within expected variance
- key_cycle_429s=0 (no retry needed for any request)
- Only 1 zombie_empty_completion (negligible, 0.7%)

## Next steps
- Monitor 24h ATE count (294 for all tiers — likely other tiers driving this)
- If ATE rises for dsv4f0731_nv specifically, consider tuning TIER_TIMEOUT_BUDGET or KEY_COOLDOWN
- No action needed at this time
