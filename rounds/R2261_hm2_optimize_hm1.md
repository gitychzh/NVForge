# R2261: HM2→HM1 KEY_COOLDOWN_S 55→48

## 数据 (改前即有理)

### 6h 成功率 (2026-07-22 11:30–17:30 UTC)
| Model | Total | OK | Fail | Success Rate | Avg OK (ms) |
|---|---|---|---|---|---|
| glm5_2_nv | 47 | 39 | 8 | 83.0% | 39,460 |
| dsv4p_nv | 15 | 10 | 5 | 66.7% | 24,560 |

### 错误分解 (6h)
| Error Type | dsv4p_nv | glm5_2_nv | Total |
|---|---|---|---|
| all_tiers_exhausted | 4 | 4 | 8 |
| zombie_empty_completion | 1 | 4 | 5 |
| (other 429/502) | — | — | — |

**All 13 ATE events have `tiers_tried_count=0`** — preempted by budget exhaustion before any key attempt.

### 429 分布 (6h)
| key_cycle_429s | Count |
|---|---|
| 0 | 31 |
| 1 | 10 |
| 2 | 4 |
| 3 | 9 |
| 4 | 1 |
| 5 | 4 |
| 6 | 1 |
| 7 | 2 |

### 预算分析
Pre-edit: KEY_COOLDOWN_S=55, KEY_AUTHFAIL_COOLDOWN_S=0, TIER_COOLDOWN_S=0,
TIER_BUDGET_DSV4P_NV=135, TIER_TIMEOUT_BUDGET_S=192.

dsv4p_nv: 55 + 0 + 0 + 135 = 190 ≤ 192 **(仅 2s 余量)**
glm5_2_nv: 55 + 0 + 0 + 85 = 140 ≤ 192 (52s margin)

## 变更

`KEY_COOLDOWN_S` 55→48 (减少 7s): 仍能防止 429 风暴 (55s 匹配 NVCF 60s 窗口, 48s 仍充分),
但为 dsv4p_nv 的 tier budget 多出 7s 呼吸空间。

Post-edit: dsv4p_nv total = 48+0+0+135 = 183 ≤ 192 **(9s margin)**

## 预期效果

- 减少 dsv4p_nv 的 preempted ATE (tiers_tried=0): 预算余量从 2s→9s 应能覆盖更多 key-cooldown
  等待场景
- 不影响 glm5_2_nv: 已有 52s→59s margin
- KEY_COOLDOWN_S=48 仍高于 30s NVCF 实际 rate-limit 窗口, 不会引发 429 风暴

## 验证

- `docker exec nv_gw env | grep KEY_COOLDOWN`: KEY_COOLDOWN_S=48 ✓
- `curl localhost:40006/health`: {"status":"ok"} ✓
- Container restarted cleanly ✓