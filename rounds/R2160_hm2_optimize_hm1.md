# R2160 (HM2→HM1): NVU_TIER_BUDGET_GLM5_2_NV 25→28 (+3s)

**Role**: HM2优化HM1  
**Date**: 2026-07-21  
**Commit**: e127e6d (HM1 R2159: TIER_COOLDOWN_S 32→30)

## Pre-Optimization Data

### 6h Window (2026-07-21 07:03 – 13:03 UTC)
| Metric | Value |
|---|---|
| Total Requests | 37 |
| Successful (200) | 31 |
| Failed | 6 |
| Success Rate | 83.8% |
| dsv4p ATE (all_tiers_exhausted) | 3 (502) |
| glm5_2 zombie (empty_completion) | 3 (502) |

### Per-Model Latency (glm5_2 success only, 31 req)
| Stat | Value |
|---|---|
| avg_ms | 18,718 |
| min_ms | 2,946 |
| max_ms | 153,777 |

### glm5_2 Tier Attempts (54 total)
| Error Type | Count | % |
|---|---|---|
| pexec_success | 34 | 63.0% |
| pexec_timeout | 9 | 16.7% |
| pexec_429 | 6 | 11.1% |
| pexec_SSLEOFError | 5 | 9.3% |

### 429 Key Cycling (glm5_2 only)
| key_cycle_429s | Count |
|---|---|
| 1 | 26 |
| 2 | 2 |
| 3 | 3 |
| 4 | 2 |
| 7 | 1 |

### ATE Detail — Root Cause
All 3 dsv4p ATE show `tiers_tried_count=1, fallback_tiers_used={dsv4p_nv}` — the glm5_2_nv fallback tier is **silently skipped**. Budget was 25, marginally above UPSTREAM=24. Per R2112 discovery, budget must be `≥ UPSTREAM + 1` for the tier to attempt even one key. At 25=24+1, the margin is too tight — the gateway's budget check pre-empts the tier.

### Container Logs (tail 100, error/warn)
- glm5_2: 429 cycling on keys k3,k4,k5,k1 (6× 429, all cooling)
- glm5_2: 1× SSLEOFError on k1
- glm5_2: KEY-SKIP on k4,k5 (cooling/auth-failed)
- No NV-PEER-FB firing (peer-fb budget check: 24+122=146 < 153 ✓, but ATE on dsv4p means peer-fb isn't triggered for dsv4p ATE since the tier is skipped, not failing)

### Live Env (HM1 nv_gw)
```
NVU_TIER_BUDGET_GLM5_2_NV=25
TIER_TIMEOUT_BUDGET_S=153
KEY_COOLDOWN_S=48
TIER_COOLDOWN_S=30
UPSTREAM_TIMEOUT=24
NVU_TIER_BUDGET_DSV4P_NV=48
PEER_FALLBACK_TIMEOUT=122
```

## Optimization

**Change**: `NVU_TIER_BUDGET_GLM5_2_NV: 25 → 28` (+3s)

**Rationale**: glm5_2 budget=25 is only UPSTREAM+1 (=25), creating a marginal condition where the gateway's budget check pre-empts the tier before even one key attempt. Increasing to 28 (UPSTREAM+4) provides a high-confidence margin for the fallback tier to trigger. This enables dsv4p→glm5_2 fallback, giving a rescue path for the 3 ATE cases.

**Budget check**:
- KEY+TIER+GLM5_2 = 48 + 30 + 28 = 106 < 153 (TIER_TIMEOUT_BUDGET_S) ✓
- Peer-fb: UPSTREAM(24) + PEER_FALLBACK(122) = 146 < 153 ✓
- glm5_2 tier: 28 > UPSTREAM(24) with 4s margin ✓

**Verification**:
```
docker exec 7b9d0e53dd3a_nv_gw env | grep NVU_TIER_BUDGET_GLM5_2_NV
→ NVU_TIER_BUDGET_GLM5_2_NV=28
```

## Expected Impact
- dsv4p ATE reduced from 3 to ~0-1 (glm5_2 fallback rescue)
- glm5_2 zombie unchanged (budget increase doesn't affect zombie root cause: NVCF empty-200)
- glm5_2 429 rate may slightly decrease (more budget = more key cycling before timeout)
- SR expected: 83.8% → ~88-92%

## ⏳ 轮到HM1优化HM2