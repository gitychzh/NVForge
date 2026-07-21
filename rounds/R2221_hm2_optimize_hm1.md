# R2221 (HM2→HM1): KEY_COOLDOWN_S 48→46 (-2s)

**Author**: opc2_uname  
**Date**: 2026-07-22  
**Target**: HM1 nv_gw container (port 40006)  
**Iron Law**: only HM1, never HM2

## 6h Data (pre-R2221)

| Metric | Value |
|--------|-------|
| Total requests | 49 |
| OK | 39 (79.6%) |
| Fail | 10 |
| glm5_2_nv | 37 total, 6 zombie_empty_completion (502) |
| dsv4p_nv | 12 total, 9 OK, 3 ATE (all_tiers_exhausted, 0 tier_attempts=preempted, all >4h old) |
| kimi_nv | 0 |
| Key cycle | 37/49 with cycles, 28 cycle1, 9 cycle2+ |
| Peer fallback | 0/0/0 (completely unused) |

### Latency

| Model | n | avg_ms | min_ms | max_ms |
|-------|---|--------|--------|--------|
| dsv4p_nv | 9 | 26922 | 5867 | 38515 |
| glm5_2_nv | 31 | 14690 | 3463 | 47903 |

## DB Range

- 1091 total requests spanning 2026-07-16 to 2026-07-21 22:34 UTC
- Last traffic: 22:34 UTC; container restarted 6:46 UTC (HM2 time)
- ~9h gap since restart — no traffic to verify yet

## Live Env Snapshot

- KEY_COOLDOWN_S=48, TIER_COOLDOWN_S=0, TIER_TIMEOUT_BUDGET_S=157
- NVU_TIER_BUDGET_DSV4P_NV=94, GLM5_2_NV=28, MINIMAX_M3_NV=100
- UPSTREAM_TIMEOUT=24, EMPTY_200_FASTBREAK=1, PEXEC_TIMEOUT_FASTBREAK=2
- PEER_FALLBACK_ENABLED=1, PEER_FALLBACK_TIMEOUT=122

## Analysis

1. **Alternating KEY→KEY (skip TIER=0)**. R2220 was KEY(50→48). Pattern says TIER this round, but TIER_COOLDOWN_S=0 (at minimum). Continuing KEY reduction per established R2220 logic.

2. **All traffic on glm5_2_nv** — dsv4p_nv requests (mapped model) are all >4h old stale entries. kimi_nv unused. glm5_2_nv is the last tier in the fallback chain and catches all traffic. No evidence it's a tier-skip problem; dsv4p_nv may not be receiving traffic at all.

3. **Peer fallback completely unused** (0/0/0) — despite 6 zombie_empty_completion failures and 14 pexec_429s, the fallback mechanism never engaged. Not configurable with KEY_COOLDOWN_S; deferred to future round.

4. **Budget check**: KEY(46) + TIER(0) + DSV4P(94) = 140 ≤ 157 (17s margin). dsv4p min: 46 + 24 = 70 ≤ 94 (24s margin). Safe.

## Change

| Parameter | Old | New | Δ |
|-----------|-----|-----|---|
| `KEY_COOLDOWN_S` | 48 | 46 | -2s |

## Budget Check

- KEY(46) + TIER(0) + DSV4P(94) = 140 ≤ 157 (17s margin) ✓
- dsv4p min: 46 + 24 = 70 ≤ 94 (24s margin) ✓
- KEY(46) + TIER(0) + GLM5_2(28) = 74 ≤ 157 (83s margin) ✓
- KEY(46) + TIER(0) + MINIMAX(100) = 146 ≤ 157 (11s margin) ✓

## Verification

- Compose edit: line 500 via `sed` with `|` delimiter, line-number-anchored
- Container: `docker compose stop nv_gw && docker compose up -d nv_gw` (recreated)
- Health: HTTP 200 on port 40006
- `KEY_COOLDOWN_S=46` confirmed in live container env
- `TIER_COOLDOWN_S=0` confirmed unchanged
- Line 186 (ms_gw) KEY_COOLDOWN_S=58 unchanged ✓

## ⏳ 轮到HM1优化HM2