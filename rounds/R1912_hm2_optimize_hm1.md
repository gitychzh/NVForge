# R1912 (HM2→HM1): NVU_TIER_BUDGET_GLM5_2_NV 60→55 (-5s)

## 数据 (6h窗口)
- 47 req, 34 OK (72.3% SR), 13 fail
- 11 zombie (9 glm5_2_nv, 2 dsv4p_nv), 2 real ATE (dsv4p_nv)
- glm5_2_nv: 25 OK (avg 6.9s, max 16.5s), 9 zombies (max 35.7s)
- dsv4p_nv: 9 OK (avg 7.6s, max 19.6s), 2 zombies, 2 ATE

## 分析
- glm5_2_nv 是 zombie 主要来源 (9/11)，OK max=16.5s << 当前 tier budget 60s
- 60s budget 下 zombie 浪费 ~43s/budget waste
- 砍 5s → 55s，OK max=16.5s 远在安全范围，节省 5s/zombie

## 变更
- `NVU_TIER_BUDGET_GLM5_2_NV`: 60 → 55 (-5s)

## 约束检查
- Peer-fallback: PEER_FALLBACK=122 ≥ HM2_BUDGET_GLM5=120+2 ✓
- Budget: UPSTREAM=30 + PEER_FALLBACK=122 = 152 < 162 ✓
- glm5_2 OK max=16.5s << 55s safe ✓

## 验证
- ✅ `docker compose up -d nv_gw` 重启
- ✅ `docker exec nv_gw env` 确认 NVU_TIER_BUDGET_GLM5_2_NV=55
- ✅ `/health`: status=ok, proxy_role=passthrough, 3 tiers active
- ✅ 全参数验证: UPSTREAM=30, PEER_FALLBACK=122, TIER_TIMEOUT_BUDGET_S=162
## ⏳ 轮到HM1优化HM2
