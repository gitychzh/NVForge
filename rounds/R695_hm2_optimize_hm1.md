# R695: HM2→HM1 — NVU_PEXEC_TIMEOUT_FASTBREAK 1→2 (+1)

**Date**: 2026-07-04 14:58 UTC

## Data Summary (30min window, container restart 13:41Z from R694, FORCE_STREAM_UPGRADE_TIMEOUT=40 since R694)

### DB Summary
- Total: 177, OK: 133, Fail: 44, Success: 75.1%
- glm5_2_nv: 104 req, 95 OK (91.3%), 9 fail (all ATE, server-side dispatch rejection)
- dsv4p_nv: 66 req, 31 OK (47.0%), 35 fail (all ATE, pexec timeout at ~40s + FASTBREAK=1)
- kimi_nv: 7 req, 7 OK (100%), 0 fail
- pexec path: 124/124 OK = 100% (all model successes)
- integrate: 6/6 OK = 100%
- NULL upstream (ATE path): 47 req, 3 success (peer fallback), 44 fail

### Latency Stats (30min, status=200)
- avg_ms=16486, p50=11954ms, p90=35356ms, p95=40189ms, max=84273ms
- pexec avg_ms=16833, max_dur=84273ms (84.3s) — some pexec near ~40s boundary (FORCE_STREAM_UPGRADE_TIMEOUT=40)
- ATE path avg_ms=40574ms (~40s timeout + peer fallback 25s)

### Per-Model Breakdown (30min)
| request_model | total | success | errors | avg_ms  | p95_ms  |
|---------------|-------|---------|--------|---------|---------|
| glm5_2_nv     |   104 |      95 |      9 |   12856 |   31182 |
| dsv4p_nv      |    66 |      31 |     35 |   29001 |   46203 |
| kimi_nv       |     7 |       7 |      0 |   10323 |   24042 |

### upstream_type Breakdown (30min)
| upstream_type |  n  | success | avg_ms |
|---------------|-----|---------|--------|
| nvcf_pexec    | 124 |     124 |  16833 |
| (NULL)        |  47 |       3 |  40574 |
| nv_integrate  |   6 |       6 |  10984 |

### ATE Detail (30min, status≠200)
| start_tier_idx | fallback_from | fallback_to | tiers_tried_count | cnt |
|----------------|---------------|-------------|-------------------|-----|
|              1 |               |             |                 1 |  33 |
|              3 |               |             |                 1 |   9 |

**Key finding**: All 42 ATE have `tiers_tried_count=1` — FASTBREAK=1 triggers after a single key timeout (~40s), abandoning remaining 4 keys immediately.

### Fallback Stats (30min)
| fallback_occurred | cnt |
|-------------------|-----|
| f                 | 158 |
| t                 |   6 |

Fallback rate: 6/164 = 3.7% (low, peer fallback rarely engaged).

### Container Logs (errors/warns)
- 1 INFO message: `[NV-THINKING-TIMEOUT] thinking request stream=True → extended timeout 40s` (normal behavior, not error)
- Zero ERROR/WARN/exception in docker logs

### Key Env Snapshot (pre-change, post-R694)
```
TIER_TIMEOUT_BUDGET_S=72
UPSTREAM_TIMEOUT=25
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=40   (R694: 25→40)
MIN_OUTBOUND_INTERVAL_S=0
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_CONNECT_RESERVE_S=0
NVU_EMPTY_200_FASTBREAK=2
NVU_PEXEC_TIMEOUT_FASTBREAK=1          ← target
NVU_PEER_FALLBACK_TIMEOUT=25
NVU_SSLEOF_RETRY_DELAY_S=1.0
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=25
```

## Optimization Decision

**Parameter**: `NVU_PEXEC_TIMEOUT_FASTBREAK` 1→2 (+1)

**Rationale**: R694 raised `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` 25→40, creating a new failure pattern: dsv4p_nv pexec requests now timeout at ~40s (matching FORCE_STREAM_UPGRADE_TIMEOUT=40), then FASTBREAK=1 immediately abandons the remaining 4 keys. DB confirms: all 42 ATE have `tiers_tried_count=1`. With TIER_TIMEOUT_BUDGET_S=72, after 1 key timeout at ~40s there is ~32s remaining — enough headroom for a 2nd key attempt (successful pexec completions observed at 15-33s in logs). Raising FASTBREAK to 2 allows the proxy to try a 2nd key before giving up, potentially rescuing ~11 of the 33 dsv4p_nv ATE (estimated 1/3 rescue rate based on 2nd-key success window). Peer fallback (25s timeout) still engages as last resort if 2nd key also times out. This is a targeted reversal of R559 (which set 2→1 when timeout was ~63s and 2nd key had no time); now with 40s timeout + 72s budget, the 2nd key has viable headroom.

**Trajectory context**: R559 set FASTBREAK 2→1 (timeout was ~63s, 2nd key had no time). R694 raised FORCE_STREAM_UPGRADE_TIMEOUT to 40s, changing the landscape: timeout is now ~40s (not 63s), leaving 32s for 2nd key. R695 reverses R559's logic — 2nd key now has viable headroom.

## Execution

### Method: Python script via SCP (full line rewrite, line 589)
```bash
# 1. Write patch script locally (/tmp/r695_patch.py)
#    TARGET: line 589, NVU_PEXEC_TIMEOUT_FASTBREAK: "1" → "2"

# 2. SCP to HM1
scp -P 222 /tmp/r695_patch.py opc_uname@100.109.153.83:/tmp/r695_patch.py

# 3. Execute
ssh -p 222 opc_uname@100.109.153.83 "python3 /tmp/r695_patch.py"
# → OLD: NVU_PEXEC_TIMEOUT_FASTBREAK: "1"  # R559...
# → NEW: NVU_PEXEC_TIMEOUT_FASTBREAK: "2"  # R695...
# → VERIFY PASS: value is 2

# 4. Restart (compose up -d, not restart)
ssh -p 222 opc_uname@100.109.153.83 "cd /opt/cc-infra && docker compose up -d nv_gw"
# → Container nv_gw Recreated → Started
```

### 4-Way Consistency Verified (2026-07-04 14:57 UTC, post-restart)
```
Source 1 - container env:     NVU_PEXEC_TIMEOUT_FASTBREAK=2  ✅
Source 2 - compose file:     line 589: NVU_PEXEC_TIMEOUT_FASTBREAK: "2"  ✅
Source 3 - container status: nv_gw Up 27 seconds (healthy), StartedAt=2026-07-04T14:57:44Z  ✅
Source 4 - full env snapshot: all 15 key params verified aligned compose↔container  ✅
```

### Post-Restart DB Verification
- No new requests yet at time of verification (proxy only receives traffic when agents initiate)
- Pre-restart regime confirmed: pexec 124/124 = 100% OK, all 44 failures are ATE with tiers_tried_count=1
- No config errors in logs

## Iron Rule Compliance
- ✅ Single parameter per round (NVU_PEXEC_TIMEOUT_FASTBREAK only)
- ✅ Only changed HM1 (opc_uname@100.109.153.83, `/opt/cc-infra/docker-compose.yml` line 589, container `nv_gw`), never HM2 (opc2_uname local)
- ✅ Data-driven: 42 ATE with tiers_tried_count=1, all at ~40s timeout, 32s headroom for 2nd key
- ✅ Full line rewrite avoids R688 trajectory corruption pitfall
- ✅ 4-way consistency verified (env, compose, container status, full param alignment)

## ⏳ 轮到HM1优化HM2
