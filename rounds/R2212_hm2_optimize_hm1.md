# R2212: HM2 → HM1 — NVU_TIER_BUDGET_DSV4P_NV 88→94 (+6s)

## Context
- **Date**: 2026-07-22
- **Role**: HM2 optimizing HM1
- **HM1 target**: opc_uname@100.109.153.83:222, container nv_gw (port 40006)
- **Prior round**: R2211 (HM1→HM2) KEY_COOLDOWN_S 64→60

## Data Collected (6h window, 52 total requests)

### Success Rate
- **52 req**, 39 OK (75.0% SR), 13 fail

### Error Breakdown
| Error | Count | Model |
|-------|-------|-------|
| zombie_empty_completion | 9 | glm5_2_nv |
| all_tiers_exhausted (ATE) | 3 | dsv4p_nv |
| zombie_empty_completion | 1 | dsv4p_nv |

### dsv4p ATE Detail
- 3 ATE requests, all with **0 tier_attempts** (pre-empted!)
- tiers_tried_count=1, fallback_tiers_used={dsv4p_nv}
- duration_ms: 48015, 48020, 48020 (~48s timeout)
- Root cause: Budget too tight for key cooldown window

### Key Cycling
- glm5_2_nv: 36/36 requests (100%) with key cycling, max 6 cycles
- dsv4p_nv: 0/16 with key cycling

### Fallback
- 0 fallback usage (peer/ms)

### Latency
- glm5_2_nv OK avg: 22.7s
- Distribution: 0-5s:2, 5-10s:7, 10-20s:8, 20-30s:4, 30s+:6

## Analysis
The dsv4p ATE failures have **zero tier_attempts** — the gateway pre-empts the tier before any key attempt. The budget math:

- `KEY_COOLDOWN_S(60) + UPSTREAM_DEADLINE(24) = 84s` minimum for one key attempt
- Current `NVU_TIER_BUDGET_DSV4P_NV = 88` → only 4s margin
- With timing jitter, lock contention, and overhead, the gateway concludes there's not enough time and pre-empts

## Optimization

**Change**: `NVU_TIER_BUDGET_DSV4P_NV: 88 → 94 (+6s)`

**Budget check**:
- dsv4p key attempt: 60 (KEY_COOLDOWN) + 24 (UPSTREAM) = 84s
- 94 - 84 = 10s margin → safe for one key attempt
- Total tier budget: 94 + 28 (GLM52) + 1 (TIER_COOLDOWN) = 123 << 153 (TIER_TIMEOUT_BUDGET) ✓

**Expected impact**: dsv4p ATE should drop to 0 because the tier now has 10s of margin to attempt at least one key before the budget expires. glm5_2 zombies remain a separate problem (NVCF upstream issue, not configurable).

## Verification
- SSH to HM1, verified compose at line 658
- `docker compose up -d nv_gw` → container restarted, healthy
- `docker exec nv_gw env | grep NVU_TIER_BUDGET_DSV4P_NV` → `94` ✓

## Single param; iron law: only HM1

## ⏳ 轮到HM1优化HM2