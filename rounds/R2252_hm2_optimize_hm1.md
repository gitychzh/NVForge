# R2252 (HM2→HM1): KEY_COOLDOWN_S 8→0 (-8s)

## 6h 数据 (HM1)
- Total: 50req/39OK(78.0%SR)/11fail
- dsv4p_nv: 22req/14OK(63.6%SR)/8fail (7 ATE + 1 zombie 18962ms)
- glm5_2_nv: 28req/25OK(89.3%SR)/3fail (2 ATE + 1 zombie 170493ms)
- 7 dsv4p ATE: ALL all_tiers_exhausted with 0 tier_attempts (pre-empted)
- glm5_2_nv: 25/28 req cycle keys, key_cycle_429s 高达 8, 48 pexec_timeout

## 诊断
R2251 将 KEY_AUTHFAIL_COOLDOWN_S 从60降到35后，per-key cost 从92s降到67s。
但 KEY_COOLDOWN_S=8 仍在 429 anti-pattern zone (1-59s)，导致:
- KEY_AUTHFAIL(35) + KEY_COOLDOWN(8) + UPSTREAM(24) = 67s per key
- NVU_TIER_BUDGET_DSV4P_NV=102 → margin 35s (仍紧张)
- 7 dsv4p ATE 全部 0 tier_attempts: 预算耗尽前未尝试任何 key
- glm5_2_nv key_cycle_429s=8: 过度 key cycling

## 修复
- KEY_COOLDOWN_S: 8→0 (-8s) — 消除 nv_gw pexec 路径 key cooldown
- Per-key cost: KEY_AUTHFAIL(35) + UPSTREAM(24) = 59s
- Margin: 102-59=43s (vs 旧 35s, +8s)
- KEY(0) + TIER(0) + DSV4P(102) = 102 << 157 (55s margin)
- 0s 消除 429 anti-pattern: 停止 key cycling 浪费
- FASTBREAK=1: 59s < 102s ✓
- 单参数; 铁律: 只改HM1不改HM2

## 部署
- sed line 500: KEY_COOLDOWN_S: "8" → "0"
- docker compose up -d --force-recreate nv_gw
- container env verified: KEY_COOLDOWN_S=0
- health check: 200 OK

## ⏳ 轮到HM1优化HM2