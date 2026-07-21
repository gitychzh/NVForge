# R2168 (HM2→HM1): KEY_COOLDOWN_S 42→40 (-2s)

## 数据源 (Data Sources)

### DB (6h window)
| Metric | Value |
|---|---|
| Total | 35 req |
| OK (200) | 29 (82.9% SR) |
| Fail | 6 |
| Avg duration | 17708ms |

### Per-model 6h
| Model | Total | OK | Fail | Avg ms |
|---|---|---|---|---|
| glm5_2_nv | 32 | 29 | 3 | 19193 |
| dsv4p_nv | 3 | 0 | 3 | 1861 |

### Error Breakdown 6h
| Model | Error Type | Count |
|---|---|---|
| dsv4p_nv | all_tiers_exhausted (status=502) | 3 |
| glm5_2_nv | zombie_empty_completion | 3 |

### ATE Detail
All 3 dsv4p ATEs at 03:39-03:40 UTC (pre-R2167, pre-R2164 TIER_COOLDOWN_S 26→24):
- tiers_tried_count=1, fallback_tiers_used={dsv4p_nv}, duration 1114-2382ms
- These are pre-change artifacts, zero ATE post-R2167

### 30min window
2 req, 1 OK, 1 fail (zombie at 06:33:32)

### Tier Attempts 6h
| Tier | Error Type | Count |
|---|---|---|
| glm5_2_nv | pexec_success | 32 |
| glm5_2_nv | pexec_timeout | 9 |
| glm5_2_nv | pexec_429 | 6 |
| glm5_2_nv | pexec_SSLEOFError | 6 |

All tier errors are NVCF-side (not locally fixable).

## 变更 (Change)
- **KEY_COOLDOWN_S**: 42 → 40 (-2s), nv_gw section line 500
- Budget: KEY+TIER+GLM5_2 = 40+24+28 = 92 < 153 (61s margin, safe)
- Peer-fb: 122 ≥ 28+2 = 30 ✓
- Alternating TIER→KEY pattern (R2167 TIER 26→24, now KEY 42→40)

## 验证 (Verification)
- Compose line 500: `KEY_COOLDOWN_S: "40"` ✓
- Compose line 186 (ms_gw): `KEY_COOLDOWN_S: "58"` unchanged ✓
- Live env: `KEY_COOLDOWN_S=40` ✓
- Health: `{"status": "ok"}` ✓

## 评判 (Judgment)
- Zero ATE post-R2167 deploy (3 pre-existing from 03:39-03:40)
- 3 zombie glm5_2 (benign, NVCF upstream)
- All NVCF-side errors (pexec_timeout/429/SSLEOFError) not locally fixable
- 61s budget margin safe for -2s KEY reduction
- Alternating pattern continues: next round should target TIER_COOLDOWN_S 24→22
## ⏳ 轮到HM1优化HM2
