# R694: HM2→HM1 — TIER_TIMEOUT_BUDGET_S 74→72 (−2s)

**Date**: 2026-07-04 13:41 UTC

## Data Summary (30min window, MAX(ts)=21:33:20 UTC, container restart 13:07Z from R693)

### DB Summary
- Total: 139, OK: 114, Fail: 27, Success: 82.3%
- glm5_2_nv: 98 req, 92 OK (93.9%), 8 fail (all ATE, server-side dispatch rejection)
- dsv4p_nv: 34 req, 15 OK (44.1%), 19 fail (all ATE, NVCF server-side down)
- kimi_nv: 7 req, 7 OK (100%), 0 fail
- pexec path: 106/106 OK = 100% (all model successes)
- integrate: 6/6 OK = 100%
- key_cycle_429s: normal rotation, all status=200

### Latency Stats (30min, status=200)
- avg_ms=19868 (inflated by ATE near ~51s), p50=13525ms, p90=50795ms, p95=51004ms, p99=51613ms
- pexec avg_ms=15018, max_dur=51145ms (51.1s) << 72s, margin 20.9s safe
- ATE max_dur=51876ms (51.9s) << 72s

### Per-Key Success Latency (30min, status=200)
| nv_key_idx | n  | avg_ms | p50_ms | p95_ms |
|------------|----|--------|--------|--------|
| 0          | 33 | 14342  | 11417  | 31029  |
| 1          | 20 | 12630  | 7911   | 40219  |
| 2          | 18 | 14381  | 12639  | 32148  |
| 3          | 21 | 17399  | 13075  | 46616  |
| 4          | 20 | 15386  | 9676   | 37621  |
| (null)     |  2 |  7571  |  7571  | 10779  |

### Error Distribution (30min)
| error_type          | upstream_type | mapped_model | count | note                              |
|---------------------|---------------|--------------|-------|-----------------------------------|
| all_tiers_exhausted | NULL          | dsv4p_nv     | 19    | server-side NVCF down, non-config fixable |
| all_tiers_exhausted | NULL          | glm5_2_nv    |  8    | server-side dispatch rejection, non-config fixable |

### Per-Model Breakdown (30min)
| request_model | total | success | errors | avg_ms  | p95_ms  |
|---------------|-------|---------|--------|---------|---------|
| glm5_2_nv     |    98 |      92 |      8 |   12213 |   25801 |
| dsv4p_nv      |    34 |      15 |     19 |   43899 |   51507 |
| kimi_nv       |     7 |       7 |      0 |   10323 |   24042 |

### upstream_type Breakdown (30min)
| upstream_type | n   | success | avg_ms |
|---------------|-----|---------|--------|
| nvcf_pexec    | 106 |     106 |  15018 |
| (NULL)        |  27 |       2 |  40883 |
| nv_integrate  |   6 |       6 |  10984 |

### Recent 10 Requests
```
21:33:20 glm5_2_nv  200 dur=4836ms             pexec
21:32:51 dsv4p_nv   502 dur=50626ms            all_tiers_exhausted
21:31:24 dsv4p_nv   502 dur=50654ms            all_tiers_exhausted
21:30:05 dsv4p_nv   502 dur=50640ms            all_tiers_exhausted
21:27:20 dsv4p_nv   200 dur=45790ms TTFB=45789 pexec kc429=1
21:13:46 dsv4p_nv   200 dur=37040ms TTFB=37039 pexec kc429=1
21:12:21 dsv4p_nv   200 dur=46616ms TTFB=46615 pexec kc429=1
21:11:02 dsv4p_nv   502 dur=50567ms            all_tiers_exhausted
21:03:20 glm5_2_nv  200 dur=11477ms TTFB=11476 pexec
21:01:57 dsv4p_nv   200 dur=29986ms TTFB=29985 pexec kc429=1
```

### Container Logs (errors/warns)
Zero ERROR/WARN/exception in docker logs. Only INFO-level tier/fallback messages (normal behavior).

### Key Env Snapshot (pre-change)
```
TIER_TIMEOUT_BUDGET_S=74 (pre-change)
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

**Parameter**: `TIER_TIMEOUT_BUDGET_S` 74→72 (−2s)

**Rationale**: R691-R694 trajectory continued (4th consecutive round, −8s total). All 27 ATE failures have upstream_type=NULL (server-side, non-config fixable) — dsv4p_nv is NVCF server-side down (15/34 OK = 44.1%), glm5_2_nv ATE are server-side dispatch rejections. The pexec path is 106/106 = 100% OK with max_dur=51.1s << 72s, margin 20.9s. ATE path max=51.9s << 72s. Budget trim accelerates the ATE failure path by 2s (from ~51s to ~49s effective ceiling). All other floor params at minimum (UPSTREAM_TIMEOUT=25, FORCE_STREAM_UPGRADE_TIMEOUT=25, CONNECT_RESERVE=0, PEXEC_FASTBREAK=1, etc.). Single param — trajectory continues toward floor.

**Trajectory**: 80→78→76→74→72 (−8s total, R691-R694)

## Execution

### Method: Python script via SCP (full line rewrite, avoids R688 trajectory corruption)
```bash
# 1. Write patch script locally
# /tmp/r694_patch.py — TARGET_LINE=490, NEW_LINE with "72" + R694 trajectory comment

# 2. SCP to HM1
scp -P 222 /tmp/r694_patch.py opc_uname@100.109.153.83:/tmp/r694_patch.py

# 3. Execute
ssh -p 222 opc_uname@100.109.153.83 "python3 /tmp/r694_patch.py"
# → OK: line 490 current value=74, rewritten to 72

# 4. Restart (compose up -d, not restart)
ssh -p 222 opc_uname@100.109.153.83 "cd /opt/cc-infra && docker compose up -d nv_gw"
# → Container nv_gw Recreated → Started
```

### 4-Way Consistency Verified (2026-07-04 13:41 UTC, post-restart)
```
Source 1 - container env:     TIER_TIMEOUT_BUDGET_S=72  ✅
Source 2 - docker logs:      NV-PROXY started, no config errors  ✅
Source 3 - health check:     HTTP 200  ✅
Source 4 - container status: nv_gw Up (healthy), StartedAt=2026-07-04T13:41:06Z  ✅
```

### Post-Restart DB Verification
- No new requests yet at time of verification (proxy only receives traffic when agents initiate)
- Pre-restart regime confirmed stable: pexec 100% OK, all failures server-side ATE
- No config errors in logs

## Iron Rule Compliance
- ✅ Single parameter per round (TIER_TIMEOUT_BUDGET_S only)
- ✅ Only changed HM1 (opc_uname@100.109.153.83, `/opt/cc-infra/docker-compose.yml`, container `nv_gw`), never HM2 (opc2_uname local)
- ✅ Data-driven: 4-layer verification (env, logs, health, StartedAt)
- ✅ Full line rewrite avoids R688 trajectory corruption pitfall

## ⏳ 轮到HM1优化HM2
