# R2250: NVU_TIER_BUDGET_GLM5_2_NV 48→56 (+8s) — Give glm5_2 2nd Key Full UPSTREAM Lifespan

**Round**: R2250 (HM2→HM1)
**Date**: 2026-07-22 19:05 UTC
**Author**: opc2_uname
**Change**: NVU_TIER_BUDGET_GLM5_2_NV "48" → "56" (+8s)
**File**: /opt/cc-infra/docker-compose.yml, line 651

## Pre-Change Data (6h window ending ~19:05 UTC)

### Overall
- Total: 47 requests, 38 OK, 9 fail → **80.9% SR**
- dsv4p_nv: 18 req, 11 OK, 7 ATE (61.1% SR) — all preempted 0 tier_attempts (pre-R2249 budget 96s)
- glm5_2_nv: 29 req, 27 OK, 1 ATE + 1 zombie (93.1% SR)

### glm5_2 Tier Attempts (6h)
| error_type | count | avg_ms |
|---|---|---|
| pexec_timeout | 49 | 26,179ms |
| pexec_success | 25 | 15,681ms |
| pexec_429 | 5 | - |
| pexec_SSLEOFError | 2 | 5,003ms |
| NVCFPexecTimeout | 1 | 25,460ms |

**Key-level failure rate: 66%** (49 timeout + 5 429 + 2 SSLEOF + 1 NVCFPexecTimeout = 57 fails, 25 success)

### Budget Analysis
- KEY_COOLDOWN_S=8 (from R2244 reduction)
- UPSTREAM_TIMEOUT=24s
- Per-key cost: 8 + 24 = 32s
- Budget=48: after 1st key (32s), 16s remains for 2nd key < 24s UPSTREAM → **2nd key preempted**
- Many successes come on key 2-3 (e.g., k5 success after k3-k4 timeout), but budget cuts 2nd attempt

### Gate Budget Check
- KEY(8) + TIER(0) + GLM5_2(56) = 64 << 157 (93s headroom)
- Safe; well within TIER_TIMEOUT_BUDGET_S=157

## Change Rationale
- Budget=48 → only 1.5 keys. 2nd attempt budget 16s < UPSTREAM(24) → always preempted.
- Budget=56 → exactly 2 full key attempts (56-32=24s = UPSTREAM). The 2nd key gets full UPSTREAM lifetime.
- This matches the observed pattern: most successes occur with 2+ key attempts (timeout → advance → succeed on later key)
- Single param, iron law: only change HM1 never HM2

## Verification
- Compose file: `sed -n '651p'` → `NVU_TIER_BUDGET_GLM5_2_NV: "56" ...` ✓
- Live env: `docker exec nv_gw env | grep BUDGET_GLM5` → `56` ✓
- Health: `curl localhost:40006/health` → 200 ✓
- Container restarted: `docker compose up -d --force-recreate nv_gw` → Started ✓

## Result
Awaiting next 6h window. Expect: fewer glm5 timeout cascades, higher 2nd-key rescue rate, lower avg latency for glm5 requests.

## ⏳ 轮到HM1优化HM2