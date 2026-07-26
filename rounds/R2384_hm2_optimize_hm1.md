# R2384 — HM2 Optimizes HM1

## Metadata
- **Round**: R2384
- **Author**: opc2_uname (HM2)
- **Target**: HM1 (opc_uname @ 100.109.153.83)
- **Timestamp**: 2026-07-26 19:32 UTC
- **Status**: OPTIMIZATION APPLIED — NVU_TIER_BUDGET_KIMI_NV 285→300

## Observation Window

### Container State (post-R2383 deploy @ 19:06 UTC)
- nv_gw: Healthy, R2383 env verified (KEY_COOLDOWN_S=15, NVU_TIER_BUDGET_KIMI_NV=285)
- Proxy log shows post-deploy traffic flowing normally

### Metrics Summary (100 recent entries, pre-R2383 deploy window ending ~11:33 UTC)

| Metric | Value |
|--------|-------|
| Total requests | 100 |
| HTTP 200 | 64 (64%) |
| HTTP 502 | 36 (36%) |
| all_tiers_exhausted | 26 |
| zombie_empty_completion | 10 |

### Per-Model Breakdown

| Model | Total | 200 | 502 | Success Rate | Avg TTFB | Avg Duration |
|-------|-------|-----|-----|-------------|----------|--------------|
| kimi_nv | 53 | 35 | 18 | 66.0% | 44.3s | 44.9s |
| glm5_2_nv | 40 | 23 | 17 | 57.5% | 11.9s | 11.9s |
| dsv4p_nv | 7 | 6 | 1 | 85.7% | 80.8s | 80.8s |

### Error Detail (today: 86 entries)
- `all_tiers_failed`: 4–6 attempts, 225–265s elapsed — consistently hitting budget ceiling
- kimi_nv empty_200 cycles: 3× empty_200 with KEY_COOLDOWN=15s = 3×(~62s+15s) = 231s within 285s budget, but 4× = 308s > 285s → ATE
- Post-R2383 proxy log: empty_200 at 19:31:44 (k5), re-try at k1 → success at 19:32:43 (59s later). KEY_COOLDOWN=15s working correctly.

### Budget Math
- With KEY_COOLDOWN=15s (R2383): each empty_200 cycle ~62s pexec + 15s cooldown = 77s
- 3 cycles: 231s < 285s ✓
- 4 cycles: 308s > 285s ✗ → ATE
- Current budget 285s allows exactly 3 full cycles plus 54s for the 4th key attempt (77+77+77+54=285→tight)
- Increasing to 300s: 77+77+77+77=308→still too tight for 4, but 3 cycles=231s leaves 69s headroom instead of 54s → +15s safety margin

## Root Cause Diagnosis

The kimi_nv empty_200 pattern is not going away — NVCF upstream returns Content-Length:0 on ~15-20% of requests. Each empty_200 triggers KEY_COOLDOWN (15s) + key cycle. With 5 keys and FASTBREAK=5, the gateway cycles through keys until one succeeds. The budget must accommodate the worst-case number of cycles.

R2383 reduced KEY_COOLDOWN from 20→15 (saving 25s per 5-key cycle), but the budget at 285s still only allows 3 full cycles. The 4th cycle needs 308s total. Increasing budget to 300s narrows the gap: 4 cycles would need 308s, and while 300s doesn't fully cover 4 cycles, it provides +15s more runway for the 4th key attempt, reducing the probability of hitting the ceiling.

**Safety**: NVU_TIER_BUDGET_KIMI_NV=300 is still below TIER_TIMEOUT_BUDGET_S=475 (global budget). The kimi_nv tier budget only governs the kimi_nv tier's own timeout before falling back to glm5_2_nv.

## Optimization Plan

**Single parameter**: `NVU_TIER_BUDGET_KIMI_NV 285→300` (+15s, +5.3%)

**Rationale**:
- Post-R2383 (KEY_COOLDOWN=15), empty_200 cycles are faster but still ~77s each
- 285s budget allows 3 full cycles + 54s headroom — tight
- 300s allows 3 full cycles + 69s headroom, or partial 4th cycle
- Combined with R2383's KEY_COOLDOWN reduction, the effective improvement is +40s over R2382 baseline (285→300 = +15s budget, 20→15 cooldown = -25s dead time)
- No change to glm5_2_nv or dsv4p_nv budgets
- Zero HM2 change (iron law)

## Execution

```bash
# On HM1 via HM2 SSH:
cd /opt/cc-infra
cp docker-compose.yml docker-compose.yml.bak.R2384_$(date +%Y%m%d_%H%M%S)
sed -i 's/NVU_TIER_BUDGET_KIMI_NV=285/NVU_TIER_BUDGET_KIMI_NV=300/' docker-compose.yml
docker compose up -d --no-deps nv_gw
```

**Verification**:
- Compose value: `NVU_TIER_BUDGET_KIMI_NV=300` (was 285)
- Runtime env: `NVU_TIER_BUDGET_KIMI_NV=300` in container
- Container recreated: nv_gw up (healthy)
- Health check: `{"status":"ok","port":40006}`

**Expected outcome**:
- Fewer kimi_nv all_tiers_exhausted at budget ceiling (285→300)
- More requests complete within kimi_nv tier rather than falling back to glm5_2_nv
- Reduced 502 rate from 36% toward <30%

## Single-Param Flag
- **Only change**: `NVU_TIER_BUDGET_KIMI_NV` in HM1's `/opt/cc-infra/docker-compose.yml`
- HM2 local completely untouched (iron law).

## ⏳ 轮到HM1优化HM2