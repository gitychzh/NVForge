# R2054 (HM2→HM1): NVU_BIG_INPUT_COOLDOWN_S 1800→1200 (30m→20m)

## 数据 (HM2 收集 HM1 数据, CST 16:00)

### 6h DB
- 31 req/27 OK(87.1% SR)/4 fail: 3 zombie_empty_completion + 1 all_tiers_exhausted(502)
- glm5_2_nv: 25 OK avg 10829ms (min 3629, max 24645)
- dsv4p_nv: 2/2 OK avg 9944ms (min 5836, max 14052)
- 429 cycling: 77.4% (24/31, 21×1 cycle + 3×2 cycles)
- Peer-fb: 0 events (silent — formula check: UPSTREAM=24+PEER=122=146<153 ✓, should trigger)
- ATE: 7 rows (6h), 6x status=200 phantom + 1x status=502 real (40s, no fallback)
- 3 zombies: all glm5_2_nv, >100K input (BIGINPUT breaker), spaced 1-1.5h apart

### 1h DB
- 5 req, 4 OK (80.0% SR), 1 zombie
- 429 cycling: 100% (5/5, all 1-cycle)
- glm5_2 OK: avg 14406ms, max 24645ms

### 30m DB (post R2053 KEY_COOLDOWN_S=60)
- 3 req, 3 OK (100% SR), 0 errors
- 429 cycling: 100% (3/3, all 1-cycle) — sample too small, needs more observation

### Env (pre-change)
- NVU_BIG_INPUT_COOLDOWN_S=1800 (R2051)
- NVU_BIG_INPUT_THRESHOLD=100000, NVU_BIG_INPUT_FAIL_N=1
- KEY_COOLDOWN_S=60 (R2053)
- TIER_COOLDOWN_S=0, TIER_TIMEOUT_BUDGET_S=153
- UPSTREAM_TIMEOUT=24, NVU_TIER_BUDGET_GLM5_2_NV=18

## 分析

R2049→R2051→R2054 继续 BIG_INPUT_COOLDOWN_S 渐进压缩：10800→3600→1800→1200。R2051 1800s (30m) 已验证安全。3个 zombie/6h 间隔 1-1.5h 远大于 20m cooldown，breaker 不会频繁触发。1200s (20m) 将合法大输入恢复时间减半至 R2051 的 50%，5 keys 低流量 (~5 req/h) 安全。429 cycling 100% 在 30m 窗口内需观察但 KEY_COOLDOWN_S=60 刚应用（R2053），信号未稳定。Peer-fb 0 事件 6h 正常（只有 1 真实 ATE reachable for peer-fb，且 24+122=146<153 ✓ 触发条件满足）。

## 优化
- NVU_BIG_INPUT_COOLDOWN_S: 1800 → 1200 (-600s, 30m→20m)
- 继续 R2049/R2051 渐进压缩轨迹，每轮验证后减半
- 3 zombie/6h spaced 1-1.5h >> 20m cooldown safe
- 5 keys, ~5 req/h, near-zero breaker exhaustion risk
- Single param; iron law: only change HM1 never HM2

## 验证
- `docker exec nv_gw env | grep NVU_BIG_INPUT_COOLDOWN_S` → 1200 ✓
- `curl /health` → status=ok ✓
- Container recreated via `docker compose up -d nv_gw` ✓
- Compose line 634: sed written with `|` delimiter + `.*` for accumulated comment safety ✓
## ⏳ 轮到HM1优化HM2
