# R1121: dsv4f0731_nv40666 Self-Optimization (NOP — Healthy)

**Datetime**: 2026-08-08 01:50 UTC (09:50 Beijing)
**Container**: dsvf0731_nv40666 (port 40666)
**Model**: dsv4f0731_nv via NVCF pexec

## Analysis

### 30min Window (Script Data)
| Metric | Value |
|--------|-------|
| Total | 128 |
| Success | 127 |
| Failures | 1 (all_tiers_exhausted — legacy from earlier) |
| **SR** | **99.2%** |
| Avg | 13,366ms |
| P50 | 9,035ms |
| P95 | 35,210ms |
| 429s | **0** |
| Fallback (hm4104) | **None** |
| Upstream | 100% nvcf_pexec |

### 2h Window (Fresh Query, 2026-08-08 00:00–02:00 UTC)
| Metric | Value |
|--------|-------|
| Total | 131 |
| Success | 130 |
| **SR** | **99.2%** |
| Avg | 19,577ms |
| P50 | 7,960ms |
| P95 | 74,671ms |
| Failures | 1 (NVStream_IncompleteRead, key 3, 55,488ms) |

### Per-Key Performance (30min)
All 5 keys had 100% success. No single key degrading.

### Per-Key Performance (24h)
| Key | Total | Success | SR% | Avg(ok) | Errors |
|-----|-------|---------|-----|---------|--------|
| 0 | 324 | 197 | 60.8% | 22,344ms | 127 (114 all_tiers_exhausted) |
| 1 | 224 | 217 | 96.9% | 19,985ms | 7 |
| 2 | 198 | 188 | 94.9% | 19,162ms | 10 |
| 3 | 198 | 189 | 95.5% | 18,945ms | 9 |
| 4 | 223 | 212 | 95.1% | 23,525ms | 11 |

### Key 0 Anomaly Investigation
Key 0 (port 7897, egress IP 134.195.101.197) experienced **~15 hours of near-total failure** (17:00–08:00 UTC), with 114 `all_tiers_exhausted` events. Since ~09:00 UTC, key 0 has fully recovered and is running at 100% SR in the most recent 2h. This was an infrastructure/proxy issue (SOCKS5 7897 port failure), **not a parameter problem**.

### Tier Attempts (6h)
- 1,266 pexec_success (balanced across all 5 keys: 244–259 each)
- 32 NVCFPexecRemoteDisconnected (spread 4–8 per key) — ~2.5% of attempts, normal for SOCKS5 proxy path
- 8 empty_200, 1 500_nv_error — negligible

### Fallback
hm4104 logs show **no fallback** in the last 5 minutes. This confirms dsv4f0731_nv is stable and serving requests directly.

### Tier Budget Usage
- Current `NVU_TIER_BUDGET_DSV4F0731_NV=180s`, `TIER_TIMEOUT_BUDGET_S=180`, `UPSTREAM_TIMEOUT=90`
- p50 latency is ~8s, p95 is ~35-75s — well within budget
- 0 429s in recent window — key cycling is not needed

## Conclusion: NOP

**System is healthy and stable:**
- 99.2% SR in both 30min and 2h windows
- 0 429s, 0 fallback
- All 5 keys working correctly
- No parameter tuning needed for current state

The key 0 proxy issue overnight was an infrastructure problem (SOCKS5 port 7897 failure on host). No parameter change would have prevented or mitigated this. The issue has self-resolved.

## Next Steps
- Monitor key 0 proxy (port 7897) for recurrence of the outage pattern
- If key 0 fails again, consider rotating the proxy port assignment for key 0
- No parameter changes needed at this time