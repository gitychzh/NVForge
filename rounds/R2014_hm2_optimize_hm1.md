# R2014 (HM2→HM1): UPSTREAM_TIMEOUT 30→28 (-2s)

## 数据摘要 (HM1, 2026-07-20 09:05 UTC)

| 指标 | 6h | 30min |
|------|-----|-------|
| 请求总数 | 32 | 2 |
| 成功 | 29 (90.63%) | 2 (100.00%) |
| 失败 | 3 (9.38%) | 0 (0.00%) |
| dsv4p_nv | 0 (6h) / 25 (24h) | 0 |

## 错误分布 (6h)

| 错误类型 | 数量 | 详情 |
|----------|------|------|
| zombie_empty_completion | 3 | status=502, duration 3.4-4.9s, NVCF content_filter (glm5_2_nv) |
| phantom ATE (status=200) | 21 | 非真实失败, 网关已交付200 |

## 日志 (最近100行)

仅有2条 ATTEMPT 日志: `09:03:20 k5 timeout=20s`, `09:03:25 k1 timeout=20s` — 正常 pexec 请求, 无 error/warn。

## 关键参数 (HM1 live env)

- UPSTREAM_TIMEOUT=30 → **28** (本轮)
- TIER_TIMEOUT_BUDGET_S=153
- NVU_TIER_BUDGET_GLM5_2_NV=20
- NVU_TIER_BUDGET_DSV4P_NV=20
- NVU_PEER_FALLBACK_TIMEOUT=122
- KEY_COOLDOWN_S=62
- PEER_FB_SKIP_MODELS=kimi_nv

## 优化决策

**参数**: UPSTREAM_TIMEOUT 30→28 (-2s)

**依据**:
- glm5_2_nv 单key OK max=7.0s << 28s (21s headroom, 安全)
- dsv4p_nv 24h内单key P95最大21.3s << 28s (K3 outlier 33.3s但仅2req/24h微不足道)
- PB约束改善: 28+122=150 < 153 (3s margin, 比原来的 30+122=152<153 仅1s更安全)
- 0 peer-fb 事件, 0 429s, 0 key_cycle_429s — 全链路健康
- 节约 2s: 每个per-key超时路径缩短 2s

**PB 约束检查**:
- UPSTREAM=28 + PEER=122 = 150 < BUDGET=153 ✓ (3s margin, strict <)
- 比 R2013 的 152<153 (1s) 更安全

**铁律**: 只改HM1不改HM2 ✓

## 验证

- compose 写入: `UPSTREAM_TIMEOUT: "28"` ✓
- docker compose up -d nv_gw: recreated+started ✓
- 容器 env: `UPSTREAM_TIMEOUT=28` ✓
- /health: `{"status": "ok"}` ✓
## ⏳ 轮到HM1优化HM2
