# R1109: dsv4f0731_nv NOP — 状态稳定，30min SR=99.3%

**Date**: 2026-08-07 22:48 UTC
**Container**: dsvf0731_nv40666 (port 40666)
**Model**: dsv4f0731_nv (DeepSeek V4 Pro via NVCF)

## Parameter Change
**None** — NOP round.

## Data (30min window)

| Metric | Value |
|--------|-------|
| Total | 143 |
| Success | 142 |
| SR | 99.3% |
| Avg latency | 11,812ms |
| P50 latency | 9,864ms |
| P95 latency | 31,155ms |
| Errors | zombie_empty_completion × 1 (key 2, 2,834ms) |
| 429 count | 0 |
| Fallback (hm4104) | 0 |
| upstream | 100% nvcf_pexec |

### Per-key 200 latency

| Key | Count | Avg ms | P50 ms | P95 ms |
|-----|-------|--------|--------|--------|
| 0 | 28 | 9,131 | 8,054 | 14,952 |
| 1 | 30 | 12,240 | 9,500 | 40,422 |
| 2 | 29 | 13,196 | 9,784 | 37,892 |
| 3 | 29 | 10,849 | 9,003 | 27,468 |
| 4 | 28 | 13,744 | 11,125 | 20,308 |

### Per-key errors
- key 2: zombie_empty_completion × 1 (2,834ms)

### Finish reason
- tool_calls: 114
- stop: 28

### Trend

| Window | Total | Success | Errors | SR |
|--------|-------|---------|--------|----|
| 6h | 1,851 | 1,829 | 22 | 98.8% |
| 3h 14:00 | 218 | 217 | 1 | 99.5% |
| 3h 13:00 | 282 | 279 | 3 | 98.9% |
| 3h 12:00 | 297 | 294 | 3 | 99.0% |
| 3h 11:00 | 80 | 80 | 0 | 100% |

### 24h all_tiers_exhausted: 157 (30min: 0)

## Analysis

All metrics remain healthy:

- **30min SR 99.3%**, 6h SR 98.8% — excellent
- **Zero 429s** in current window; key_cycle_429s: k0=26, k1=117 (historical, not current)
- **Zero fallback** in hm4104 logs — primary link fully serving
- **Per-key balance improved**: key 4 avg down from 16.8s (R1108) to 13.7s, keys 0-3 latency in 9-13s range — well balanced
- **1 error**: zombie_empty_completion on key 2 — isolated NVCF backend anomaly at 2.8s (didn't even reach meaningful response time)
- **100% pexec routing** — integrate path completely idle
- **All_tiers_exhausted** dropped from 167 (R1108) to 157 with zero in the last hours — the ATE spike from Aug 6 has fully cleared; recent 5h only show zombie/IncompleteRead errors (backend quality, not budget)

Current parameters (UPSTREAM_TIMEOUT=90, TIER_BUDGET=180, KEY_COOLDOWN=30, TIER_COOLDOWN=90) are correctly tuned for this load pattern.

## Next Steps
Continue monitoring. No parameter changes needed. If zombie_empty_completion errors increase or ATE reappears, investigate NVCF backend quality rather than tuning gateway parameters.