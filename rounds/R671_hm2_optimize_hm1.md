# R671: HM2→HM1 — NVU_FORCE_STREAM_UPGRADE_TIMEOUT 46→45 (−1s)

**Date**: 2026-07-04 08:10 UTC

## Data Summary (6h window)

| Metric | Value |
|--------|-------|
| Total requests | 73 |
| OK (200) | 69 (94.5%) |
| Fail | 4 (ATE: `all_tiers_exhausted`, server-side NVCF non-config fixable) |
| Log errors | 0 |
| key_cycle_429s | 0 |
| pexec | 57/57 OK, avg TTFB=7269ms, avg dur=7289ms |
| integrate | 12/12 OK, avg TTFB=53187ms, avg dur=112944ms |
| ATE (NULL upstream) | 4 (avg dur=37164ms, max=141293ms) |

### 24h errors
- `all_tiers_exhausted`: 28 (100% server-side NVCF, non-config fixable)

### DB last 10 requests
| ts | model | status | ttfb_ms | dur_ms | upstream | kc429 |
|----|-------|--------|---------|--------|----------|-------|
| 08:03:20 | glm5_2_nv | 200 | 2360 | 2360 | nvcf_pexec | 0 |
| 07:33:20 | glm5_2_nv | 200 | 2507 | 2508 | nvcf_pexec | 0 |
| 07:03:20 | glm5_2_nv | 200 | 2408 | 2408 | nvcf_pexec | 0 |
| 06:33:20 | glm5_2_nv | 200 | 2406 | 2406 | nvcf_pexec | 0 |
| 06:03:20 | glm5_2_nv | 200 | 2038 | 2038 | nvcf_pexec | 0 |
| 05:33:20 | glm5_2_nv | 200 | 2430 | 2430 | nvcf_pexec | 0 |
| 05:03:23 | glm5_2_nv | 200 | 2224 | 2228 | nvcf_pexec | 0 |
| 05:03:20 | glm5_2_nv | 200 | 3040 | 3040 | nvcf_pexec | 0 |
| 04:33:23 | glm5_2_nv | 200 | 2424 | 2424 | nvcf_pexec | 0 |
| 04:33:20 | glm5_2_nv | 200 | 3122 | 3123 | nvcf_pexec | 0 |

## Optimization

**Parameter**: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` 46→45 (−1s)

**Rationale**:
- R656-R671 trajectory continued: 61→59→58→57→56→55→54→53→52→51→50→49→48→47→46→45 (−16s total)
- Zero-error regime sustained: 0 log errors, 0 kc429, 0 fallback triggered
- All 4 failures are server-side `all_tiers_exhausted` — non-config fixable, unrelated to timeout
- integrate 12/12 OK, pexec 57/57 OK — streaming paths unaffected
- Margin: 45s >> UPSTREAM_TIMEOUT=25s (20s safe margin)
- Conservative: −1s per round, multi-round accumulation
- Log confirms thinking timeout extension at 46s — still safe at 45s

**Verification**:
- Compose line 492: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "45"` ✅
- Docker compose config: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "45"` ✅
- Container env: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=45` ✅
- 3-way consistency confirmed ✅

## Iron Rule Compliance
- ✅ Single parameter per round
- ✅ Only changed HM1, never HM2

## ⏳ 轮到HM1优化HM2