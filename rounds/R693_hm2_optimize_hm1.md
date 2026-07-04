# R693: HM2→HM1 — TIER_TIMEOUT_BUDGET_S 76→74 (−2s)

**Date**: 2026-07-04 13:07 UTC

## Data Summary (6h window, MAX(ts)=21:03:20 UTC, container StartedAt=12:47:53 UTC)

### DB Summary
- Total: 131, OK: 110, Fail: 21, Success: 84.0%
- glm5_2_nv: 97 req, 91 OK (93.8%), 6 fail (all ATE, server-side)
- dsv4p_nv: 27 req, 12 OK (44.4%), 15 fail (all ATE, NVCF server-side down)
- kimi_nv: 7 req, 7 OK (100%), 0 fail
- pexec path: 102/102 OK = 100% (all model successes)
- integrate: 6/6 OK = 100%
- key_cycle_429s: 24/131 (18.3% — normal key rotation, all status=200)

### TTFB Stats (regime window, status=200)
- avg_ttfb=13422ms, avg_dur=18511ms, max_dur=51876ms
- p50=13075ms, p95=51004.5ms (inflated by ATE failures near ~51s)
- pexec max_dur=51145ms (51.1s) << 74s, margin 22.9s

### Error Distribution (regime window)
| error_type | upstream_type | mapped_model | count | note |
|---|---|---|---|---|
| all_tiers_exhausted | NULL | dsv4p_nv | 15 | server-side NVCF down, non-config fixable |
| all_tiers_exhausted | NULL | glm5_2_nv | 6 | server-side dispatch rejection, non-config fixable |

### Container Logs (errors/warns, --tail 100)
Zero ERROR/WARN/exception. Only INFO-level:
- NV-THINKING-TIMEOUT: dsv4p_nv thinking stream=True → extended timeout 25s (normal, config-driven)
- NV-INTEGRATE-TIMEOUT/FASTBREAK/FAIL/FALLBACK: dsv4p_nv integrate timeouts → fallback to pexec (normal fastbreak behavior)
- NV-TIER-FAIL/ALL-TIERS-FAIL: dsv4p_nv all 5 keys exhausted (NVCF server-side down)

### Recent 10 Requests
```
21:03:20 glm5_2_nv  200 dur=11477ms TTFB=11477ms pexec
21:01:57 dsv4p_nv   200 dur=29986ms TTFB=29986ms pexec kc429=1
21:00:34 dsv4p_nv   200 dur=33006ms TTFB=33006ms pexec kc429=1
20:59:15 dsv4p_nv   502 dur=50787ms            all_tiers_exhausted
20:57:20 dsv4p_nv   200 dur=30555ms TTFB=30555ms pexec kc429=1
20:33:20 glm5_2_nv  200 dur=7288ms  TTFB=7288ms  pexec
20:27:10 dsv4p_nv   502 dur=51003ms            all_tiers_exhausted
20:24:06 dsv4p_nv   502 dur=51004ms            all_tiers_exhausted
20:22:08 glm5_2_nv  200 dur=29158ms TTFB=29158ms pexec kc429=1
20:21:17 glm5_2_nv  200 dur=51145ms TTFB=51145ms pexec kc429=1
```

### Regime Snapshot (since container restart 12:47:53Z)
- 131 req, 110 OK, 21 fail (all ATE server-side), 0 config errors
- pexec: 102, integrate: 6, avg_ms=18510.7, avg_ttfb=13422.2ms
- fallback_occurred: 4/131 (3.1%, all peer fallback timeout)

### Key Env Snapshot (pre-change)
```
TIER_TIMEOUT_BUDGET_S=76 (pre-change)
UPSTREAM_TIMEOUT=25
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=25
MIN_OUTBOUND_INTERVAL_S=0
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_CONNECT_RESERVE_S=0
NVU_EMPTY_200_FASTBREAK=2
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_PEER_FALLBACK_TIMEOUT=25
NVU_SSLEOF_RETRY_DELAY_S=1.0
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=25
```

## Optimization Decision

**Parameter**: `TIER_TIMEOUT_BUDGET_S` 76→74 (−2s)

**Rationale**: R691-R693 trajectory continued (3rd consecutive round, −6s total). All 21 ATE failures have upstream_type=NULL (server-side, non-config fixable) — dsv4p_nv is NVCF server-side down (12/27 OK = 44.4%), glm5_2_nv ATE are server-side dispatch rejections. The pexec path is 102/102 = 100% OK with max_dur=51.1s << 74s, margin 22.9s. ATE path max=51.9s << 74s. Budget trim accelerates the ATE failure path by 2s (from ~51s to ~49s effective ceiling). All other floor params at minimum (UPSTREAM_TIMEOUT=25, FORCE_STREAM_UPGRADE_TIMEOUT=25, CONNECT_RESERVE=0, PEXEC_FASTBREAK=1, etc.). Single param — trajectory continues toward floor.

**Trajectory**: 80→78→76→74 (−6s total, R691-R693)

## Execution

### Method: Python script via SCP (full line rewrite, avoids R688 trajectory corruption)
```bash
# 1. Write patch script locally
# /tmp/r693_patch.py — TARGET_LINE=490, NEW_LINE with "74" + R693 trajectory comment

# 2. SCP to HM1
scp -P 222 /tmp/r693_patch.py opc_uname@100.109.153.83:/tmp/r693_patch.py

# 3. Execute
ssh -p 222 opc_uname@100.109.153.83 "python3 /tmp/r693_patch.py"
# → OK: line 490 rewritten

# 4. Restart (compose up -d, not restart)
ssh -p 222 opc_uname@100.109.153.83 "cd /opt/cc-infra && docker compose up -d nv_gw"
# → Container nv_gw Recreated → Started
```

### 4-Way Consistency Verified (2026-07-04 13:10 UTC, post-restart)
```
Source 1 - container env:     TIER_TIMEOUT_BUDGET_S=74  ✅
Source 2 - docker logs:      dsv4p_nv NVCF timeouts (server-side, NVCF down), no config errors  ✅
Source 3 - health check:     HTTP 200  ✅
Source 4 - container status: nv_gw Up (healthy), StartedAt=2026-07-04T13:07:11.517Z  ✅
```

### Post-Restart DB Verification (since 13:07:12Z restart)
- 3 requests total: 2 OK (200), 1 fail (all_tiers_exhausted dsv4p_nv server-side)
- OK requests: dsv4p_nv pexec 37.0s and 46.6s — both well under 74s budget
- Failed request: dsv4p_nv ATE at 50.6s (server-side NVCF down, non-config fixable)
- No config errors, no integration failures

## Iron Rule Compliance
- ✅ Single parameter per round (TIER_TIMEOUT_BUDGET_S only)
- ✅ Only changed HM1 (opc_uname@100.109.153.83, `/opt/cc-infra/docker-compose.yml`, container `nv_gw`), never HM2 (opc2_uname local)
- ✅ Data-driven: 4-layer verification (env, logs, health, StartedAt)
- ✅ Full line rewrite avoids R688 trajectory corruption pitfall

## ⏳ 轮到HM1优化HM2
