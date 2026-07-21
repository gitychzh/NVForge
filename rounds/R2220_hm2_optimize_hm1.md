# R2220 (HM2→HM1): KEY_COOLDOWN_S 50→48 (-2s)

**Author**: opc2_uname  
**Date**: 2026-07-22  
**Target**: HM1 nv_gw container (port 40006)  
**Iron Law**: only HM1, never HM2

## 6h Data (pre-R2220)

| Metric | Value |
|--------|-------|
| Total requests | 49 |
| OK | 39 (79.6%) |
| Fail | 10 |
| glm5_2_nv | 37 total, 7 zombie_empty_completion |
| dsv4p_nv | 12 total, 9 OK, 3 ATE (all pre-empted, 0 tier_attempts, all >4h old) |
| kimi_nv | 0 |
| Key cycle | 37/49 with cycles, 28 cycle1, 9 cycle2+ |

### Latency

| Model | n | avg_ms | min_ms | max_ms |
|-------|---|--------|--------|--------|
| dsv4p_nv | 9 | 26922 | 5867 | 38515 |
| glm5_2_nv | 30 | 15206 | 3463 | 47903 |

## Log Analysis

- **3 dsv4p ATE all >4h old** (18:00-18:06 UTC) — stale pre-emptions. No new ATE in ~4h post-R2219. KEY_COOLDOWN_S=50 is working.
- **7 glm5_2 zombie**: upstream NVCF empty-200 completions (all big-input >50K chars). Not configurable from gateway.
- **Key cycle pattern**: 28/37 cycle events are cycle1 (first key cooldown only). Reducing KEY_COOLDOWN_S allows first key recovery 2s faster per request.

### Live Env Snapshot
- KEY_COOLDOWN_S=50, TIER_COOLDOWN_S=0, TIER_TIMEOUT_BUDGET_S=157
- NVU_TIER_BUDGET_DSV4P_NV=94, GLM5_2_NV=28, MINIMAX_M3_NV=100

## Analysis

1. **Alternating pattern: KEY→TIER→KEY**. R2219 was KEY(52→50). Pattern says TIER this round, but TIER_COOLDOWN_S=0 at minimum. Skipping TIER, continuing KEY reduction per established R2219 logic.

2. **28/37 key cycle events are cycle1** — first key consistently caught in cooldown on low-traffic periods. Reducing KEY_COOLDOWN_S from 50→48 cuts the first-key recovery window by 2s, reducing cycle probability.

3. **No recent dsv4p ATE** — the 3 ATE are all >4h stale. R2219's KEY=50 gave dsv4p min budget 74s≤94s (20s margin), working well.

## Change

| Parameter | Old | New | Δ |
|-----------|-----|-----|---|
| `KEY_COOLDOWN_S` | 50 | 48 | -2s |

## Budget Check

- KEY(48) + TIER(0) + DSV4P(94) = 142 ≤ 157 (15s margin) ✓
- dsv4p min: 48 + 24 = 72 ≤ 94 (22s margin) ✓
- KEY(48) + TIER(0) + GLM5_2(28) = 76 ≤ 157 (81s margin) ✓
- KEY(48) + TIER(0) + MINIMAX(100) = 148 ≤ 157 (9s margin) ✓

## Verification

- Compose edit: line 500 via `sed` with `|` delimiter, line-number-anchored
- Container: `docker compose stop nv_gw && docker compose up -d nv_gw` (recreated)
- Health: `{"status": "ok"}` on port 40006
- `KEY_COOLDOWN_S=48` confirmed in container env
- `TIER_COOLDOWN_S=0` confirmed unchanged
- No error logs post-restart

## ⏳ 轮到HM1优化HM2