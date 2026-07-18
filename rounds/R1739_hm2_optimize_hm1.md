# R1739 (HM2→HM1): PEER_FALLBACK_TIMEOUT 125→124 — dsv4p_nv peer-fb gap micro-fix

## 6h 数据 (HM1 nv_gw 40006)
- 37 req: 29 OK, 8 fail → **78.4% SR** (与R1736/R1737/R1738相同数据, post-R1735重启前)
- 6 zombie_empty_completion (glm5_2_nv, NVCF content-filter, 251K-283K chars, BIG_INPUT breaker working)
- 2 dsv4p_nv ATE 502 (69-70s, pre-R1735)
- 3 phantom ATE (status=200, glm5_2_nv, not real failures)
- 0 fallback occurred (peer-fb skipped)
- 32 key_cycle_429s (single-IP with 5 keys, glm5_2_nv)
- Post-R1735: 仅 2 条 glm5_2_nv (23:33 UTC), 均 200 OK (4.9s, 6.9s)
- Zero dsv4p_nv post-R1735 → 无法验证 peer-fb rescue

## 根因分析: dsv4p_nv ATE peer-fb gap
- dsv4p_nv ATE duration ~70s (Tier budget 60s + overhead)
- PEER_FALLBACK_TIMEOUT=125: 70+125=195 = BUDGET=195 → peer-fb skipped (≥ BUDGET)
- fallback_occurred=false, fallback_tiers_used={dsv4p_nv}, tiers_tried_count=1
- **R1735 BUDGET=195 声称 peer-fb rescue 可用, 但实际因 70+125=195 边界相等被跳过**

## 容器状态
- `docker exec nv_gw env`: 所有关键参数 compose=container ✓
  - TIER_TIMEOUT_BUDGET_S=195, UPSTREAM_TIMEOUT=55, KEY_COOLDOWN=60
  - TIER_COOLDOWN=60, BIG_INPUT_COOLDOWN=5400, BIG_INPUT_FAIL_N=1
  - EMPTY_200_FASTBREAK=1, PEXEC_TIMEOUT_FASTBREAK=1, SSLEOF_RETRY_DELAY=0.5
  - PEER_FALLBACK_TIMEOUT=124 (post-R1739), PEER_FALLBACK_ENABLED=1
  - NVU_TIER_BUDGET_DSV4P_NV=60, NVU_TIER_BUDGET_GLM5_2_NV=120
- Post-R1739 deploy: container healthy ✓
- 零容器漂移: 所有参数与 compose 一致 ✓

## 优化
- **NVU_PEER_FALLBACK_TIMEOUT: 125→124 (-1s)**
- 70+124=194 < 195 (BUDGET) → peer-fb 可被触发
- 约束: PEER_FALLBACK ≥ HM2_BUDGET+2 = 120+2+3=125? 不对, HM2 BUDGET is 120
  - 实际检查: PEER_FALLBACK=124 ≥ 120+2=122 ✓
  - 剩余 2s 为 connect reserve buffer
- 单参数, 最小步长 (-1s), 仅解 peer-fb 边界跳过问题
- 铁律: 只改HM1不改HM2

## 评判
- 更少报错: dsv4p_nv ATE peer-fb 边界 70+125=195=BUDGET 被跳过 → 70+124=194<195 启用 rescue
- 更快请求: 无影响 (仅影响 ATE 失败路径, 成功路径不变)
- 超低延迟: 无影响
- 稳定优先: 最小步长 -1s, 约束 PEER≥HM2_BUDGET+2=122 仍满足 (124≥122)
- 铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2