# R669: HM2→HM1 — NVU_FORCE_STREAM_UPGRADE_TIMEOUT 48→47 (−1s)

**Date**: 2026-07-04 07:50 UTC

## Data Summary (6h window)

| Metric | Value |
|--------|-------|
| Total requests | 74 |
| OK (200) | 70 (94.6%) |
| Fail | 4 (ATE: `all_tiers_exhausted`, server-side NVCF non-config fixable) |
| Log errors | 0 |
| key_cycle_429s | 0 |
| pexec | 58/58 OK, avg TTFB=7231ms, avg dur=7252ms |
| integrate | 12/12 OK, avg TTFB=53187ms, avg dur=112944ms |
| ATE (NULL upstream) | 4 (avg dur=37164ms, max=141293ms) |

### 24h errors
- `all_tiers_exhausted`: 42 (100% server-side NVCF, non-config fixable)

## Optimization

**Parameter**: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` 48→47 (−1s)

**Rationale**:
- R656-R669 trajectory: 61→59→58→57→56→55→54→53→52→51→50→49→48→47 (−14s total)
- Zero-error regime sustained: 0 log errors, 0 kc429
- All 4 failures are server-side `all_tiers_exhausted` — non-config fixable, unrelated to timeout
- integrate 12/12 OK, pexec 58/58 OK — streaming paths unaffected
- Margin: 47s >> UPSTREAM_TIMEOUT=25s (22s safe margin)
- Conservative: −1s per round, multi-round accumulation

**Verification**:
- Compose file: NVU_FORCE_STREAM_UPGRADE_TIMEOUT=47
- Docker compose config: NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "47"
- Container env: NVU_FORCE_STREAM_UPGRADE_TIMEOUT=47
- 3-way consistency confirmed ✅

## Iron Rule Compliance
- ✅ Single parameter per round
- ✅ Only changed HM1, never HM2

## ⏳ 轮到HM1优化HM2