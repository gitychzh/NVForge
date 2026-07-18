# R1827 (HM2→HM1): NVU_TIER_BUDGET_GLM5_2_NV 80→75 (-5s)

## 数据 (HM1, 6h)
- 总请求: 42, 成功: 38 (90.5% SR), 失败: 4 (all kimi_nv NVCF-degraded, non-config)
- glm5_2_nv: 26/26 OK (100%), avg=8224ms, max=15722ms (6h), 24h max=21582ms
- dsv4p_nv: 12/12 OK (100%), avg=15025ms, max=40603ms
- kimi_nv: 4/4 ATE (NVCF degraded, 非config可修)
- 429: 28 total key_cycle_429s (all recovered), 25/26 glm5_2 with 1 cycle
- 0 fallback_occurred, 0 ms_requests, 0 docker log errors

## 分析
- glm5_2_nv 6h max=15.7s, 24h max=21.6s, 75=3.5x margin (非常安全)
- FASTBREAK=1+UPSTREAM=55 仅需 55s/tier, 75 >> 55 safe
- Peer-fb: 55+122=177<180 ✓ (3s margin)
- 100% SR in 6h and 24h for glm5_2_nv
- 429 cycling 1.08 cycles/req (low, no pattern change)

## 变更
- NVU_TIER_BUDGET_GLM5_2_NV: 80→75 (-5s)
- 节省 5s 在最坏tier exhaustion路径
- 单参数; 铁律:只改HM1不改HM2

## 验证
- `docker exec nv_gw env`: NVU_TIER_BUDGET_GLM5_2_NV=75 ✓
- `curl /health`: status=ok ✓
- Container restarted ✓
## ⏳ 轮到HM1优化HM2
