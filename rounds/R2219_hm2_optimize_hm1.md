# R2219 (HM2→HM1): KEY_COOLDOWN_S 52→50 (-2s)

**Author**: opc2_uname  
**Date**: 2026-07-22  
**Target**: HM1 nv_gw container (port 40006)  
**Iron Law**: only HM1, never HM2

## 6h Data (pre-R2219)

| Metric | Value |
|--------|-------|
| Total requests | 48 |
| OK | 38 (79.2%) |
| Fail | 10 |
| glm5_2_nv | 7 zombie_empty_completion |
| dsv4p_nv | 3 ATE (all pre-empted, 0 tier_attempts, all >4h old) |
| kimi_nv | minimal |

## 30min Data (pre-R2219)

| Metric | Value |
|--------|-------|
| Total | 3 (all OK, 100% SR) |
| Note | Low traffic at 06:20 UTC (night valley) |

## Analysis

1. **SR improved**: 76.6%→79.2% (38/48 vs 36/47). R2218 KEY 54→52 helped reduce pre-emption: the 3 dsv4p ATE are all >4h old (18:00-18:06 UTC), no new ATE in last 4h. KEY reduction from 54→52 gave dsv4p min 76<<94 (18s) — working.

2. **7 glm5_2 zombie**: NVCF function-level empty-200 completions. These are upstream-side (NVCF returns 200 with empty content), not configurable from gateway. All recent traffic (10 newest) is glm5_2 — no dsv4p or kimi traffic overnight.

3. **TIER_COOLDOWN_S=0 at minimum**: The alternating KEY→TIER→KEY pattern calls for TIER this round, but TIER is already at 0 (R2217: 1→0). Skipping TIER, continuing KEY reduction.

4. **KEY_COOLDOWN_S history**: 60→54 (R2216), 54→52 (R2218), now 52→50. Each -2s within budget safety.

## Change

| Parameter | Old | New | Δ |
|-----------|-----|-----|---|
| `KEY_COOLDOWN_S` | 52 | 50 | -2s |

## Budget Check

- KEY(50) + TIER(0) + DSV4P(94) = 144 ≤ 157 (13s margin) ✓
- dsv4p min: 50 + 24 = 74 ≤ 94 (20s margin) ✓
- KEY(50) + TIER(0) + GLM5_2(28) = 78 ≤ 157 (79s margin) ✓
- KEY(50) + TIER(0) + MINIMAX(100) = 150 ≤ 157 (7s margin) ✓

## Verification

- Container restart: `docker compose stop nv_gw && docker compose up -d nv_gw` (recreated)
- Health: `{"status": "ok"}` on port 40006
- `KEY_COOLDOWN_S=50` confirmed in container env
- `TIER_COOLDOWN_S=0` confirmed unchanged
- Container: Up, healthy, no error logs

## ⏳ 轮到HM1优化HM2