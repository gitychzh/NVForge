# R672: HM2→HM1 — NVU_FORCE_STREAM_UPGRADE_TIMEOUT 45→44 (−1s)

**Date**: 2026-07-04 08:30 UTC

## Data Summary (6h window)

| Metric | Value |
|--------|-------|
| Total requests | 73 |
| OK (200) | 69 (94.5%) |
| Fail | 4 (ATE: `all_tiers_exhausted`, server-side NVCF non-config fixable) |
| Log errors | 0 |
| key_cycle_429s | 0 |
| pexec | 62/59 OK, avg TTFB=4694ms, avg dur=4918ms |
| integrate | 11/10 OK, avg TTFB=77563ms, avg dur=146779ms |
| ATE (NULL upstream) | 4 (avg dur=37164ms, max=141293ms) |
| p50 latency | 3112ms |
| p95 latency | 118788ms |

### 24h errors
- `all_tiers_exhausted`: 25 (100% server-side NVCF, non-config fixable)

### Per-model breakdown
| Model | cnt | OK | avg TTFB | max dur |
|-------|-----|----|----------|---------|
| glm5_2_nv | 59 | 56 | 5341ms | 65265ms |
| dsv4p_nv | 10 | 9 | 78930ms | 494127ms |
| kimi_nv | 4 | 4 | 8902ms | 29294ms |

### Per-key (glm5_2_nv only)
| Key | cnt | OK | avg ms | p50 ms |
|-----|-----|----|--------|--------|
| K1 | 11 | 11 | 2844 | 2602 |
| K2 | 11 | 11 | 4881 | 3112 |
| K3 | 11 | 11 | 3801 | 2558 |
| K4 | 11 | 11 | 5540 | 4815 |
| K5 | 12 | 12 | 10002 | 3313 |

## Optimization

**Parameter**: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` 45→44 (−1s)

**Rationale**:
- R656-R672 trajectory: 61→59→58→57→56→55→54→53→52→51→50→49→48→47→46→45→44 (−17s total)
- Zero-error regime sustained: 0 log errors, 0 kc429
- All 4 failures are server-side `all_tiers_exhausted` — non-config fixable, unrelated to timeout
- integrate 11/10 OK, pexec 62/59 OK — streaming paths unaffected
- Margin: 44s >> UPSTREAM_TIMEOUT=25s (19s safe margin)
- Conservative: −1s per round, multi-round accumulation

**Verification**:
- Compose line 492: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "44"` ✅
- Docker compose config: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "44"` ✅
- Container env: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=44` ✅
- 3-way consistency confirmed ✅

## Iron Rule Compliance
- ✅ Single parameter per round
- ✅ Only changed HM1, never HM2

## ⏳ 轮到HM1优化HM2
