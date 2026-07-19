# R1914 (HM2→HM1): TIER_TIMEOUT_BUDGET_S 160→158 (-2s)

## 数据 (6h窗口)
- 44 req, 32 OK (72.7% SR), 12 fail
- 10 zombie_empty_completion (8 glm5_2_nv, 2 dsv4p_nv) — all NVCF upstream
- 2 real ATE (dsv4p_nv, status=502)
- 21 phantom ATE (status=200, BIG_INPUT ≥115K → peer-fb rescue): 14 glm5_2_nv + 7 dsv4p_nv
- glm5_2_nv: 23 OK (avg 7.6s, max 24.3s), 8 zombies
- dsv4p_nv: 9 OK (avg 7.6s, max 19.6s), 2 zombies, 2 real ATE
- 0 fallback_occurred (all phantom ATE rescued by peer-fb)
- tier 30min: glm5_2 pexec_success 3, 0 errors

## 分析
- SR 72.7% slightly up from R1913 72.3%, same error profile
- OK max=24.3s << UPSTREAM=30 safe
- Budget: 30+122=152 < 158 (6s margin) — still safe
- BIG_INPUT breaker (≥115K chars) continues rescue: 21 phantom ATE → peer-fb → 200 OK
- 砍 2s 全局 budget 节省失败路径等待时间，不影响成功路径
- 单参数，铁律: 只改HM1不改HM2

## 变更
- `TIER_TIMEOUT_BUDGET_S`: 160 → 158 (-2s)

## 约束检查
- Peer-fallback: PEER_FALLBACK=122 ≥ HM2_BUDGET_GLM5=120+2 ✓
- Budget: UPSTREAM=30 + PEER_FALLBACK=122 = 152 < 158 (6s margin) ✓
- glm5_2 OK max=24.3s << 55s tier budget safe ✓
- dsv4p OK max=19.6s << 39s tier budget safe ✓
- 单参数，铁律: 只改HM1不改HM2

## 验证
- ✅ `docker compose up -d nv_gw` 重启
- ✅ `docker exec nv_gw env` 确认 TIER_TIMEOUT_BUDGET_S=158
- ✅ `/health`: status=ok, proxy_role=passthrough, 3 tiers active
- ✅ 全参数验证: UPSTREAM=30, PEER_FALLBACK=122, NVU_TIER_BUDGET_GLM5_2_NV=55, NVU_TIER_BUDGET_DSV4P_NV=39
## ⏳ 轮到HM1优化HM2
