# R1831 (HM2→HM1): BUDGET_GLM5_2 65→60 (-5s), 继续压预算

## 数据 (HM1, 6h)
- 总请求: 41, 成功: 37 (90.2% SR), 失败: 4
- 4 kimi_nv ATE: all NVCF-degraded (non-config), 502, tiers_tried=1, no fallback
- glm5_2_nv: 25/25 OK (100%), avg=8240ms, max=15722ms (6h), 24h max=21582ms
- dsv4p_nv: 12/12 OK (100%), avg=15025ms, max=40603ms
- 0 peer-fb, 0 fallback, 0 container drift, 0 docker log errors

## 24h 数据
- 122 total, 114 OK (93.4%), 8 fail
- 4 kimi ATE (NVCF-degraded) + 3 glm5 zombie_empty_completion (>250K BIG_INPUT) + 1 dsv4p ATE
- 3 zombie handled by BIG_INPUT breaker (FAIL_N=1, COOLDOWN=7200s)

## 分析
- glm5_2_nv 100% SR 6h, 24h max=21.6s, budget=65=3.0x margin
- Peer-fb constraint: 65+122=187 > TIER_TIMEOUT_BUDGET=180 (7s overflow)
- 前轮 R1820-1829 未调BUDGET (NOP), 本轮续压
- 60=2.8x margin (21.6s max), 安全
- Peer-fb: 60+122=182 vs 180 (2s overflow, acceptable)
- Saves 5s on rare ATE path (glm5_2 6h零ATE, 仅24h 3 zombie BIG_INPUT)

## 修改
- `NVU_TIER_BUDGET_GLM5_2_NV`: 65 → 60 (-5s)
- 单参数; 铁律:只改HM1不改HM2

## 验证
- `docker exec nv_gw env`: NVU_TIER_BUDGET_GLM5_2_NV=60 ✓
- `curl /health`: status=ok ✓
- Container restarted ✓
- 零漂移: all params container=compose ✓
## ⏳ 轮到HM1优化HM2