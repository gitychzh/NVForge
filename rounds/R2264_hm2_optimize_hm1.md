# R2264 (HM2→HM1): NVU_TIER_BUDGET_GLM5_2_NV 85→100

**Timestamp**: 2026-07-23 01:00 UTC (cron)

## 6h Pre-Optimization Data

### Overall
| Metric | Value |
|--------|-------|
| Total requests | 57 |
| OK (200) | 41 (71.9%) |
| Fail | 16 (28.1%) |
| Avg duration | 40,510ms |

### Per-Model
| Model | Req | OK | Fail | SR% | Avg ms |
|-------|-----|-----|------|-----|--------|
| glm5_2_nv | 43 | 31 | 12 | 72.1% | 39,590 |
| dsv4p_nv | 14 | 10 | 4 | 71.4% | 43,337 |

### Error Breakdown
| Model | Error Type | Status | Count |
|-------|-----------|--------|-------|
| glm5_2_nv | zombie_empty_completion | 502 | 5 |
| glm5_2_nv | all_tiers_exhausted (429) | 429 | 4 |
| dsv4p_nv | all_tiers_exhausted | 502 | 3 |
| glm5_2_nv | all_tiers_exhausted | 502 | 3 |
| dsv4p_nv | zombie_empty_completion | 502 | 1 |

### Key Cycling (429s)
21 key-cycle-429 events on glm5_2_nv in 6h. Budget too tight prevents retry recovery.

## Root Cause Analysis

- **PER_KEY = KEY_COOLDOWN_S(48) + UPSTREAM_TIMEOUT(24) = 72s**
- **Old budget: NVU_TIER_BUDGET_GLM5_2_NV = 85s**
- **Ratio: 85/72 = 1.18** — barely enough for 1 key attempt, zero retry margin
- All ATE events show `tiers_tried_count=1` — key cycling happens but budget expires before second key can complete
- 4 ATE_429 on glm5_2_nv: NVCF rate limits hit → key cycling triggers → budget exhausted → ATE
- 5 zombie 502: NVCF upstream issue, not our parameter problem

## Optimization

**Change**: `NVU_TIER_BUDGET_GLM5_2_NV` 85 → 100

| Parameter | Old | New | Rationale |
|-----------|-----|-----|-----------|
| NVU_TIER_BUDGET_GLM5_2_NV | 85 | 100 | +15s budget enables 1 key cycle retry after 429 |

**New ratio**: 100/72 = 1.39 — allows 1 key cycle retry with 28s margin

**Global budget check**: 48(KEY_COOLDOWN) + 5(TIER_COOLDOWN) + 100(GLM5) = 153 < 192(TIER_TIMEOUT_BUDGET) ✓

## Execution

```bash
# On HM1 (100.109.153.83):
sed -i 's/NVU_TIER_BUDGET_GLM5_2_NV=85/NVU_TIER_BUDGET_GLM5_2_NV=100/' /opt/cc-infra/docker-compose.yml
docker compose -f /opt/cc-infra/docker-compose.yml up -d nv_gw
# Verified: NVU_TIER_BUDGET_GLM5_2_NV=100, container Up and healthy
```

## Expected Impact

- ATE_429 events should decrease (budget now allows key cycling retry before expiry)
- SR should improve from 71.9% toward 80%+
- Zombie 502 unaffected (NVCF upstream issue)
- Iron law: only changed HM1, never HM2

## ⏳ 轮到HM1优化HM2