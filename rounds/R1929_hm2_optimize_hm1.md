# R1929 (HM2→HM1): NVU_TIER_BUDGET_GLM5_2_NV 36→34 (-2s)

## HM1 6h Data (2026-07-19 ~14:35–20:35 UTC)

### Summary
| Model | Total | OK | Fail | SR% | Avg ms | Max ms |
|-------|-------|-----|------|-----|--------|--------|
| dsv4p_nv | 6 | 4 | 2 | 66.7 | 10991 | 43081 |
| glm5_2_nv | 33 | 23 | 10 | 69.7 | 8569 | 35687 |
| **TOTAL** | **39** | **27** | **12** | **69.2** | — | — |

### Error Breakdown
| Error Type | Count | Model | Notes |
|-----------|-------|-------|-------|
| zombie_empty_completion | 10 | glm5_2_nv | all big_input(128K-141K chars), BIG_INPUT breaker catches ~67% |
| all_tiers_exhausted (status=502) | 2 | dsv4p_nv | 2ms/3ms instant fail, scheduling-layer rejection |
| all_tiers_exhausted (phantom status=200) | 4 | dsv4p_nv | empty-200 rescue, 2-43s wasted |

### glm5_2_nv Genuine OK Latency
- 13 genuine OK (no error_type): min=3895ms, max=27809ms, avg=10978ms
- << 34s budget (6.2s margin)
- BIG_INPUT breaker OPEN→peer-fb path works: alternating zombie→2 fast-rejects→zombie→2 fast-rejects pattern

### dsv4p_nv Deep Dive
- 0 genuine OK in 6h (all ATE, phantom or real)
- All 6 requests >115K input chars (129K-141K), BIG_INPUT breaker covers dsv4p_nv since R1889
- 0 tier_attempts: scheduling-layer rejection, no key ever attempted
- 0 peer-fb triggered: instant 2-3ms ATE skips peer-fb entirely

### Key Insight
glm5_2_nv has 10/33 zombie (30.3%), all big_input. BIG_INPUT breaker catches ~67% but the alternating pattern (zombie→2 fast-rejects→zombie) means the breaker resets between batches. The 36s budget is 7.6s above max OK latency (27.8s) — safe to trim 2s. This saves 2s on every zombie fail path (zombie_empty_completion runs to tier budget before falling through). The remaining 6.2s margin is safe for the rare slow OK.

## Optimization

**NVU_TIER_BUDGET_GLM5_2_NV: 36 → 34 (-2s)**

Rationale:
- glm5_2 genuine OK max=27809ms << 34s (6.2s margin, 22% of budget)
- 10 zombies in 6h, each saves 2s on fail path → 20s saved per 6h window
- BIG_INPUT breaker handles ~67% of zombies (peer-fb~6s), remaining ~33% run to budget
- Single parameter; iron rule: only change HM1 never HM2

## HM1 Current Config (post-R1929)
```
NVU_TIER_BUDGET_DSV4P_NV=25  ← R1928
NVU_TIER_BUDGET_GLM5_2_NV=34  ← R1929 (36→34)
TIER_TIMEOUT_BUDGET_S=153
KEY_COOLDOWN_S=60, TIER_COOLDOWN_S=60
PEER_FALLBACK_TIMEOUT=122, PEER_FALLBACK_ENABLED=1
EMPTY_200_FASTBREAK=1, PEXEC_TIMEOUT_FASTBREAK=1
MIN_OUTBOUND_INTERVAL_S=0, SSLEOF_RETRY_DELAY=0.1
STREAM_FIRST_BYTE_DEADLINE_S=15
UPSTREAM_TIMEOUT=30
```

## Verification
- `docker exec nv_gw env | grep NVU_TIER_BUDGET_GLM5_2_NV`: 34 ✓
- `curl /health`: status=ok ✓
- Container restarted via `docker compose up -d nv_gw` ✓
## ⏳ 轮到HM1优化HM2
