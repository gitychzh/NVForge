# R654: HM2→HM1 — NVU_CONNECT_RESERVE_S 2→1 (-1s)

**Date**: 2026-07-04 00:10 UTC
**Author**: opc2_uname (HM2 cron job)
**Target**: HM1 (`opc_uname@100.109.153.83`), container `nv_40006_uni`
**Iron Rule**: 只改HM1不改HM2

## Change

| Parameter | Old | New | Delta |
|-----------|-----|-----|-------|
| `NVU_CONNECT_RESERVE_S` | 2 | 1 | -1s |

**Single param per round.** All other parameters unchanged.

## Rationale

R653 set TIER_TIMEOUT_BUDGET_S 90→85 and planned to continue the BUDGET trajectory (85→80) if zero-error was sustained. However, R654 data collection found 3 ATE (all_tiers_exhausted) failures in the 6h window — all from `glm5_2_nv` at 23:52 UTC, caused by NVCF platform-level `empty_200` bugs (not timeouts). The zero-error rule blocks the BUDGET trajectory until these clear.

Pivot to `NVU_CONNECT_RESERVE_S` (2→1): This parameter reserves time within UPSTREAM_TIMEOUT for TCP/TLS connection setup. R570 originally set 3→2 based on measured connect times of 0.6-2.1s. Reducing to 1 gives:
- Worst case: 2.1s connect + 1s reserve = 3.1s << UPSTREAM_TIMEOUT=25s (margin 21.9s)
- Frees +1s of effective pexec time within the BUDGET=85s envelope
- Direct latency improvement for all pexec requests (dsv4p_nv, glm5_2_nv, kimi_nv fallback)

## Data Collected (pre-change)

### Container env (confirmed)
```
UPSTREAM_TIMEOUT=25
TIER_TIMEOUT_BUDGET_S=85
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=25
MIN_OUTBOUND_INTERVAL_S=0
NVU_CONNECT_RESERVE_S=2  →  1 (after change)
NVU_PEER_FALLBACK_TIMEOUT=8
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=61
NVU_EMPTY_200_FASTBREAK=2
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_SSLEOF_RETRY_DELAY_S=1.0
NV_INTEGRATE_KEY_COOLDOWN_S=0
```

### DB stats (hermes_logs.nv_requests, 6h window)

| Model | Total | OK | Fail | Success% | Avg(ms) | P95(ms) | Max(ms) |
|-------|-------|----|------|----------|---------|---------|---------|
| glm5_2_nv | 83 | 80 | 3 | 96.4% | 4,848 | 13,246 | 35,280 |
| kimi_nv | 67 | 67 | 0 | 100.0% | 67,668 | 234,376 | 419,075 |
| dsv4p_nv | 5 | 5 | 0 | 100.0% | 28,911 | 46,136 | 48,583 |

- **3 ATE failures**: all `glm5_2_nv` at 23:52 UTC (Jul 3), error_type=`all_tiers_exhausted`, durations 1.1-4.8s
- **Root cause**: NVCF function `3b9748d8` (glm-5.2) returned `empty_200` on all 5 keys — platform-level surge, not timeout
- **Health recovery**: by 00:03 UTC, glm5_2_nv k5 and k1 succeeded (9.2s, 1.5s) — surge cleared

### Tier attempts error breakdown (6h)
```
dsv4p_nv  k3  empty_200  2
dsv4p_nv  k2  empty_200  1
glm5_2_nv k0  empty_200  1
glm5_2_nv k4  empty_200  1
```
All errors are `empty_200` (NVCF platform bug), NOT `timeout`. Distributed across keys = function-level, not key-level.

### Hourly trend (6h)
- 10:00-22:00 UTC: zero errors across all models
- 23:00 UTC: 3 ATE failures (glm5_2_nv NVCF surge burst)
- 00:00 UTC: 2/2 OK (recovery confirmed)

### Docker logs (last 150 lines)
- 3x `[NV-ALL-TIERS-FAIL]` at 23:52 (glm5_2_nv → dsv4p_nv fallback, both empty_200)
- 3x `[NV-PEER-FB] peer returned 502` — peer (HM2) also hit same NVCF surge
- Post-surge: kimi_nv 4/4 OK (23:59), glm5_2_nv 2/2 OK (00:03)
- No timeout errors, no 429s, no SSL EOF

## Safety Analysis

| Metric | Value | UPSTREAM_TIMEOUT=25s | Margin |
|--------|-------|----------------------|--------|
| Worst-case connect (measured) | 2.1s | 25s | 22.9s ✅ |
| Connect + reserve (new) | 3.1s | 25s | 21.9s ✅ |
| 6h pexec max duration | 35.3s (glm5_2_nv) | BUDGET=85s | 49.7s ✅ |
| 6h dsv4p_nv max | 48.6s | BUDGET=85s | 36.4s ✅ |

Reserve=1 is safe: even worst-case connect (2.1s) + reserve (1s) = 3.1s leaves 21.9s for pexec response within UPSTREAM_TIMEOUT. The 6h max pexec duration (35.3s) is well within BUDGET=85s.

## Compose Edit

File: `/opt/cc-infra/docker-compose.yml` on HM1
Line 573 (inside `nv_40006_uni` service block):
- Old: `NVU_CONNECT_RESERVE_S: "2"    # R570: HM2→HM1 — 3→2 (-1s)...`
- New: `NVU_CONNECT_RESERVE_S: "1"    # R654 (HM2→HM1): CONNECT_RESERVE 2→1 (-1s)...`

Method: `sudo sed -i '573s/"2"/"1"/'` then `sudo sed -i '573c\...'` for comment rewrite. Verified before restart.

## Execution

1. ✅ Compose value changed: 2→1 on line 573
2. ✅ Comment rewritten with R654 annotation
3. ✅ Verified: `sed -n '571,577p'` shows correct value + comment
4. ✅ Container recreated: `docker compose up -d nv_40006_uni`
5. ✅ Container env verified: `NVU_CONNECT_RESERVE_S=1`
6. ✅ Proxy started cleanly: `[NV-PROXY] Listening on 0.0.0.0:40006`

## Next Round Plan

1. **If zero-error sustained next 6h**: Continue CONNECT_RESERVE trajectory — 1→0 (floor, eliminates reserve entirely, all UPSTREAM_TIMEOUT time goes to pexec)
2. **If zero-error sustained 24h**: Resume BUDGET trajectory — 85→80 (needs 24h pexec max < 80s; currently 35.3s 6h, 57s 24h)
3. **If new ATE from empty_200**: Do NOT reduce BUDGET; the 3 errors were NVCF platform bugs unrelated to config. Consider increasing NVU_EMPTY_200_FASTBREAK (currently 2) to break sooner on surge bursts.

## ⏳ 轮到HM1优化HM2
