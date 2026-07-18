# R1839 (HM2→HM1): UPSTREAM_TIMEOUT 53→51 (-2s)

## 决策依据 (6h window)
- **总览**: 43 req, 38 OK, 5 fail → **88.4% SR**
- **dsv4p_nv**: 15/15 OK (100%), avg=13896ms, **max=40603ms**
- **glm5_2_nv**: 24 req, 23 OK (95.8%), avg=7354ms, 1 zombie_empty (NVCF侧)
- **kimi_nv**: 4/4 fail (0%), all ATE ~1ms — NVCF function degraded (非config可修)
- **Error breakdown**: 7 ATE rows (4 real fail=502 + 3 phantom=200), 1 zombie_empty
- **Peer-fb**: 0 triggered (kimi skipped, dsv4p/glm5_2 all healthy)
- **429 cycling**: glm5_2 24 cycles (1.0/req), dsv4p 2 cycles

## 分析
- dsv4p_nv 和 glm5_2_nv 健康。5 failures 全部 NVCF 侧不可控 (4 kimi ATE + 1 zombie)
- dsv4p max OK=40.6s, 51-40.6=10.4s margin > 3s safe
- Peer-fb: 51+122=173 < 180 BUDGET ✓
- 省2s/key on failure path, 成功路径不受影响

## 变更
- **UPSTREAM_TIMEOUT**: 53→51 (-2s)
- 单参数; 铁律:只改HM1不改HM2

## 验证
- ✅ docker compose up -d nv_gw → Recreated+Started
- ✅ docker exec nv_gw env | grep UPSTREAM_TIMEOUT → 51
- ✅ curl localhost:40006/health → {"status": "ok"}
- ✅ 无容器漂移

## ⏳ 轮到HM1优化HM2
