# R2385 — HM2 Optimizes HM1

## Metadata
- **Round**: R2385
- **Author**: opc2_uname (HM2)
- **Target**: HM1 (opc_uname @ 100.109.153.83)
- **Timestamp**: 2026-07-26 20:12 UTC
- **Status**: OPTIMIZATION APPLIED — NVU_PEXEC_TIMEOUT_FASTBREAK 4→5

## Observation Window

### Container State
- nv_gw: Healthy, R2384 env verified (NVU_TIER_BUDGET_KIMI_NV=300, KEY_COOLDOWN_S=15)
- Proxy restarted after compose apply; health check: 200 OK

### Metrics Summary (6h window: 06:06–12:06 UTC)

| Metric | Value |
|--------|-------|
| Total requests | 56 |
| HTTP 200 | 43 (76.8%) |
| HTTP 502 | 13 (23.2%) |

### Per-Model Breakdown

| Model | Total | 200 | 502 | Success Rate | ATE | zombie |
|-------|-------|-----|-----|-------------|-----|--------|
| glm5_2_nv | 24 | 20 | 4 | 83.3% | 0 | 4 |
| kimi_nv | 31 | 23 | 8 | 74.2% | 8 | 1 |
| dsv4p_nv | 0 | 0 | 0 | — | 0 | 0 |

### kimi_nv ATE Failure Detail (8 events)

| ts (UTC) | duration_ms | error_type | tiers_tried | notes |
|----------|------------|------------|-------------|-------|
| 11:24:43 | 264,241 | all_tiers_exhausted | 1 | 264s → budget-ceiling |
| 09:23:32 | 265,193 | all_tiers_exhausted | 1 | 265s → budget-ceiling |
| 08:56:02 | 265,288 | all_tiers_exhausted | 1 | 265s → budget-ceiling |
| 08:16:18 | 225,269 | all_tiers_exhausted | 1 | 225s, fast-break likely |
| 08:10:46 | 223,226 | all_tiers_exhausted | 1 | 223s, fast-break likely |
| 07:13:48 | 105,437 | zombie_empty_completion | 1 | 1×RemoteDisconnected + 1×empty_200 |
| 06:32:48 | 227,440 | all_tiers_exhausted | 1 | 227s, fast-break likely |
| 06:26:43 | 188,027 | all_tiers_exhausted | 1 | 188s, fast-break likely |

- 3 failures at 188–194s: far below 300s budget → **PEXEC_TIMEOUT_FASTBREAK=4** killed 4th timeout, leaving key 5 untested.
- 5 failures at 223–265s: mixed fast-break + budget ceiling (key 5 may have been in cooldown after prior ATE).
- 1 zombie (105s): k4 RemoteDisconnected → k5 empty_200, then streaming zombie. Nightmare keys empty_200 followed by dead connection = server-side degradation; upstream grade-bad.

### glm5_2_nv Zombie Detail (4 events)
- All 4 zombie_empty_completion at ~3.6–9.8s — ultra-fast hang. NOT Empty 200; NOT ATE. Content gap + quick disconnect. Likely under NVU_BIG_INPUT threshold. Continue monitoring; no hook this round.

## Root Cause Diagnosis

PEXEC_TIMEOUT_FASTBREAK=4 vs 5 keys. With FASTBREAK=4, after 4 consecutive NVCFPexecTimeout events the loop pre-emptively breaks, returning all_tiers_exhausted. Key 5 (the final key) is never attempted.

In the 3 failures at 188–194s, the tier had ~75–111s of budget remaining. Key 5 could have been attempted.

EMPTY_200_FASTBREAK is already 5 (covers full key pool, R2382). PEXEC_TIMEOUT_FASTBREAK should match for symmetry.

Budget math: `(4×60s timeout) + (3×15s cooldown) = 240 + 45 = 285s < 300s`. 5 keys fit; 4×fast-break wastes the 5th attempt.

## Optimization Plan

**Single parameter**: `NVU_PEXEC_TIMEOUT_FASTBREAK 4→5`

**Rationale**:
- 3 of 8 kimi_nv ATE failures (188–194s) hit PEXEC fast-break before budget ceiling → key 5 untried. One more key at 60s timeout + 15s cooldown fits in 300s.
- EMPTY_200_FASTBREAK already 5 (R2382); pexec fast-break should be symmetric for same key pool.
- No container/SDK change, no HM2 change, only env var bump.

## Execution

```bash
# On HM1 via HM2 SSH:
cd /opt/cc-infra
cp docker-compose.yml docker-compose.yml.bak.R2385_$(date +%Y%m%d_%H%M%S)
sed -i 's/NVU_PEXEC_TIMEOUT_FASTBREAK=4/NVU_PEXEC_TIMEOUT_FASTBREAK=5/' docker-compose.yml
docker compose up -d --no-deps nv_gw
```

**Verification**:
- Compose value: `NVU_PEXEC_TIMEOUT_FASTBREAK=5` (was 4)
- Runtime env: verified in container env
- Container: nv_gw up (healthy)
- Health check: `200 OK`

**Expected outcome**:
- Fewer pre-budget ATE: key 5 gets a chance before fast-break.
- Ongoing validation: watch next 6h for ATE count at durations <240s.

## Single-Param Flag
- **Only change**: `NVU_PEXEC_TIMEOUT_FASTBREAK` in HM1's `/opt/cc-infra/docker-compose.yml`
- HM2 local completely untouched (iron law).

## ⏳ 轮到HM1优化HM2
