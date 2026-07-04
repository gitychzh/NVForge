# R682: HM2→HM1 — NVU_FORCE_STREAM_UPGRADE_TIMEOUT 35→34 (−1s)

**Date**: 2026-07-04 11:55 UTC

## Data Summary (6h window)

### DB Summary
- Total: 226, OK: 222, Fail: 4, Success: 98.2%
- pexec: 210 req, 210 OK (100%), avg TTFB=7024ms, p95 TTFB=18016ms, avg dur=7219ms
- integrate: 12 req, 12 OK (100%), avg TTFB=53187ms, p95 TTFB=88375ms, avg dur=112944ms
- ATE (all_tiers_exhausted): 4 — server-side, non-config-fixable

### Container Logs (errors/warns)
Zero errors. Only routine operational messages:
- NV-THINKING-TIMEOUT (glm5_2_nv thinking request stream=True → extended timeout 35s) — INFO-level, working correctly
- No 429, 502, timeout errors, fallback triggers, or kc429

### Last 10 Requests
```
11:56:33 glm5_2_nv 200 TTFB=1650ms  pexec
11:56:27 glm5_2_nv 200 TTFB=3793ms  pexec
11:51:39 glm5_2_nv 200 TTFB=3438ms  pexec
11:51:27 glm5_2_nv 200 TTFB=9305ms  pexec
11:46:35 glm5_2_nv 200 TTFB=1702ms  pexec
11:46:27 glm5_2_nv 200 TTFB=6046ms  pexec
11:41:32 glm5_2_nv 200 TTFB=2018ms  pexec
11:41:27 glm5_2_nv 200 TTFB=2893ms  pexec
11:36:46 glm5_2_nv 200 TTFB=1371ms  pexec
11:36:27 glm5_2_nv 200 TTFB=17131ms pexec
```
All 10 recent = 200 OK, no errors, no fallback, zero key_cycle_429s

### Key Env Snapshot
```
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=35 (pre-change)
NVU_FORCE_STREAM_UPGRADE=1
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=8
UPSTREAM_TIMEOUT=25
TIER_TIMEOUT_BUDGET_S=80
MIN_OUTBOUND_INTERVAL_S=0
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_EMPTY_200_FASTBREAK=2
NVU_PEXEC_TIMEOUT_FASTBREAK=1
```

## Optimization Decision

**Parameter**: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` 35→34 (−1s)

**Rationale**: R656-R682 trajectory continued. The system is in a sustained zero-error regime: 6h 226req/222OK 98.2%, 4 ATE are server-side non-config-fixable. pexec 210/210 OK 100%, integrate 12/12 OK 100%. pexec p95 TTFB=18016ms << UPSTREAM_TIMEOUT=25s, margin ~7s. The thinking timeout extension (34s) still covers slowest glm5_2 observed (17.1s, 2× margin). Deeper force-stream reduces envelope latency for thinking-aware streaming without risking timeout failures. Single param — continue until signal of tension.

**Trajectory**: 61→59→58→57→56→55→54→53→52→51→50→49→48→47→46→45→44→43→42→41→40→39→38→37→36→35→34 (−27s total)

## Execution

### Method: Python via SCP (R682 template)
```bash
# SCP rewrite script
scp -P 222 rewrite_682.py opc_uname@100.109.153.83:/tmp/rewrite_682.py

# Execute on HM1
ssh -p 222 opc_uname@100.109.153.83 'python3 /tmp/rewrite_682.py'

# Restart
cd /opt/cc-infra && docker compose up -d nv_40006_uni
```

### 3-Way Consistency Verified
- ✅ Compose line 492: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "34"`
- ✅ Docker compose config: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "34"`
- ✅ Container env: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=34`
- ✅ Container restarted cleanly: `nv_40006_uni Recreated → Started`

## Iron Rule Compliance
- ✅ Single parameter per round
- ✅ Only changed HM1 (opc_uname@100.109.153.83, `/opt/cc-infra/docker-compose.yml`, container `nv_40006_uni`), never HM2 (opc2_uname local)
- ✅ Data-driven: collected logs, env, DB before deciding

## ⏳ 轮到HM1优化HM2