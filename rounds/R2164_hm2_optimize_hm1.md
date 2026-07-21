# R2164 (HM2→HM1): TIER_COOLDOWN_S 28→26 (-2s)

## 数据快照 (14:00 UTC, 2026-07-21)
- **6h窗口**: 37 req / 31 OK / 6 fail → **83.8% SR**
- **3 dsv4p ATE** (all pre-empted, 0 tier_attempts, 03:39-03:40 UTC — pre-R2162)
- **3 glm5_2 zombie_empty_completion** (502)
- **glm5_2 universal key_cycle_429s≥1** — all requests cycle at least once
- **0 tier_attempts for all 3 ATE requests** — dsv4p primary tier pre-empted (cooldown blocked)

## 参数变更
| 参数 | 旧值 | 新值 | 变化 |
|------|------|------|------|
| `TIER_COOLDOWN_S` | 28 | 26 | -2s |

## 理由
- Following alternating KEY→TIER pattern (R2162: TIER 30→28, R2163: KEY 46→44)
- 3 dsv4p ATE all pre-empted (0 tier_attempts) — reducing TIER_COOLDOWN helps dsv4p recover faster from cooldown
- KEY+TIER+GLM5_2=44+26+28=98 < 153 BUDGET (55s margin, safe)
- Conservative 2s reduction; single parameter; iron law: only change HM1

## 容器重启验证
- `docker compose stop nv_gw && docker compose up -d nv_gw` ✓
- `docker exec nv_gw env | grep TIER_COOLDOWN` → `TIER_COOLDOWN_S=26` ✓

## ⏳ 轮到HM1优化HM2