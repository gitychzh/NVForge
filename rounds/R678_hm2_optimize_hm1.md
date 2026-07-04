# R678: HM2→HM1 — NVU_FORCE_STREAM_UPGRADE_TIMEOUT 39→38 (−1s)

**Date**: 2026-07-04 10:00 UTC

## Data Summary (6h window)

| Metric | Value |
|--------|-------|
| Total requests | 104 |
| OK (200) | 100 (96.2%) |
| Fail | 4 (ATE: `all_tiers_exhausted`, server-side NVCF non-config fixable) |
| Log errors | 0 |
| key_cycle_429s | 0 |
| Avg latency | 19899ms |
| p50 latency | 3424ms |
| p95 latency | 86202ms |
| Max latency | 494127ms |
| pexec | 93/90 OK, avg TTFB=4706ms, avg dur=4891ms |
| integrate | 11/10 OK, avg TTFB=77563ms, avg dur=146779ms |
| ATE (NULL upstream key) | 3 for glm5_2_nv + 1 for dsv4p_nv = 4 total |

### Per-model (6h)
| Model | Req | OK | Avg ms | Max ms |
|-------|-----|-----|--------|--------|
| glm5_2_nv | 90 | 87 | 5168 | 65265 |
| dsv4p_nv | 10 | 9 | 154931 | 494127 |
| kimi_nv | 4 | 4 | 13763 | 29294 |

### Per-key per-model (6h)
| Model | Key | Req | OK | Avg ms | p50 ms |
|-------|-----|-----|-----|--------|--------|
| glm5_2_nv | 0 | 17 | 17 | 3538 | 3100 |
| glm5_2_nv | 1 | 17 | 17 | 4580 | 3132 |
| glm5_2_nv | 2 | 18 | 18 | 3934 | 2776 |
| glm5_2_nv | 3 | 17 | 17 | 5820 | 4660 |
| glm5_2_nv | 4 | 18 | 18 | 8333 | 3135 |
| glm5_2_nv | NULL | 3 | 0 | 2454 | 1445 (ATE) |
| dsv4p_nv | 0 | 2 | 2 | 58993 | — |
| dsv4p_nv | 1 | 3 | 3 | 84917 | — |
| dsv4p_nv | 2 | 2 | 2 | 290263 | — |
| dsv4p_nv | NULL | 1 | 0 | 141293 | — (ATE) |

### 24h errors
- `all_tiers_exhausted`: 14 (100% server-side NVCF, non-config fixable)

### Hourly trend (6h)
| Hour (UTC) | Req | OK | Avg ms |
|------------|-----|-----|--------|
| 03:00 | 4 | 4 | 2949 |
| 04:00 | 4 | 4 | 2840 |
| 05:00 | 3 | 3 | 2566 |
| 06:00 | 2 | 2 | 2222 |
| 07:00 | 2 | 2 | 2458 |
| 08:00 | 3 | 3 | 2615 |
| 09:00 | 35 | 35 | 4728 |

### DB last 10 requests
| ts | model | key | status | dur_ms | error | fallback |
|----|-------|-----|--------|--------|-------|----------|
| 09:50:28 | glm5_2_nv | 3 | 200 | 3899 | — | f |
| 09:50:25 | glm5_2_nv | 2 | 200 | 2450 | — | f |
| 09:50:16 | glm5_2_nv | 1 | 200 | 3263 | — | f |
| 09:50:07 | glm5_2_nv | 0 | 200 | 4788 | — | f |
| 09:49:51 | glm5_2_nv | 4 | 200 | 2895 | — | f |
| 09:49:47 | glm5_2_nv | 3 | 200 | 3445 | — | f |
| 09:49:31 | glm5_2_nv | 2 | 200 | 6309 | — | f |
| 09:49:25 | glm5_2_nv | 1 | 200 | 5618 | — | f |
| 09:49:17 | glm5_2_nv | 0 | 200 | 7708 | — | f |
| 09:49:13 | glm5_2_nv | 4 | 200 | 2979 | — | f |

## Optimization

**Parameter**: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` 39→38 (−1s)

**Rationale**:
- R656-R678 trajectory continued: 61→59→58→57→56→55→54→53→52→51→50→49→48→47→46→45→44→43→42→41→40→39→38 (−23s total)
- Zero-error regime sustained: 0 log errors, 0 kc429, 0 fallback triggered
- 6h 104req/100OK 96.2% — all 4 failures are server-side `all_tiers_exhausted`, non-config fixable
- pexec 93/90 OK, integrate 11/10 OK — streaming keepalive paths unaffected
- glm5_2_nv perf solid: 90req/87OK, p50 across keys 2776-4660ms fast
- Margin: 38s >> UPSTREAM_TIMEOUT=25s (13s safe margin)
- Conservative: −1s per round, multi-round accumulation

**Edit method**: sed line-anchored (per R672: `grep -n` verified line 492, then `sed -i '492s/"39"/"38"/'` + comment rewrite, no SCP needed)

**Verification**:
- Compose line 492: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "38"` ✅
- Docker compose config: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "38"` ✅
- Container env: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=38` ✅
- 3-way consistency confirmed ✅

## Iron Rule Compliance
- ✅ Single parameter per round
- ✅ Only changed HM1 (opc_uname@100.109.153.83), never HM2 (opc2_uname local)

## ⏳ 轮到HM1优化HM2