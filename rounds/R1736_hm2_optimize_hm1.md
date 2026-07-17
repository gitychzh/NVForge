# R1736 (HM2→HM1): 部署验证 — R1735 BUDGET=195 零漂移, 无新数据, 无变更

## 6h 数据 (HM1 nv_gw 40006)
- 37 req: 28 OK, 9 fail → **75.7% SR** (全部为 R1735 重启前数据)
- 7 zombie_empty_completion (glm5_2_nv, all >250K chars) → BIG_INPUT breaker working
- 2 dsv4p_nv ATE 502 (69-70s) → pre-R1735, peer-fb skipped: 70+125=195>185
- 3 phantom ATE (status=200, not real failures)
- 0 fallback occurred (pre-R1735, peer-fb not engaged)
- **0 post-R1735 requests** — DB 最新条目 2026-07-17 23:03 UTC, 容器重启后无流量
- 86.5% key_cycle_429s (32/37, 2×2-cycle, 30×1-cycle, 5×0-cycle)

## 优化
- **无变更** (改前必有数据: 零 post-R1735 数据, 无法做出数据驱动的决策)
- R1735 BUDGET=195 部署已验证: dsv4p peer-fb 已启用 (70+125=195≤195)
- 下一轮需要 post-R1735 数据来验证 peer-fb rescue 是否实际工作

## 部署验证
- `docker exec nv_gw env`: TIER_TIMEOUT_BUDGET_S=195 ✓
- `docker logs nv_gw --tail 30`: 正常启动, 无 error ✓
- 零容器漂移: 所有关键参数 compose=container ✓
  - UPSTREAM_TIMEOUT=55, KEY_COOLDOWN=60, TIER_COOLDOWN=60
  - BIG_INPUT_COOLDOWN=5400, BIG_INPUT_FAIL_N=1, EMPTY_200_FASTBREAK=1
  - PEXEC_TIMEOUT_FASTBREAK=1, SSLEOF_RETRY_DELAY=0.5, PEER_FALLBACK_TIMEOUT=125
- HM1 nv_gw 正常运行, 等待流量

## 评判
- 更少报错: 无变更, 等待数据验证 R1735 peer-fb rescue
- 更快请求: 无变更
- 超低延迟: 无变更
- 稳定优先: 遵守铁律, 不在无数据时盲目变更
- 铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
