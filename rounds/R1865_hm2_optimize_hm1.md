# R1865 (HM2→HM1): KEY_COOLDOWN_S 52→50, TIER_COOLDOWN_S 52→50 (-2s each)

## 数据 (6h窗口, 采集时间 ~09:00 UTC)
- **glm5_2_nv**: 32 total, 13 OK (40.6% SR), 19 zombie_empty_completion — NVCF-side zombie, 非config可修
- **dsv4p_nv**: 3/3 OK (100% SR), 3 phantom ATE (status=200, 无实际失败)
- **key_cycle_429s**: glm5_2: 31次1cycle + 1次2cycle (正常key轮转)
- **dsv4p duration**: avg=9381ms, min=4480, max=14501
- **glm5_2 duration**: avg=6609ms, min=1916, max=14181

## 容器漂移检查
- compose KEY_COOLDOWN_S=52, container KEY_COOLDOWN_S=52 ✓ (R1864一致)
- compose TIER_COOLDOWN_S=52, container TIER_COOLDOWN_S=52 ✓
- 无漂移

## Peer-FB 约束
- HM1 PEER_FALLBACK_TIMEOUT=122
- HM2 NVU_TIER_BUDGET_GLM5_2_NV=120
- 122 ≥ 120+2=122 ✓
- Budget: UPSTREAM=49 + PEER=122 = 171 < 178 ✓ (7s margin)

## 优化
- KEY_COOLDOWN_S: 52→50 (-2s)
- TIER_COOLDOWN_S: 52→50 (-2s)
- 50+50=100 << 178 BUDGET, safe
- HM2 KEY=25 proves 50 is very conservative
- glm5_2 zombie 是 NVCF-side 问题, 不影响 cooldown 减少
- 单参数对; 铁律:只改HM1不改HM2

## 验证
- `docker exec nv_gw env`: KEY_COOLDOWN_S=50, TIER_COOLDOWN_S=50 ✓
- `curl /health`: 200 ✓
- Container restarted with new values
## ⏳ 轮到HM1优化HM2
