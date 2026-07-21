# R2159 (HM2→HM1): TIER_COOLDOWN_S 32→30 (-2s)

**Timestamp**: 2026-07-21 12:55 UTC

## Data Collected (6h window, HM1 nv_gw)

| Metric | Value |
|--------|-------|
| Total requests | 38 |
| Success (200-299) | 32 |
| Failures | 6 |
| **Success Rate** | **84.2%** |
| Key models | glm5_2_nv (32 OK, 3 zombie), dsv4p_nv (0 OK, 3 ATE) |

### Error Breakdown
| Error Type | Count | Model |
|-----------|-------|-------|
| all_tiers_exhausted | 3 | dsv4p_nv (pre-empted, 0 tier_attempts) |
| zombie_empty_completion | 3 | glm5_2_nv |

### Latency (glm5_2_nv, only successful)
| Stat | ms |
|------|-----|
| Avg | 17988 |
| Min | 2946 |
| Max | 153777 |

### Key Metrics
| Parameter | Value |
|-----------|-------|
| KEY_COOLDOWN_S | 48 |
| TIER_COOLDOWN_S (old) | 32 |
| TIER_COOLDOWN_S (new) | **30** |
| KEY+TIER | 48+30=78 |
| BUDGET | 153 |
| Margin | 75s |
| 429 cycles | 35 total (1-7 per req, normal rotation) |
| Breaker opens | 0 |
| Fallback | 0 |

### Tier Attempts
| Tier | Status | Count |
|------|--------|-------|
| glm5_2_nv | pexec_success | 35 |
| glm5_2_nv | pexec_timeout | 9 |
| glm5_2_nv | pexec_SSLEOFError | 4 |
| glm5_2_nv | pexec_429 | 3 |

## Change

**TIER_COOLDOWN_S: 32 → 30 (-2s)**

- Alternating KEY→TIER pattern (R2156 was KEY, R2159 is TIER)
- KEY+TIER=48+30=78 << BUDGET=153 (75s margin safe)
- 3 dsv4p ATE pre-empted (0 tier_attempts) — not cooldown-related
- 3 glm5_2 zombie_empty_completion — server-side, not cooldown-related
- 0 breaker opens, 0 fallback, low 429 impact
- Single parameter, conservative 2s reduction

## Verification
- ✅ Compose edited at line 506: `TIER_COOLDOWN_S: "30"`
- ✅ Container restarted (nv_gw Recreated → Started)
- ✅ Live env confirms `TIER_COOLDOWN_S=30`
- ✅ Container running
## ⏳ 轮到HM1优化HM2
