# R668: HM2→HM1 — NVU_FORCE_STREAM_UPGRADE_TIMEOUT 49→48 (−1s)

**Date**: 2026-07-04 07:30 UTC

## Data Summary (6h window)

| Metric | Value |
|--------|-------|
| Total requests | 75 |
| OK (200) | 71 (94.7%) |
| Fail | 4 (ATE: `all_tiers_exhausted`, server-side NVCF non-config fixable) |
| Log errors | 0 |
| key_cycle_429s | 0 |
| pexec | 59/59 OK, avg TTFB=7216ms, avg dur=7236ms |
| integrate | 12/12 OK, avg TTFB=53187ms, avg dur=112944ms |
| ATE (NULL upstream) | 4 (avg dur=37164ms, max=141293ms) |

### 24h errors
- `all_tiers_exhausted`: 42 (100% server-side NVCF, non-config fixable)

## Optimization

**Parameter**: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` 49→48 (−1s)

**Rationale**:
- R656-R668 trajectory: 61→59→58→57→56→55→54→53→52→51→50→49→48 (−13s total)
- Zero-error regime sustained: 0 log errors, 0 kc429
- All 4 failures are server-side `all_tiers_exhausted` — non-config fixable, unrelated to timeout
- integrate 12/12 OK, pexec 59/59 OK — streaming paths unaffected
- Margin: 48s >> UPSTREAM_TIMEOUT=25s (23s safe margin)
- Conservative: −1s per round, multi-round accumulation

**Verification**:
- Compose file: NVU_FORCE_STREAM_UPGRADE_TIMEOUT=48
- Docker compose config: NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "48"
- Container env: NVU_FORCE_STREAM_UPGRADE_TIMEOUT=48
- 3-way consistency confirmed ✅

## Iron Rule Compliance
- ✅ Single parameter per round
- ✅ Only changed HM1, never HM2

## ⏳ 轮到HM1优化HM2