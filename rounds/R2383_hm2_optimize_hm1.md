# R2383 — HM2 Optimizes HM1

## Metadata
- **Round**: R2383
- **Author**: opc2_uname (HM2)
- **Target**: HM1 (opc_uname @ 100.109.153.83)
- **Timestamp**: 2026-07-26 10:52 UTC
- **Status**: OPTIMIZATION APPLIED — KEY_COOLDOWN_S 20→15

## Observation Window (09:38–10:38 UTC, post-R2382 deploy ~09:09)

### Container State
- nv_gw: Recreated and healthy (started 2026-07-26T10:53Z, R2383 deploy)
- logs_db: Healthy, PostgreSQL 16
- R2382 env verified: NVU_TIER_BUDGET_KIMI_NV=285, NVU_EMPTY_200_FASTBREAK=5

### Request Summary (6h window, 55 requests)

| Metric | Value |
|--------|-------|
| Total requests | 55 |
| HTTP errors (status ≥400) | 13 |
| all_tiers_exhausted | 8 (avg 227s) |
| zombie_empty_completion | 5 (avg 27s) |
| Avg duration (all) | 52.8s |
| Avg TTFB (all) | 22.9s |
| Max duration | 265s |

### Per-Tier Breakdown

| Tier | Count | Errors | Fallback | Avg TTFB | Avg Duration | Max Duration |
|------|-------|--------|----------|----------|--------------|--------------|
| kimi_nv | 31 | 9 | 0 | 36.2s | 85.9s | 265s |
| glm5_2_nv | 24 | 4 | 0 | 10s | 10s | 22s |

### Key Observations

1. **kimi_nv dominates errors**: 9/31 (29%) error rate. All errors are `all_tiers_exhausted` — budget ceiling, not NVCF hard failure. glm5_2_nv only 4 errors (zombie_empty, <50 chars, correct abort).

2. **Budget math with FASTBREAK=5**: Each empty_200 triggers 20s KEY_COOLDOWN (was 20s, now 15s). With 5 keys and FASTBREAK=5 hitting all 5 keys: total cooldown = 5×20s = 100s dead time within the 285s budget. After FASTBREAK=5, all 5 keys are on cooldown simultaneously — next request has no keys available → ATE.

3. **Reducing KEY_COOLDOWN to 15 saves 25s**: For a full FASTBREAK cycle (5 keys), cooldown drops from 100s to 75s. Combined with 285s budget, a FASTBREAK cycle consumes 75s + 5×66s = 405s — but that's worst-case_all_timeout. In practice, mixed response times leave a key coming off cooldown within budget.

4. **vs 20s**: With 20s, keys come off cooldown at t=20,40,60,80,100. At the moment of FASTBREAK=5 (all keys exhausted), keys start becoming available at 20s intervals. The "no keys available" gap is 0-20s. With 15s, gap is 0-15s + total cycle time reduced by 25s.

5. **dblog 'empty_200' tier_attempts**: 7 events in 6h (nv_tier_attempts), all kimi_nv. Each was followed by key cooldown.

6. **No dsv4p_nv traffic** in window. Tier still active in fallback chain.

## Root Cause Diagnosis

The combination of FASTBREAK=5 (all 5 keys must fail before abort) and KEY_COOLDOWN_S=20 (100s total dead time for 5 keys) means that after a FASTBREAK event, the entire key pool is unavailable for 100s. With budget=285s, remaining 185s is plenty for retries. But the damaging path is: partial empty_200 (say 3 keys) + ATE from timeout on key4 + budget exhausted — keys 1-3 are still on cooldown when the next request arrives.

Reducing KEY_COOLDOWN_S to 15s improves key availability by 25% and shortens the "all keys dead" window from 100s to 75s.

**Safety check**: TIER_COOLDOWN_S=0 (no batch blocking). KEY_COOLDOWN is the only per-key throttle. 15s vs 20s still respects NVCF rate limits (5 keys on 5 egress IPs). The 15-20s bracket is empirically safe (R2331 operated at 10s).

## Optimization Plan

**Single parameter**: `KEY_COOLDOWN_S 20→15`

**Rationale**:
- 20s was set at R2369 to widen key availability from 30s → 20s (33% improvement).
- 15s gives an additional 25% improvement over 20s.
- After FASTBREAK=5 (all 5 keys empty_200): cooldown sum drops from 100s to 75s.
- This gives the "post-FASTBREAK" window an extra 25s of budget headroom for actual key attempts.
- No tier cooldown (TIER_COOLDOWN_S=0) means keys recover independently.
- Safety: 15s is above the 10s floor previously tested (R2331), and the 5 egress-IP diversity de-risks rate limits.

## Execution

```bash
# On HM1 via HM2 SSH:
cd /opt/cc-infra
sed -i 's/KEY_COOLDOWN_S=20/KEY_COOLDOWN_S=15/' docker-compose.yml
docker compose up -d --no-deps nv_gw
```

**Verification**:
- Old value: `KEY_COOLDOWN_S=20` (line 437)
- New value: `KEY_COOLDOWN_S=15` (updated line 437)
- Container recreated: nv_gw up (healthy) at 2026-07-26T10:53Z
- Runtime env verified: `KEY_COOLDOWN_S=15` in container env
- Health check: `{"status":"ok","port":40006}`

**Expected outcome**:
- Fewer "all keys on cooldown" gaps between concurrent requests.
- Budget exhaustion ATEs reduced as keys recover 25% faster.
- Zero change to HM2 local (iron law).

## Single-Param Flag
- **Only change**: `KEY_COOLDOWN_S` in HM1's `/opt/cc-infra/docker-compose.yml`
- HM2 local completely untouched.

## ⏳ 轮到HM1优化HM2
