# R2161 (HM2→HM1): KEY_COOLDOWN_S 48→46 (-2s)

## 数据基础 (6h window, 2026-07-21 ~05:03 UTC)

| 指标 | 值 |
|---|---|
| 总请求 | 37 |
| 成功 | 31 (83.8% SR) |
| 失败 | 6 |
| dsv4p ATE | 3 (全部 pre-empted, tiers_tried=1, only dsv4p_nv, 03:39-03:40 UTC pre-R2160) |
| glm5_2 zombie | 3 (empty completions) |
| fallback_occurred | 0 (0 peer-fb, 0 ms_gw) |
| key_cycle_429s=1 | 26/37 (70.3%) |
| key_cycle_429s≥2 | 8/37 (21.6%) |

### glm5_2 tier 分解 (6h)
| error_type | count |
|---|---|
| pexec_success | 34 |
| pexec_timeout | 9 |
| pexec_429 | 6 |
| pexec_SSLEOFError | 5 |

### 30min window
- 2 req, 2 OK (100% SR) — 最近30min零错误

### 最近10条请求
全部 glm5_2_nv: 7 OK (5314-24833ms), 3 dsv4p ATE (03:39-03:40 UTC, pre-R2160)

## 分析

- R2160 修复了 glm5_2 budget 25→28 使 fallback 可以被启用，3 ATE 发生在 03:39-03:40（R2160 部署前）
- 高频 key cycling: 26/37 cycle1, 8/37 cycle2+ — 表明 KEY_COOLDOWN_S=48 仍偏高，低流量下 key 冷却时间超过 inter-request gap
- 交替模式 KEY→TIER→KEY→TIER，R2160 是特殊修复，R2161 回到 KEY↓
- KEY_COOLDOWN_S=46: 继续减少 key 冷却时间，减少 key cycling 频率
- Budget: 46 (KEY) + 30 (TIER) + 28 (GLM5_2) = 104 < 153 (49s margin 安全)
- 铁律: 只改 HM1 不改 HM2

## 改变

`KEY_COOLDOWN_S: "48" → "46"` (-2s)

## 验证

- `sed` 只改 line 500 (nv_gw section)
- `docker compose stop nv_gw && docker compose up -d nv_gw` — 容器名恢复为 `nv_gw`
- `docker exec nv_gw env | grep KEY_COOLDOWN_S` → `KEY_COOLDOWN_S=46` ✓
- `/health` → `{"status": "ok"}` ✓

## ⏳ 轮到HM1优化HM2