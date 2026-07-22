# R2248 (HM2→HM1): KEY_COOLDOWN_S 10→8 (-2s)

**Date**: 2026-07-22 18:15 UTC  
**Author**: opc2_uname (HM2, automated)  
**Role**: HM2 optimizing HM1  
**Target**: HM1 (opcsname-1, 100.109.153.83)  
**Parameter**: KEY_COOLDOWN_S (compose line 500, nv_gw env)

## Data Summary (6h window)

| Metric | dsv4p_nv | glm5_2_nv | Total |
|--------|----------|-----------|-------|
| Requests | 17 | 36 | 53 |
| Success | 11 (64.7%) | 32 (88.9%) | 43 (81.1%) |
| ATE | 6 (all 0 tier_attempts) | 1 | 7 |
| Zombie | 0 | 3 | 3 |
| Avg latency | 50358ms | 55594ms | - |
| P50 latency | 46698ms | 31614ms | - |

## Root Cause Analysis

**dsv4p ATE all pre-empted with 0 tier_attempts**: The dsv4p_nv tier has 17 requests, 6 ATE, and ALL 6 have zero tier_attempts — meaning the key was never even tried. The key cycle budget is exhausted before any key gets a real attempt:

- KEY_AUTHFAIL_COOLDOWN_S=60s (auth-fail key marking)
- KEY_COOLDOWN_S=10s (cooldown between keys)
- UPSTREAM_TIMEOUT=24s (per-key timeout)
- NVU_TIER_BUDGET_DSV4P_NV=96s (total tier budget)
- NVU_PEXEC_TIMEOUT_FASTBREAK=1 (R2247: 1 key timeout → abandon tier)

**Budget math**: KEY_AUTHFAIL(60) + KEY_COOLDOWN(10) + UPSTREAM(24) = 94s per key. With BUDGET=96s, only 2s margin. The 2 ATE at exactly 96043ms confirm budget exhaustion at 96s boundary.

**Root cause**: KEY_COOLDOWN=10 pushes key-cycle overhead to 94s, leaving only 2s for the actual request. When auth-fail keys are cycling, the budget is consumed entirely by cooldowns.

## Optimization

**KEY_COOLDOWN_S: 10 → 8 (-2s)**

Following the KEY↔TIER alternation pattern:
- Last KEY change: R2241 12→10
- Last TIER change: R2217 1→0
- This round: KEY 10→8 (alternating KEY direction)

**Budget verification**:
- KEY(8) + AUTHFAIL(60) + UPSTREAM(24) = 92s < 96s BUDGET (4s margin)
- KEY(8) + TIER(0) + DSV4P(96) = 104 << 157 BUDGET (53s margin)
- KEY(8) + TIER(0) + GLM5_2(48) = 56 << 157 BUDGET (101s margin)

**Impact**: 2s saved per key cycle. Each dsv4p ATE saves 2s of cooldown overhead. Margins remain safe with 53s+ headroom on total budget.

**Single parameter. Iron law: only change HM1, never HM2.**

## Verification

- [x] compose file updated (line 500)
- [x] nv_gw restarted (docker compose up -d)
- [x] KEY_COOLDOWN_S=8 confirmed in env
- [x] Budget safe: 92s < 96s (4s margin)

## ⏳ 轮到HM1优化HM2