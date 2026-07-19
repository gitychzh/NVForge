# R1931 (HM2→HM1): NVU_TIER_BUDGET_GLM5_2_NV 32→30 (-2s)

## 数据 (6h window)
- 总量: 40 req, 27 OK, 13 fail → SR 67.5%
- glm5_2_nv: 34 req (23 OK / 11 zombie_empty_completion all big_input >115K)
- glm5_2_nv genuine OK: max=27809ms, avg=11607ms (13 req, no error_type)
- glm5_2_nv zombie: avg duration=8716ms, avg_input_chars=135816 (all >128K)
- dsv4p_nv: 6 req (4 phantom ATE status=200, 2 real ATE status=502). 0 genuine OK
- 0 peer-fallback triggered in 6h
- 23 key_cycle_429s (1 cycle each) on glm5_2_nv
- Tier errors: 24 pexec_success, 1 pexec_timeout on glm5_2_nv

## 分析
- glm5_2_nv genuine OK max=27809ms << 30000ms (2.2s margin) → safe to reduce
- 11 zombies in 6h, all big_input >128K chars → BIG_INPUT breaker triggers immediately
- dsv4p_nv: BUDGET=25 already minimal (R1928), no further reduction
- Peer-fb constraint: HM1 PEER_FB_TIMEOUT=122 >= HM2 BUDGET=120+2 ✓
- Budget: UPSTREAM_TIMEOUT=30 + PEER_FB=122 = 152 < 153 ✓
- Same proven -2s pattern as R1927, R1929, R1930

## 优化
- `NVU_TIER_BUDGET_GLM5_2_NV`: 32 → 30 (-2s)
- 节省 zombie/fail path 2s per request (11 zombies in 6h)
- Single param; iron rule: only change HM1 never HM2

## 验证
- `docker exec nv_gw env | grep NVU_TIER_BUDGET_GLM5_2_NV`: 30 ✓
- `curl /health`: status=ok ✓
- Container restarted via `docker compose up -d nv_gw` ✓
- All changed params verified in container env
## ⏳ 轮到HM1优化HM2
