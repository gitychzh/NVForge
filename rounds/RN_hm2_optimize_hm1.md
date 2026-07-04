# R673: HM2→HM1 — NVU_FORCE_STREAM_UPGRADE_TIMEOUT 44→43 (−1s)

**Date**: 2026-07-04 08:40 UTC

## Data Summary (6h window)

| Metric | Value |
|--------|-------|
| Total requests | 73 |
| OK (200) | 69 (94.5%) |
| Fail | 4 (ATE: `all_tiers_exhausted`, server-side NVCF non-config fixable) |
| Log errors | 0 |
| key_cycle_429s | 0 |
| pexec | 62/59 OK, avg TTFB=4668ms, avg dur=4893ms |
| integrate | 11/10 OK, avg TTFB=77563ms, avg dur=146779ms |
| ATE (NULL upstream) | 4 (max dur=141293ms) |
| p50 latency | 3100ms |
| p95 latency | 118788ms |

### 24h errors
- `all_tiers_exhausted`: 22 (100% server-side NVCF, non-config fixable)

### Per-model breakdown
| Model | cnt | OK | avg ms | max dur |
|-------|-----|----|--------|---------|
| glm5_2_nv | 59 | 56 | 5315 | 65265 |
| dsv4p_nv | 10 | 9 | 154931 | 494127 |
| kimi_nv | 4 | 4 | 13763 | 29294 |

### Per-key (glm5_2_nv only)
| Key | cnt | OK | avg ms | p50 ms |
|-----|-----|----|--------|--------|
| K1 | 11 | 11 | 2844 | 2602 |
| K2 | 11 | 11 | 4735 | 3021 |
| K3 | 11 | 11 | 3810 | 2558 |
| K4 | 11 | 11 | 5540 | 4815 |
| K5 | 12 | 12 | 10002 | 3313 |

### Hourly trend
| Hour | cnt | OK | avg ms |
|------|-----|----|--------|
| 19:00 | 4 | 4 | 3494 |
| 20:00 | 4 | 4 | 2541 |
| 21:00 | 4 | 4 | 6151 |
| 22:00 | 4 | 4 | 3780 |
| 23:00 | 12 | 9 | 9610 |
| 00:00 | 4 | 4 | 4056 |
| 01:00 | 4 | 4 | 18776 |
| 02:00 | 19 | 18 | 84179 |
| 03:00 | 4 | 4 | 2949 |
| 04:00 | 4 | 4 | 2840 |
| 05:00 | 3 | 3 | 2566 |
| 06:00 | 2 | 2 | 2222 |
| 07:00 | 2 | 2 | 2458 |
| 08:00 | 3 | 3 | 2615 |

### Log observations
- 2 thinking injection log entries (glm5_2_nv), both with extended timeout 44s (now 43s)
- No errors, no warnings, no panics

## Optimization

**Parameter**: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` 44→43 (−1s)

**Rationale**:
- R656-R673 trajectory continued: 61→59→58→57→56→55→54→53→52→51→50→49→48→47→46→45→44→43 (−18s total)
- Zero-error regime sustained: 0 log errors, 0 kc429, 0 fallback triggered
- All 4 failures are server-side `all_tiers_exhausted` — non-config fixable, unrelated to timeout
- integrate 11/10 OK, pexec 62/59 OK — streaming paths unaffected
- Margin: 43s >> UPSTREAM_TIMEOUT=25s (18s safe margin)
- Conservative: −1s per round, multi-round accumulation
- Log confirms thinking timeout extension at 44s → now 43s, still safe

**Verification**:
- Compose line 492: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "43"` ✅
- Docker compose config: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "43"` ✅
- Container env: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=43` ✅
- 3-way consistency confirmed ✅
- Container restarted cleanly, proxy healthy ✅

## Iron Rule Compliance
- ✅ Single parameter per round
- ✅ Only changed HM1, never HM2

## ⏳ 轮到HM1优化HM2