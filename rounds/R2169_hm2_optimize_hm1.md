# R2169 (HM2→HM1): TIER_COOLDOWN_S 24→22 (-2s)

## 改前数据 (HM1, 2026-07-21 15:05 UTC)

### 6h Window (09:05–15:05 UTC)
| Model | Total | OK | Fail | SR | Avg Lat |
|-------|-------|-----|------|------|---------|
| dsv4p_nv | 3 | 0 | 3 | 0% | 1861ms |
| glm5_2_nv | 30 | 27 | 3 | 90.0% | 20468ms |
| **Total** | **33** | **27** | **6** | **81.8%** |

### 6h Error Breakdown
- `all_tiers_exhausted` (dsv4p_nv): 3 — all from 03:39-03:40 UTC, **pre-R2168**. Zero tier_attempts = pre-empted (TIER_COOLDOWN_S=24 blocking at that time). Post-R2168: 0 ATE.
- `zombie_empty_completion` (glm5_2_nv): 3 — one at 06:33, two earlier. NVCF empty-200 issue, not tier-cooldown related.

### Post-R2167 (2h Window, 13:05–15:05 UTC)
| Model | Total | OK | Fail | SR |
|-------|-------|-----|------|-----|
| glm5_2_nv | 8 | 7 | 1 | 87.5% |

1 zombie only. Zero ATE since R2168 deploy.

### glm5_2_nv Per-Key (6h)
| Key | Total | OK | Avg ms | P50 ms |
|-----|-------|-----|--------|--------|
| K0 | 8 | 6 | 11254 | 11284 |
| K1 | 7 | 7 | 15076 | 16471 |
| K2 | 4 | 4 | 23008 | 12310 |
| K3 | 5 | 5 | 50181 | 11191 |
| K4 | 6 | 5 | 12591 | 11458 |

K3 has 1 outlier (50s avg from one very slow request), all keys healthy.

### Config at Start
| Param | Value |
|-------|-------|
| KEY_COOLDOWN_S | 40 |
| TIER_COOLDOWN_S | 24 |
| NVU_TIER_BUDGET_GLM5_2_NV | 28 |
| TIER_TIMEOUT_BUDGET_S | 153 |
| UPSTREAM_TIMEOUT | 24 |
| NVU_EMPTY_200_FASTBREAK | 1 |

Budget: KEY + TIER + GLM5_2 = 40 + 22 + 28 = 90 < 153 (63s margin) ✓

## 优化决策

**TIER_COOLDOWN_S 24→22 (-2s)**

Rationale:
- Alternating KEY→TIER pattern: R2168 reduced KEY 42→40, this round targets TIER
- 3 dsv4p ATE were all pre-R2168 (03:39-03:40 UTC), confirmed zero tier_attempts = pre-emption from old TIER_COOLDOWN=24. Post-R2168: 0 ATE.
- zombie_empty_completion is NVCF platform issue, not tier-cooldown related
- 2s reduction is conservative, 90 < 153 budget margin healthy
- TIER_COOLDOWN_S below 20s risks NVCF function-level rate limiting; 22s is still safe

## 验证

- Compose line 506: `TIER_COOLDOWN_S: "22"`
- Live env: `TIER_COOLDOWN_S=22` ✓
- Health: `{"status": "ok"}` ✓
- Container restarted successfully

## 铁律
- [x] 只改HM1不改HM2
- [x] 改前必有数据
- [x] 改后必有验证
- [x] 单参数每轮
- [x] 写入仓库

## ⏳ 轮到HM1优化HM2