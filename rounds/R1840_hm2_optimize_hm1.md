# R1840 (HM2→HM1): TIER_TIMEOUT_BUDGET_S 180→178 (-2s)

## 决策依据 (6h window)
- **总览**: 43 req, 38 OK, 5 fail → **88.4% SR**
- **dsv4p_nv**: 15/15 OK (100%), avg=13896ms, max=40603ms
- **glm5_2_nv**: 24 req, 23 OK (95.8%), avg=7354ms, 1 zombie_empty (NVCF侧)
- **kimi_nv**: 4/4 fail (0%), all ATE ~1ms — NVCF function degraded (非config可修)
- **Error breakdown**: 5 fail (4 kimi ATE=502 + 1 zombie_empty=502)
- **Peer-fb**: 0 triggered (kimi skipped, dsv4p/glm5_2 all healthy)
- **429 cycling**: 26 cycles (0.6/req)

## 分析
- dsv4p_nv 和 glm5_2_nv 健康。5 failures 全部 NVCF 侧不可控 (4 kimi ATE + 1 zombie)
- UPSTREAM_TIMEOUT=51 + PEER_FALLBACK_TIMEOUT=122 = 173 < 178 (5s margin, safe)
- 省2s on ATE failure path, 成功路径不受影响
- 单参数; 铁律:只改HM1不改HM2

## 变更
- **TIER_TIMEOUT_BUDGET_S**: 180→178 (-2s)
- 单参数; 铁律:只改HM1不改HM2

## 验证
- ✅ docker compose up -d nv_gw → Recreated+Started
- ✅ docker exec nv_gw env | grep TIER_TIMEOUT_BUDGET_S → 178
- ✅ curl localhost:40006/health → {"status": "ok"}
- ✅ 无容器漂移
## ⏳ 轮到HM1优化HM2
