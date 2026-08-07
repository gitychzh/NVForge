# R1108: dsv4f0731_nv NOP — 状态稳定，30min SR=99.2%

**Date**: 2026-08-07 22:32 UTC
**Container**: dsvf0731_nv40666 (port 40666)
**Model**: dsv4f0731_nv (DeepSeek V4 Pro via NVCF)

## Parameter Change
**None** — NOP round.

## Data (30min window, 130 requests)

| Metric | Value |
|--------|-------|
| Total | 130 |
| Success | 129 |
| SR | 99.2% |
| Avg latency | 12,832ms |
| Errors | zombie_empty_completion × 1 (key 2, 2834ms) |
| 429 count | 0 |
| Fallback (hm4104) | 0 |
| upstream | 100% nvcf_pexec |

### Per-key 200 latency
| Key | Count | Avg ms | P95 ms |
|-----|-------|--------|--------|
| 0 | 24 | 12,516 | 42,829 |
| 1 | 29 | 12,111 | 39,982 |
| 2 | 22 | 12,054 | 32,869 |
| 3 | 25 | 10,390 | 19,837 |
| 4 | 29 | 16,854 | 56,567 |

### Per-key errors
- key 2: zombie_empty_completion × 1 (2834ms)

### Finish reason
- tool_calls: 102
- stop: 27

### Trend
| Window | Total | Success | Errors | SR |
|--------|-------|---------|--------|----|
| 6h | 1,842 | 1,818 | 24 | 98.7% |
| 3h 14:00 | 141 | 140 | 1 | 99.3% |
| 3h 13:00 | 282 | 279 | 3 | 98.9% |
| 3h 12:00 | 297 | 294 | 3 | 99.0% |
| 3h 11:00 | 156 | 155 | 1 | 99.4% |

### 24h all_tiers_exhausted: 167 (30min: 0)

## Analysis
All metrics are healthy:
- 30min SR 99.2%, 6h SR 98.7% — excellent
- Zero 429s in recent window
- Zero fallback in last 5min
- Per-key latencies are balanced (k4 slightly slower at 16.8s avg, but within normal variance)
- Only 1 error: zombie_empty_completion on key 2 — isolated, not a pattern
- 100% pexec routing (no integrate used in this window)

The 24h ATE count of 167 is notable but 30min ATE = 0, indicating the tier handles current load without exhaustion. Current parameters (UPSTREAM_TIMEOUT=90, TIER_BUDGET=180, KEY_COOLDOWN=30, TIER_COOLDOWN=90) are working well.

## Next Steps
Continue monitoring. No parameter changes needed. If ATE starts reappearing in shorter windows, consider tuning KEY_COOLDOWN_S or TIER_COOLDOWN_S.