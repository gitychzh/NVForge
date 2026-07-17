# R1738 (HM2→HM1): NOP — 零 post-R1735 新流量, 待验证 peer-fb rescue, 无变更

## 6h 数据 (HM1 nv_gw 40006)
- 37 req: 29 OK, 8 fail → **78.4% SR** (全部为 R1735 重启前数据, 同 R1736/R1737)
- 6 zombie_empty_completion (glm5_2_nv, BIG_INPUT breaker working, 251K-283K chars)
- 2 dsv4p_nv ATE 502 (69-70s, pre-R1735, peer-fb skipped: 70+125=195>185 at time)
- 3 phantom ATE (status=200, glm5_2_nv, not real failures)
- 0 fallback occurred (pre-R1735 data)
- **Post-R1735 流量**: 仅 2 条 glm5_2_nv (23:33 UTC, 同 R1737), 均 200 OK (4.9s, 6.9s)
- **Zero dsv4p_nv post-R1735** — 无法验证 peer-fb rescue 是否实际工作
- 最新 DB 条目: 2026-07-17 23:33 UTC → ~8h 无流量
- 32 key_cycle_429s (single-IP with 5 keys, glm5_2_nv)

## 容器状态
- `docker exec nv_gw env`: 所有关键参数 compose=container ✓
  - TIER_TIMEOUT_BUDGET_S=195, UPSTREAM_TIMEOUT=55, KEY_COOLDOWN=60
  - TIER_COOLDOWN=60, BIG_INPUT_COOLDOWN=5400, BIG_INPUT_FAIL_N=1
  - EMPTY_200_FASTBREAK=1, PEXEC_TIMEOUT_FASTBREAK=1, SSLEOF_RETRY_DELAY=0.5
  - PEER_FALLBACK_TIMEOUT=125, PEER_FALLBACK_ENABLED=1
  - NVU_TIER_BUDGET_DSV4P_NV=60, NVU_TIER_BUDGET_GLM5_2_NV=120
- `docker logs nv_gw --tail 50`: 正常启动, 零 error/warn ✓
- 零容器漂移: 所有参数与 compose 一致
- 最新日志: 仅 2 条 glm5_2_nv 成功 (23:33 UTC), 之后无新请求

## 当前状态总结
- R1735 BUDGET=195 已部署, peer-fb=125s 可被 dsv4p ATE (70s) 使用
- 零 dsv4p_nv 流量 → peer-fb rescue 路径仍未实际验证
- glm5_2_nv zombie 路径: BIG_INPUT breaker (FAIL_N=1, COOLDOWN=5400) 正常工作
- 铁律:改前必有数据, 零新数据 = 零变更

## 优化
- **无变更** (改前必有数据: 与 R1736/R1737 相同数据, 零 post-R1735 dsv4p 流量)
- 等待 dsv4p_nv 流量产生以验证 R1735 peer-fb rescue 路径

## 评判
- 更少报错: 无变更, 等待数据验证 R1735 peer-fb rescue
- 更快请求: 无变更
- 超低延迟: 无变更
- 稳定优先: 遵守铁律, 不在无数据时盲目变更
- 铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
