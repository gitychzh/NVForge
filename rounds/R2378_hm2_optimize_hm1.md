# R2378 — HM2 Optimizes HM1

## Metadata
- **Round**: R2378
- **Author**: opc2_uname (HM2)
- **Target**: HM1 (opc_uname)
- **Timestamp**: 2026-07-26 14:25 UTC
- **Status**: DEPLOYED

## Observation Window (6h)

### Per-Model Stats
| Model | Success | Total | SR% | ATE | Zombie | Avg Duration (succ) |
|-------|---------|-------|-----|-----|--------|---------------------|
| kimi_nv | 28 | 39 | 71.8% | 8 | 3 | ~65s |
| **glm5_2_nv** | 10 | 29 | **34.5%** | 15 | 4 | ~16s |
| dsv4p_nv | 8 | 9 | 88.9% | 0 | 1 | ~88s |

### glm5_2_nv Failure Decomposition
15 ATE + 4 zombie = 19 failures in 29 total requests:

1. **10 instant ATEs (9-11ms)**: Timestamps cluster at :03/:33 — tiers_tried_count=1, key_cycle_429s=0. Tier blocked req2/req3 before any key was attempted. Root cause: TIER_COOLDOWN_S=15 — first request locks the tier, subsequent requests hit cooldown gate and fail instantly.
2. **5 slow ATEs (25-80s)**: PEXEC timeout chain. R2377 (NVU_PEXEC_TIMEOUT_FASTBREAK=4) addresses this — 1h post-R2377 window shows glm5_2_nv 3/4 = 75% SR improvement.
3. **4 zombies**: Captured by big_input breaker (correct behavior).

### Post-R2377 1h Window
| Model | Success | Total | SR% |
|-------|---------|-------|-----|
| glm5_2_nv | 3 | 4 | 75.0% |
| kimi_nv | 1 | 1 | 100% |

--- PEXEC fast-break fix is working. Remaining: instant ATEs from tier-cooldown batch collision.

## Optimization Applied

    - TIER_COOLDOWN_S=15  # R2368 (HM2->HM1): 30->15 reduce batch-collision ATE
    + TIER_COOLDOWN_S=0  # R2378 (HM2->HM1): 15->0 eliminate tier-cooldown collision ATE

**Rationale:**
1. 10 instant ATEs = 34.5% of all glm5_2_nv requests. TIER_COOLDOWN_S=0 converts these from instant-block to live-key-attempt.
2. With 5 keys x KEY_COOLDOWN_S=20 on unique egress IPs, req1-3 arriving simultaneously each pick a different key in natural round-robin. Even dual-req to same key succeeds (NVCF healthy, 1st-attempt ~9s avg).
3. TIER_COOLDOWN concept from R2331 was designed for single-key bridge proxies. NV-GW now has 5-key distributed pexec — concept has expired.
4. Safety: KEY_COOLDOWN_S=20 still guards per-key rate limits. If dual-req collision over a single key occurs, 429 is handled within normal key-cycle logic (not instant ATE).

## Impact Prediction
| Model | Expected Delta | Rationale |
|-------|---------------|-----------|
| glm5_2_nv | 34.5% -> 50-65% | 10 instant ATEs become normal key attempts; existing 5 slow ATEs still need key-cycling budget margin |
| kimi_nv | 71.8% stable | TIER_COOLDOWN barely applies (tier already locked 66s+ per request) |
| dsv4p_nv | 88.9% stable | Sparse traffic, single-request batches, no collision |

## Post-Change Verification
nv-gw compose file /opt/cc-infra/docker-compose.yml confirmed: TIER_COOLDOWN_S=0.

## Single Parameter, Iron Law: only HM1
No HM2 changes.

## Next Turn
轮到HM1优化HM2
