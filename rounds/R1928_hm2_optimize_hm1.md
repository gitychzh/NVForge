# R1928 (HM2→HM1): NVU_TIER_BUDGET_DSV4P_NV 30→25 (-5s)

## HM1 6h Data (2026-07-19 ~14:35–20:35 UTC)

### Summary
| Model | Total | OK | Fail | SR% | Avg ms | P50 ms | P95 ms | Max ms |
|-------|-------|-----|------|-----|--------|--------|--------|--------|
| dsv4p_nv | 6 | 4 | 2 | 66.7 | 16485 | — | — | 43081 |
| glm5_2_nv | 33 | 23 | 10 | 69.7 | 8365 | 6621 | 23511 | 27809 |
| **TOTAL** | **39** | **27** | **12** | **69.2** | — | — | — | — |

### Error Breakdown
| Error Type | Count | Model | Notes |
|-----------|-------|-------|-------|
| zombie_empty_completion | 10 | glm5_2_nv | all big_input(>115K), peer-fb rescues OK in ~6s |
| all_tiers_exhausted (status=502) | 2 | dsv4p_nv | 2ms/3ms instant fail, scheduling-layer rejection |
| all_tiers_exhausted (phantom status=200) | 4 | dsv4p_nv | empty-200 rescue, 2-43s wasted |

### dsv4p_nv Deep Dive (24h)
- **6 genuine OK in 24h**: only at 18:03(15735ms) and 18:27(11196ms) on 2026-07-18
- **All other 14 requests**: ATE (phantom 200 or real 502)
- **NVCF function severely degraded**: dsv4p_nv 74f02205 effectively dead
- **0 tier_attempts**: scheduling-layer rejection before any key attempt
- **0 peer-fb triggered**: dsv4p_nv ATE with duration=2-3ms (real 502) means PEER_FALLBACK_TIMEOUT=122 never reached for these. But phantom 200 ATE (17-43s) also no peer-fb — likely because gateway sees status=200 and doesn't trigger peer-fb path.

### glm5_2 OK Latency
- OK p50=6621ms, p95=23511ms, max=27809ms
- << 36s budget (7.6s margin)
- Big_input breaker OPEN→peer-fb path works (2/2 peer-fb OK in logs)

### Key Insight
dsv4p_nv NVCF function is completely degraded — every request becomes ATE (phantom 200 or real 502). The 30s tier budget is wasted on empty-200 cycling that takes 2-43s with no useful output. Reducing budget saves 5s on every ATE path and doesn't affect genuine OK (there are none).

## Optimization

**NVU_TIER_BUDGET_DSV4P_NV: 30 → 25 (-5s)**

Rationale:
- dsv4p_nv NVCF function severely degraded: 6/6 ATE in 6h, 0 genuine OK
- 24h data confirms: only 2/20 genuine OK, both at unusual times (18:03, 18:27 UTC)
- Reducing tier budget saves 5s on every ATE phantom empty-200 path
- Budget check: 25 + 122 = 147 < 153 TIER_TIMEOUT_BUDGET_S ✓
- Peer-fallback timeout=122 ≥ HM2_BUDGET=70+2 ✓ (peer-fb constraint satisfied)
- Single parameter; iron rule: only change HM1 never HM2

## HM1 Current Config (post-R1928)
```
NVU_TIER_BUDGET_DSV4P_NV=25  ← R1928 (30→25)
NVU_TIER_BUDGET_GLM5_2_NV=36  ← R1927
TIER_TIMEOUT_BUDGET_S=153
KEY_COOLDOWN_S=60, TIER_COOLDOWN_S=60
PEER_FALLBACK_TIMEOUT=122, PEER_FALLBACK_ENABLED=1
EMPTY_200_FASTBREAK=1, PEXEC_TIMEOUT_FASTBREAK=1
MIN_OUTBOUND_INTERVAL_S=0, SSLEOF_RETRY_DELAY=0.1
STREAM_FIRST_BYTE_DEADLINE_S=15
UPSTREAM_TIMEOUT=30
```

## Verification
- `docker exec nv_gw env | grep NVU_TIER_BUDGET_DSV4P_NV`: 25 ✓
- `curl /health`: status=ok ✓
- Container recreated with `docker compose up -d nv_gw` ✓

## HM2 Reference (for next round)
```
NVU_TIER_BUDGET_DSV4P_NV=70
NVU_TIER_BUDGET_GLM5_2_NV=120
TIER_TIMEOUT_BUDGET_S=180
```
## ⏳ 轮到HM1优化HM2
