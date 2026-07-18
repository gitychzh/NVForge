# R1829 (HM2→HM1): NVU_TIER_BUDGET_GLM5_2_NV 70→65 (-5s)

## 数据 (HM1, 6h)
- 总请求: 41, 成功: 37 (90.2% SR), 失败: 4 (all kimi_nv ATE, NVCF-degraded, non-config)
- glm5_2_nv: 25/25 OK (100%), avg=8195ms, max=15722ms (6h), 24h max=21582ms
- dsv4p_nv: 12/12 OK (100%), avg=15025ms, max=40603ms
- 24h: 122 total, 114 OK (93.4%), 8 fail (4 kimi ATE + 3 glm5 zombie + 1 dsv4p ATE)
- 429: 27 key_cycle_429s (all recovered), 24/25 glm5_2 with 1 cycle
- 0 fallback_occurred, 0 docker log errors, 0 peer-fb triggered

## 分析
- glm5_2_nv 6h max=15.7s, 24h max=21.6s, 65=3.0x margin (安全)
- FASTBREAK=1+UPSTREAM=55 仅需 55s/tier, 65 >> 55 safe
- Peer-fb: 55+122=177<180 ✓ (3s margin)
- 6h 100% SR for glm5_2_nv, continued trajectory from R1825→R1826→R1827→R1828
- 429 cycling 1.08 cycles/req (low, no pattern change)
- 0 errors in logs, clean state

## 变更
- NVU_TIER_BUDGET_GLM5_2_NV: 70→65 (-5s)
- 节省 5s 在最坏tier exhaustion路径
- 单参数; 铁律:只改HM1不改HM2
- Trajectory: R1825(80)→R1826(80, no change)→R1827(75)→R1828(70)→R1829(65)

## 验证
- `docker exec nv_gw env`: NVU_TIER_BUDGET_GLM5_2_NV=65 ✓
- `curl /health`: status=ok ✓
- Container restarted ✓
## ⏳ 轮到HM1优化HM2
