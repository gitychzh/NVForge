# R2167 (HM2→HM1): TIER_COOLDOWN_S 26→24 (-2s)

## 数据快照 (~14:45 UTC, 2026-07-21)
- **6h窗口**: 35 req / 29 OK / 6 fail → **82.9% SR**
- **3 dsv4p ATE** (all pre-empted, 0 tier_attempts, 03:39-03:40 UTC — pre-R2164)
- **3 glm5_2 zombie_empty_completion** (502)
- **glm5_2 tier**: 32 pexec_success + 9 timeout + 6 429 + 6 SSLEOFError
- **0 fallback occurrences**
- **glm5_2 6h SR**: 29/32=90.6% (29/29 on non-zombie, 3 zombie are NVCF upstream)
- **key_cycle_429s**: 23/32 glm5_2=1 (72%), 3=2, 3=3, 2=4, 1=7 — healthy key rotation
- **30min window**: 1 OK / 1 fail (thin window)

## 参数变更
| 参数 | 旧值 | 新值 | 变化 |
|------|------|------|------|
| `TIER_COOLDOWN_S` | 26 | 24 | -2s |

## 理由
- Following alternating KEY→TIER pattern (R2163: KEY 46→44, R2164: TIER 28→26, R2165: KEY 44→42)
- 3 dsv4p ATE all pre-empted (0 tier_attempts) — reducing TIER_COOLDOWN helps dsv4p recover faster
- KEY+TIER+GLM5_2=42+24+28=94 < 153 BUDGET (59s margin, very safe)
- Conservative 2s reduction; single parameter; iron law: only change HM1

## 容器重启验证
- `docker compose stop nv_gw && docker compose up -d nv_gw` ✓
- `docker exec nv_gw env | grep TIER_COOLDOWN` → `TIER_COOLDOWN_S=24` ✓
- `/health` → `{"status":"ok"}` ✓

## ⏳ 轮到HM1优化HM2