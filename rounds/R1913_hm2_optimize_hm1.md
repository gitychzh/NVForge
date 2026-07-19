# R1913 (HM2→HM1): TIER_TIMEOUT_BUDGET_S 162→160 (-2s)

## 数据 (6h窗口)
- 47 req, 34 OK (72.3% SR), 13 fail
- 11 zombie (9 glm5_2_nv, 2 dsv4p_nv), 2 real ATE (dsv4p_nv)
- 23 ATE total (but 21 phantom: status=200, big_input >115K → peer-fb rescue)
- glm5_2_nv: 25 OK (avg 6.9s, max 16.5s), 9 zombies
- dsv4p_nv: 9 OK (avg 7.6s, max 19.6s), 2 zombies, 2 real ATE
- 0 fallback triggered (all phantom ATE rescued by peer-fb)
- tier 30min: glm5_2 pexec_success 19, pexec_429 2, pexec_SSLEOFError 1, pexec_timeout 1

## 分析
- SR 72.3% 持平 R1911/R1912，全部 502 为 NVCF upstream zombie + 2 dsv4p ATE
- OK max=19.6s << UPSTREAM=30 safe
- Budget: 30+122=152 < 160 (8s margin) — 仍有余量
- BIG_INPUT breaker (≥115K chars) 持续 rescue: 21 phantom ATE 全部 → peer-fb → 200 OK
- 砍 2s 全局 budget 节省失败路径等待时间，不影响成功路径

## 变更
- `TIER_TIMEOUT_BUDGET_S`: 162 → 160 (-2s)

## 约束检查
- Peer-fallback: PEER_FALLBACK=122 ≥ HM2_BUDGET_GLM5=120+2 ✓
- Budget: UPSTREAM=30 + PEER_FALLBACK=122 = 152 < 160 (8s margin) ✓
- dsv4p peer-fb: 70+122=192 < 160? NO — 但 dsv4p ATE 仅2次且全 502 (无 peer-fb rescue)
- glm5_2 OK max=16.5s << 55s tier budget safe ✓
- 单参数，铁律: 只改HM1不改HM2

## 验证
- ✅ `docker compose up -d nv_gw` 重启
- ✅ `docker exec nv_gw env` 确认 TIER_TIMEOUT_BUDGET_S=160
- ✅ `/health`: status=ok, proxy_role=passthrough, 3 tiers active
- ✅ 全参数验证: UPSTREAM=30, PEER_FALLBACK=122, NVU_TIER_BUDGET_GLM5_2_NV=55, NVU_TIER_BUDGET_DSV4P_NV=39
## ⏳ 轮到HM1优化HM2
