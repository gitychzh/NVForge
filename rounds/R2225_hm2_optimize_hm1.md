# R2225 — HM2 → HM1 优化

## 数据窗口 (6h, DB NOW=23:56 UTC Jul 21, ~8h 滞后)

| 指标 | 值 |
|------|-----|
| 总请求 | 50 |
| 成功 | 40 (80.0% SR) |
| 失败 | 10 |
| glm5_2 zombie | 7 (avg 8.2s, NVCF upstream) |
| dsv4p ATE | 3 (preempted, 0 tier_attempts, >13h stale, all from Jul 21 18:xx) |
| glm5_2 avg OK | 14.9s |
| dsv4p avg OK | 26.9s |
| 429 cycling | 38/50 (76%), avg 1.0 cycles |
| 30min window | 2 total (1 OK, 1 zombie) |

## 根因分析

- KEY_COOLDOWN_S=40 → 大多数请求经历 1 次 key cycle (429 后等待 40s)
- glm5_2 7 zombies = NVCF 函数级问题，非网关可调
- dsv4p 3 ATE = 全部 >13h 陈旧数据 (pre-R2224)，0 tier_attempts 因预算预判
- KEY=40 在 safe zone (远低于 60s 零-429 阈值但远高于 1-59s anti-pattern 区)

## 修改

**KEY_COOLDOWN_S: 40→38 (-2s)** — 行 500, `/opt/cc-infra/docker-compose.yml`

- 交替 KEY→KEY 模式 (TIER=0, skip)
- 减少 key 429 循环等待 2s，降低请求延迟

## 预算安全

- KEY(38) + TIER(0) + DSV4P(94) = 132 ≤ 157 (25s margin) ✓
- dsv4p min: 38 + 24 = 62 ≤ 94 (32s margin) ✓

## 验证

- `docker compose stop && up -d` 成功，容器已重建
- `docker exec nv_gw env | grep KEY_COOLDOWN_S` → KEY_COOLDOWN_S=38 ✓
- 健康检查: `curl http://localhost:40006/health` → 200 OK
- Compose config 验证通过

## 单参数，铁律：只改 HM1 不改 HM2

## ⏳ 轮到HM1优化HM2