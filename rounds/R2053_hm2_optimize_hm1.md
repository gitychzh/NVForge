# R2053 (HM2→HM1): KEY_COOLDOWN_S 0→60 (+60s). 429-cycling 76.67% anti-pattern zone fix.

## 数据 (HM2 收集 HM1 数据, CST 15:50)

### 6h DB
- 30req/25OK(83.3% SR)/5 fail: 4 zombie_empty_completion + 1 all_tiers_exhausted(502)
- glm5_2_nv: 23/23 OK avg 10408ms (min 3629, max 18388)
- dsv4p_nv: 2/2 OK avg 9944ms (min 5836, max 14052)
- 429 cycling: **76.67%** (23/30) — 反模式区
- 30min: 2req/1OK(50.0% SR) — 429 cycling 100% (2/2)
- fallback: 0 (all direct)
- ATE: 7 rows (6h), 6x status=200 phantom + 1x status=502 real

### Env
- KEY_COOLDOWN_S=0 (pre)
- TIER_COOLDOWN_S=0
- TIER_TIMEOUT_BUDGET_S=153
- UPSTREAM_TIMEOUT=24
- NVU_TIER_BUDGET_GLM5_2_NV=18
- NVU_TIER_BUDGET_DSV4P_NV=20
- KEY_AUTHFAIL_COOLDOWN_S=60

## 分析
429 cycling 76.67% with KEY_COOLDOWN_S=0: keys are cycling too fast (<1s cooldown) and re-entering the pool while still hot from NVCF rate limits. The 429-cycling-anti-pattern reference confirms: 0s is the "fast cycle" variant that works for high-traffic pools, but with only 5 keys at ~5 req/h, 0s causes repeated hot-key collisions. The fix per the anti-pattern doc: jump to KEY_COOLDOWN_S=60s (NVCF rate-limit window boundary), letting keys fully cool before re-entering rotation.

## 优化
- KEY_COOLDOWN_S: 0 → 60 (+60s)
- Budget: 60 + 0 = 60 << 153 (93s margin)
- 5 keys, ~5 req/h, near-zero key exhaustion risk
- NV_INTEGRATE_KEY_COOLDOWN_S=0 unchanged (integrate path has separate cooldown)
- Single param; iron law: only change HM1 never HM2

## 验证
- `docker exec nv_gw env | grep KEY_COOLDOWN_S` → 60 ✓
- `curl /health` → status=ok ✓
- Container recreated via `docker compose up -d nv_gw` ✓
## ⏳ 轮到HM1优化HM2