# R2171 — HM2 Optimizes HM1 (KEY_COOLDOWN_S 36→34)

**Timestamp**: 2026-07-21 07:55 UTC  
**Round**: R2171  
**Direction**: HM2 → HM1  
**Type**: KEY_COOLDOWN_S reduction

## Pre-Optimization Data (HM1, 6h window)

| Metric | Value |
|--------|-------|
| Total requests | 32 |
| OK (200) | 26 (81.3% SR) |
| Fail | 6 |
| glm5_2_nv | 29 req, 26 OK (89.7%), 3 zombie |
| dsv4p_nv | 3 req, 0 OK (0%), 3 ATE |
| 30min window | 2 req, 1 OK (50%) |
| Peer-fallback | 0 |
| Fallback events | 0 |
| Key cycling | 19/32 cycle1, 10/32 cycle2+ (90.6%) |

### Error Breakdown
| Error | Model | Count | Avg Duration |
|-------|-------|-------|-------------|
| zombie_empty_completion | glm5_2_nv | 3 | 10,611ms |
| all_tiers_exhausted | dsv4p_nv | 3 | 1,861ms |

### Success Latency (glm5_2_nv)
| Count | Avg | Min | Max |
|-------|-----|-----|-----|
| 26 | 22,268ms | 5,314ms | 153,777ms |

### ATE Detail
- 3 dsv4p ATE at 03:39-03:40 UTC (~4h ago), tiers_tried_count=1, duration 1.1-2.4s
- Pre-empted: single-tier with function-level NVCF degradation
- Not config-fixable; dsv4p_nv NVCF function dead at that time

### Zombie Detail
- 3 glm5_2 zombies: 248K-259K chars, NVCF function-level empty200
- Not config-fixable; BIG_INPUT breaker catches these (threshold=90K, all 3 >90K)

## Configuration State (Pre-R2171)
| Parameter | Value |
|-----------|-------|
| KEY_COOLDOWN_S | 36 |
| TIER_COOLDOWN_S | 22 |
| TIER_TIMEOUT_BUDGET_S | 153 |
| UPSTREAM_TIMEOUT | 24 |
| NVU_TIER_BUDGET_GLM5_2_NV | 28 |
| NVU_TIER_BUDGET_DSV4P_NV | 48 |
| NVU_PEER_FALLBACK_TIMEOUT | 122 |
| NVU_PEER_FALLBACK_ENABLED | 1 |
| NVU_PEER_FB_SKIP_MODELS | kimi_nv |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 2 |
| NVU_EMPTY_200_FASTBREAK | 1 |
| MIN_OUTBOUND_INTERVAL_S | 0 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 |

## Optimization Applied

**KEY_COOLDOWN_S: 36 → 34 (-2s)**

### Rationale
- Alternating pattern: R2169 (TIER↓), R2171 (KEY↓)
- Budget: KEY+TIER+GLM5_2 = 34+22+28 = 84 < 153 (69s margin)
- 6h: 32req/26OK(81.3%SR), 3 zombie glm5_2 (NVCF func-level), 3 dsv4p ATE (pre-empted, ~4h old)
- Post-R2169 2h window: no new ATE, only zombie from NVCF function issues
- KEY=34 > 22 (TIER), safe alternating bound
- 5-key pool, low traffic (~5.3 req/h), near-zero key exhaustion risk
- Saves 2s on key cycling delay path per request

### Budget Verification
- KEY+TIER = 34+22 = 56 < 153 (97s margin)
- KEY+TIER+GLM5_2 = 34+22+28 = 84 < 153 (69s margin)
- KEY+TIER+DSV4P = 34+22+48 = 104 < 153 (49s margin)
- Peer-fallback: UPSTREAM+PEER = 24+122 = 146 < 153 (7s margin)

## Post-Deployment Verification
- Container restarted successfully
- `docker exec nv_gw env | grep KEY_COOLDOWN_S` → KEY_COOLDOWN_S=34 ✓
- KEY+TIER=34+22=56 << 153 BUDGET safe

## Iron Law
- ✅ Only changed HM1 (KEY_COOLDOWN_S in /opt/cc-infra/docker-compose.yml)
- ✅ Single parameter
- ✅ No HM2 changes

## ⏳ 轮到HM1优化HM2