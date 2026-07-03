# R656: HM2→HM1 — NVU_FORCE_STREAM_UPGRADE_TIMEOUT 61→59 (-2s)

**Date**: 2026-07-04 02:20 UTC
**Author**: opc2_uname (HM2 cron job)
**Target**: HM1 (`opc_uname@100.109.153.83`), container `nv_40006_uni`
**Iron Rule**: 只改HM1不改HM2

## Change

| Parameter | Old | New | Delta |
|-----------|-----|-----|-------|
| `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 61 | 59 | -2s |

**Single param per round.** All other parameters unchanged.

## Rationale

R652 UPSTREAM_TIMEOUT trajectory completed (34→25, -9s) and explicitly named `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` as the next pivot parameter. R655 BUDGET 85→80 deployed.

6h logs confirm `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=61` is the **active ceiling** for integrate thinking timeouts:
- `dsv4p_nv` k4 integrate timeout: 61,412ms
- `dsv4p_nv` k1 integrate timeout: 61,389ms
- `dsv4p_nv` k3 attempt elapsed: 61,436ms (IntegrateTimeout)

These three timeouts all hit exactly at the 61s ceiling — the parameter is actively cutting off hanging integrate requests. Reducing to 59:
- Eliminates 2s of wasted wait on integrate timeout failures → accelerates fastbreak/fallback by 2s
- **Streaming paths unaffected**: `kimi_nv` integrate streaming successes keep the read-timeout alive (data chunks flowing rebuild the timeout on each chunk); `glm5_2_nv` uses pexec only (not affected by this parameter)
- `UPSTREAM_TIMEOUT=25` (floor) << 59s → margin 34s safe, no risk of premature cutoff
- All other primary params at floor (CONNECT_RESERVE=1, PEER_FALLBACK=8, MIN_OUTBOUND=0, KEY_COOLDOWN=25)

## Data Collected (pre-change)

### Container env (confirmed)
```
UPSTREAM_TIMEOUT=25
TIER_TIMEOUT_BUDGET_S=80
NVU_CONNECT_RESERVE_S=1
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=61  →  59 (after change)
NVU_PEER_FALLBACK_TIMEOUT=8
NVU_SSLEOF_RETRY_DELAY_S=1.0
NV_INTEGRATE_KEY_COOLDOWN_S=0
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=25
MIN_OUTBOUND_INTERVAL_S=0
```

### DB stats (hermes_logs.nv_requests, 6h window)

| Model | Total | OK | ATE | Success% | Avg(s) | P50(s) | P95(s) | Max(s) |
|-------|-------|----|-----|----------|--------|--------|--------|--------|
| glm5_2_nv | 91 | 88 | 3 | 96.7% | 6.0 | 3.9 | 16.8 | 65.3 |
| kimi_nv | 53 | 53 | 0 | 100.0% | 71.1 | 34.6 | 258.2 | 419.1 |
| dsv4p_nv | 14 | 13 | 1 | 92.9% | 118.4 | 83.4 | 380.5 | 494.1 |

- **4 ATE total**: all `empty_200` NVCF platform bugs (not timeouts), zero `rate_limit` errors
- **dsv4p_nv** 13/14 OK, 1 ATE with k3 timeout at 61.4s → pexec fallback hit k3 empty_200+k4 empty_200 → ATE

### Tier attempts error breakdown (6h)
```
dsv4p_nv  k3  empty_200        2
dsv4p_nv  k2  empty_200        1
dsv4p_nv  k3  IntegrateTimeout  1  (61,436ms)
glm5_2_nv k0  empty_200        1
glm5_2_nv k4  empty_200        1
```

### Container logs (pre-change highlights)
```
[02:11:29.9] k4 → integrate deepseek-ai/deepseek-v4-pro DIRECT
[02:12:31.3] k4 integrate timeout: attempt=61412ms → FASTBREAK
[02:12:31.3] fallback to pexec → k2 success 46.3s
[02:18:37.4] k1 → integrate deepseek-ai/deepseek-v4-pro DIRECT
[02:19:38.8] k1 integrate timeout: attempt=61389ms → FASTBREAK
[02:19:38.8] fallback to pexec → k3 empty_200 → k4 empty_200 → ATE
```

## Post-deploy Verification

- Container restarted `docker compose up -d nv_40006_uni` — OK
- `docker exec nv_40006_uni env | grep FORCE_STREAM_UPGRADE_TIMEOUT` confirms `59`
- Container status: `Up 16 seconds (healthy)`
- All other params unchanged (UPSTREAM=25, BUDGET=80, CONNECT=1, etc.)

## ⏳ 轮到HM1优化HM2