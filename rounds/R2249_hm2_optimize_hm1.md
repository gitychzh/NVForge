# R2249 (HM2→HM1): NVU_TIER_BUDGET_DSV4P_NV 96→102 (+6s)

**Date**: 2026-07-22 18:40 UTC  
**Author**: opc2_uname (HM2, automated)  
**Role**: HM2 optimizing HM1  
**Target**: HM1 (opcsname-1, 100.109.153.83)  
**Parameter**: NVU_TIER_BUDGET_DSV4P_NV (compose line 658, nv_gw env)

## Data Summary (6h window)

| Metric | dsv4p_nv | glm5_2_nv | Total |
|--------|----------|-----------|-------|
| Requests | 18 | 29 | 47 |
| Success | 11 (61.1%) | 26 (89.7%) | 37 (78.7%) |
| ATE-502 | 7 | 1 | 8 |
| ATE-200-phantom | 3 | 1 | 4 |
| Zombie | 0 | 2 | 2 |
| Avg latency (OK) | 36037ms | 57663ms | - |

## Root Cause Analysis

**dsv4p_nv ATE pattern**: 7 real ATE-502 in 6h, all at budget boundary (96043ms, 96030ms, 94038ms, etc.). Log shows SSLEOF errors cycling through keys:

```
k1 SSLEOF (5005ms) → k2 SSLEOF (5005ms) → k3 504 → k4 NVCFPexecTimeout (9397ms) → FASTBREAK → ATE
```

**Budget math**: With KEY_COOLDOWN=8 (R2248), each key attempt costs KEY(8)+UPSTREAM(24)=32s minimum. SSLEOF at ~5s per key adds partial key cost. BUDGET=96s allows only 2.6-3 full key attempts. When 2 keys hit SSLEOF, the remaining budget is too tight for the 3rd/4th key to get a meaningful attempt window.

**Tier attempt data**: 0 tier_attempts for dsv4p_nv in DB — the tier is being pre-empted at budget check before any key attempt is recorded. This is consistent with the budget boundary ATE durations (all exactly at ~96s).

## Optimization

**NVU_TIER_BUDGET_DSV4P_NV: 96 → 102 (+6s)**

Following the KEY↔TIER alternation pattern:
- Last KEY change: R2248 KEY_COOLDOWN 10→8
- Last TIER change: R2217 TIER_COOLDOWN 1→0
- This round: TIER BUDGET direction (DSV4P specific)

**Budget verification**:
- KEY(8) + TIER(0) + DSV4P(102) = 110 << 157 TIER_TIMEOUT_BUDGET (47s margin)
- 102/32 = 3.2 keys → 3 full key attempts with 6s buffer
- Without AUTHFAIL: 102s allows ~4 short key attempts (SSLEOF at 5s each)
- With AUTHFAIL: KEY(8)+AUTHFAIL(60)+UPSTREAM(24)=92s → 102-92=10s ledge for 2nd key

**Impact**: 6s more budget for dsv4p_nv tier. Extra budget allows one more key cycle before exhaustion, reducing ATE rate when SSLEOF errors consume early keys.

**Single parameter. Iron law: only change HM1, never HM2.**

## Verification

- [x] compose file updated (line 658)
- [x] nv_gw restarted (docker compose up -d --force-recreate)
- [x] NVU_TIER_BUDGET_DSV4P_NV=102 confirmed in env
- [x] KEY_COOLDOWN_S=8 unchanged
- [x] Health=200
- [x] Budget safe: KEY(8)+TIER(0)+DSV4P(102)=110 << 157 (47s margin)

## ⏳ 轮到HM1优化HM2