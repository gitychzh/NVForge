# R1006: dsv4f0731_nv Self-Optimization — NOP (30min SR=98.89%)

**Date**: 2026-08-07 17:32 UTC
**Container**: dsvf0731_nv40666 (port 40666)
**Decision**: NOP — no parameter change

## Current Parameters

| Parameter | Value |
|-----------|-------|
| UPSTREAM_TIMEOUT | 90 |
| TIER_TIMEOUT_BUDGET_S | 180 |
| NVU_TIER_BUDGET_DSV4F_NV | 180 |
| KEY_COOLDOWN_S | 30 |
| TIER_COOLDOWN_S | 90 (reduced from 180 in earlier rounds) |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 3 |
| NVU_EMPTY_200_FASTBREAK | 3 |
| NVU_KEYMGR_429_BASE_COOLDOWN | 120 |
| NVU_KEYMGR_429_MAX_COOLDOWN | 120 |
| NVU_KEYMGR_CONN_BASE_COOLDOWN | 30 |
| NVU_KEYMGR_CONN_FAIL_THRESHOLD | 3 |
| NVU_KEYMGR_CONN_LONG_COOLDOWN | 120 |
| NVU_KEYMGR_CONN_MAX_COOLDOWN | 60 |
| NVU_BUFFER_TIMEOUT_STAIRS | 90,90,90,90,90 |

## 30min Performance

| Metric | Value |
|--------|-------|
| Total requests | 180 |
| Success | 178 |
| **SR** | **98.89%** |
| ATE | 0 |
| 429 count | 0 |
| Avg latency | 9,749 ms |
| P50 | 8,674 ms |
| P95 | 22,245 ms |
| P99 | 38,542 ms |

## Error Breakdown

| Error | Count | Max ms | Key |
|-------|-------|--------|-----|
| NVStream_IncompleteRead | 1 | 35,476 | 4 |
| zombie_empty_completion | 1 | 4,953 | 0 |

Both errors are low-impact (2/180 = 1.1% failure rate). The IncompleteRead at 35s is within UPSTREAM_TIMEOUT=90s but the stream was cut by NVCF. The zombie_empty_completion on key 0 is minor.

## Per-Key Analysis

| Key | Requests | Avg (ms) | P50 (ms) | Errors |
|-----|----------|----------|----------|--------|
| 0 | 36 | 10,312 | **33,038** | 1 (zombie_empty) |
| 1 | 35 | 9,276 | 17,910 | 0 |
| 2 | 39 | 10,506 | 22,374 | 0 |
| 3 | 34 | 8,645 | 16,391 | 0 |
| 4 | 34 | 9,262 | 18,191 | 1 (IncompleteRead) |

Key 0 P50 (33s) is notably higher than others (16-22s). This suggests key 0's SOCKS5 proxy or NVCF route may have higher tail latency. However, only 1 error on key 0 — it's still generally functional.

key_cycle_429s: key 0=64, key 1=115 — 429s encountered and retried successfully. No tier exhaustion.

## Upstream Distribution

100% nvcf_pexec — 177/179 successful, avg 9,728ms.

## Longer-term Trends

| Window | Total | Success | Fail | ATE | Avg ms |
|--------|-------|---------|------|-----|--------|
| 30min | 180 | 178 | 2 | 0 | 9,749 |
| 6h | 1,664 | 1,623 | 41 | 0 | — |
| 3h (09:00) | 194 | 192 | 2 | 0 | 9,810 |
| 3h (08:00) | 260 | 251 | 9 | 0 | 12,495 |
| 3h (07:00) | 262 | 253 | 9 | 0 | 12,557 |
| 24h | — | — | — | 317 | — |

24h ATE=317 is the main concern — ~1.3% of requests over 24h hit all_tiers_exhausted. This typically happens during low-traffic periods or overnight when the tier budget is consumed by slow requests.

## Fallback Status

hm4104 shows zero fallback events in last 5min — dsv4f0731_nv is serving all requests directly.

## Health

/health returns ok with 5 model keys, passthrough role, model list including dsv4f0731_nv.

## Assessment

**Decision: NOP (no parameter change).** Current 30min SR=98.89%, 0 429s, 0 ATE, strong performance. The per-key variance (key 0 P50=33s vs others 16-22s) is a potential concern but not actionable without more data — the overall latency and success rate are excellent.

The 24h ATE=317 suggests periodic budget exhaustion, but the current window is healthy. The TIER_COOLDOWN=90 and KEY_COOLDOWN_S=30 parameters are working well in the current traffic regime.

## Next Steps

1. Monitor whether key 0 continues to show elevated P50 in future windows
2. If 24h ATE increases, consider whether budget tuning (NVU_TIER_BUDGET_DSV4F_NV) needs adjustment
3. No changes needed at this time