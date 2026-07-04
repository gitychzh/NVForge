# R674: HM2→HM1 — NVU_FORCE_STREAM_UPGRADE_TIMEOUT 43→42 (−1s)

**Date**: 2026-07-04 09:05 UTC

## Data Summary (6h window)

| Metric | Value |
|--------|-------|
| Total requests | 73 |
| OK (200) | 69 (94.5%) |
| Fail | 4 (ATE: `all_tiers_exhausted`, server-side NVCF non-config fixable) |
| Log errors | 0 |
| key_cycle_429s | 0 |
| pexec | 57/57 OK (100%), avg TTFB=7242ms, avg dur=7263ms, max=107733ms |
| integrate | 12/12 OK (100%), avg TTFB=53187ms, avg dur=112944ms, max=494127ms |
| ATE (NULL upstream) | 4 (max dur=141293ms) |

### 24h errors
- `all_tiers_exhausted`: 15 (100% server-side NVCF, non-config fixable)

### Per-model breakdown
| Model | cnt | OK | avg dur (ms) | max dur (ms) |
|-------|-----|----|--------------|---------------|
| glm5_2_nv | 59 | 56 | 5265 | 65265 |
| dsv4p_nv | 10 | 9 | 154931 | 494127 |
| kimi_nv | 4 | 4 | 13763 | 29294 |

### Per-key (glm5_2_nv only)
| Key | cnt | OK | avg dur (ms) |
|-----|-----|----|--------------|
| K1 (idx=0) | 12 | 12 | 2820 |
| K2 (idx=1) | 11 | 11 | 4735 |
| K3 (idx=2) | 11 | 11 | 3810 |
| K4 (idx=3) | 10 | 10 | 5545 |
| K5 (idx=4) | 12 | 12 | 10000 |

### Log observations
- 0 errors, 0 warnings, 0 panics
- Thinking injection active: log shows `extended timeout 42s`
- Container healthy, proxy listening

## Optimization

**Parameter**: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` 43→42 (−1s)

**Rationale**:
- R656-R674 trajectory continued: 61→59→58→57→56→55→54→53→52→51→50→49→48→47→46→45→44→43→42 (−19s total)
- Zero-error regime sustained: 0 log errors, 0 kc429, 0 fallback triggered
- All 4 failures are server-side `all_tiers_exhausted` — non-config fixable, unrelated to timeout
- pexec 57/57 OK (100%), integrate 12/12 OK (100%) — streaming paths unaffected
- Margin: 42s >> UPSTREAM_TIMEOUT=25s (17s safe margin, well above floor)
- Conservative: −1s per round, multi-round accumulation
- Log confirms thinking timeout extension at 42s, still safe

**Verification**:
- Compose line 492: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "42"` ✅
- Docker compose config: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "42"` ✅
- Container env: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=42` ✅
- 3-way consistency confirmed ✅
- Container restarted cleanly, proxy healthy ✅

## Iron Rule Compliance
- ✅ Single parameter per round
- ✅ Only changed HM1, never HM2

## ⏳ 轮到HM1优化HM2