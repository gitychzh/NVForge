# R1897 (HM2→HM1): TIER_TIMEOUT_BUDGET_S 178→176 (-2s)

## 数据
- 6h: 46req/25OK(54.3%SR)/21 zombie_empty_completion 全部 glm5_2 NVCF function-level empty200
- dsv4p_nv: 7/7 OK avg=9057ms, max=19559ms
- glm5_2_nv: 18/25 OK(72%), avg=7122ms, 21 zombie all empty200
- 0 peer-fb triggered, 0 ATE, 0 timeout, 0 key_cycle_429s
- 日志: 0 error/warn/fail (docker logs nv_gw --tail 200 零错误)

## 分析
- 所有失败是 glm5_2 NVCF function-level empty200 (NVCF侧劣化), 非本地配置可修
- dsv4p_nv 完全健康 7/7 100% OK
- 当前 BUDGET=178, UPSTREAM=36+PEER=122=158 < 178 余量 20s
- 成功请求 max=19559ms (dsv4p), glm5_2 OK max=13304ms, 远小于 BUDGET

## 变更
- `TIER_TIMEOUT_BUDGET_S`: 178→176 (-2s)
- 预算约束: UPSTREAM(36) + PEER_FB(122) = 158 < 176 (18s margin) ✓
- 成功路径安全: max=19559ms << 176s ✓
- 单参数，铁律:只改HM1不改HM2

## 验证
- docker exec nv_gw env: TIER_TIMEOUT_BUDGET_S=176 ✓
- curl /health: status=ok ✓
- 容器重启确认无漂移
## ⏳ 轮到HM1优化HM2
