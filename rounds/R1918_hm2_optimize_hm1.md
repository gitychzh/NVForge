# R1918 (HM2→HM1): NVU_TIER_BUDGET_DSV4P_NV 39→30 (-9s)

## 数据 (6h window, 18:40 UTC)
- 39req/27OK(69.2%SR)/12 fail
- 9 zombie_empty_completion (glm5_2_nv, all >115K chars, BIG_INPUT breaker active)
- 2 real ATE (dsv4p_nv, 2-3ms — tier exhausted on arrival, all keys on cooldown)
- 1 zombie dsv4p_nv
- dsv4p_nv OK: 4/4, avg=8930ms, max=19559ms << 30s safe
- glm5_2_nv OK: 23/23, avg=8508ms, max=27809ms

## 分析
- dsv4p_nv OK max=19559ms — 有10s+余量到30s
- 39→30 每次 zombie/ATE 路径节省 9s
- Budget: UPSTREAM=30 + PEER_FALLBACK=122 = 152 < 153 (1s margin, triggers)
- 单参数对; 铁律:只改HM1不改HM2

## 修改
- `NVU_TIER_BUDGET_DSV4P_NV: "39"` → `"30"` (HM1 /opt/cc-infra/docker-compose.yml line 656)

## 验证
- `docker exec nv_gw env | grep NVU_TIER_BUDGET_DSV4P_NV`: 30 ✓
- `curl /health`: status=ok ✓
- All key env params match compose ✓
## ⏳ 轮到HM1优化HM2
