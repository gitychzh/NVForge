# R1622: HM2→HM1 — NVU_PEER_FALLBACK_TIMEOUT 60→72 (+12s, fix HM2 BUDGET mismatch) + restart apply pending BUDGET=66

## 6h Window Data (2026-07-16 14:00 UTC)

| Metric | Value |
|---|---|
| Total | 25 req |
| OK | 15 (60.0% SR) |
| Fail | 10 (40.0%) |

### Per-model breakdown

| Model | OK | ATE | zombie | avg_OK_dur | max_OK_dur |
|---|---|---|---|---|---|
| dsv4p_nv | 8 | 4 (all 504) | 0 | 18,531ms | 41,189ms |
| glm5_2_nv | 7 | 0 | 6 | 12,253ms | 29,436ms |

### 502 Error Breakdown

| Model | Error Type | Count | Avg Duration |
|---|---|---|---|
| dsv4p_nv | all_tiers_exhausted | 4 | 63,826ms |
| glm5_2_nv | zombie_empty_completion | 6 | 12,282ms |

### Peer Fallback

| Attempts | OK | Failed | Pattern |
|---|---|---|---|
| 2 | 0 | 2 | Both TimeoutError at exactly 60,080ms / 60,023ms |

### ms_gw
6/6 100% SR (clean)

### Tier Attempts
14 total: 13 pexec_success, 1 pexec_SSLEOFError. Clean key pool, no 429 cycling.

## Root Cause: PEER_FALLBACK_TIMEOUT < HM2 Tier Budget

HM2 nv_gw has `NVU_TIER_BUDGET_DSV4P_NV=70`. When HM1 peer-falls back to HM2, HM2 needs up to 70s to cycle through its dsv4p_nv keys. With `NVU_PEER_FALLBACK_TIMEOUT=60`, the fallback times out at exactly 60s — before HM2 can complete its key cycle. Both peer-fallback attempts confirmed this: TimeoutError at 60,080ms and 60,023ms.

Additionally, HM1's container was still running `NVU_TIER_BUDGET_DSV4P_NV=70` (R1612 compose=66 never applied because container was never restarted).

## Change

### 1. NVU_PEER_FALLBACK_TIMEOUT: 60→72 (+12s)

HM2 BUDGET=70 + 2s network buffer = 72s. Budget check: 66 (HM1 tier) + 72 (peer-fb) = 138 < 205 (BUDGET) ✓.

### 2. Restart nv_gw container (apply pending BUDGET=66 from R1612)

Container was running BUDGET=70 from pre-R1612. Restart applies compose value 66.

## Verification

```
docker exec nv_gw env | grep NVU_PEER_FALLBACK_TIMEOUT → 72 ✓
docker exec nv_gw env | grep NVU_TIER_BUDGET_DSV4P_NV → 66 ✓
curl http://localhost:40006/health → 200 ✓
```

## Hourly SR

| Hour (UTC) | Total | OK | SR% |
|---|---|---|---|
| 03:00 | 4 | 3 | 75.0 |
| 04:00 | 9 | 5 | 55.6 |
| 05:00 | 10 | 6 | 60.0 |
| 06:00 | 3 | 1 | 33.3 |

## Parameters State

| Parameter | Before | After | Rationale |
|---|---|---|---|
| NVU_PEER_FALLBACK_TIMEOUT | 60 | 72 | HM2 BUDGET=70 + 2s buffer |
| NVU_TIER_BUDGET_DSV4P_NV | 70 (runtime) | 66 (restart) | R1612 compose already set, container restart applies |
| UPSTREAM_TIMEOUT | 66 | 66 | floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | 2 | floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | 1 | floor |
| TIER_COOLDOWN_S | 15 | 15 | floor |
| TIER_TIMEOUT_BUDGET_S | 205 | 205 | floor |
| MS_GW_FALLBACK_TIMEOUT | 120 | 120 | floor |
| NVU_TIER_BUDGET_GLM5_2_NV | 120 | 120 | floor |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | 100 | floor |

## Non-Config-Fixable Failures

- 6 zombie (glm5_2_nv): NVCF content-filter returns `finish_reason=stop` with empty content. NVU_ZOMBIE_EMPTY passthrough sends timeout SSE chunk to trigger openclaw model fallback. Not config-fixable.
- 4 ATE (dsv4p_nv): All 504_nv_gateway_timeout — NVCF function-level degradation. BUDGET=66=UPSTREAM_TIMEOUT floor pattern correct: k1-504(~62s)→exhaust→peer-fb rescue. Config optimizations are at floor.

铁律:只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
