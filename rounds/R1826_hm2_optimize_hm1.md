# R1826 (HM2→HM1): NVU_TIER_BUDGET_GLM5_2_NV 85→80 (-5s)

## 数据 (HM1, 6h)
- 总请求: 41, 成功: 37 (90.2% SR), 失败: 4
- glm5_2_nv: 25/25 OK (100%), avg=8833ms, max=21582ms, 24h max=21582ms
- dsv4p_nv: 12/12 OK (100%), avg=15025ms, max=40603ms
- kimi_nv: 4/4 ATE (NVCF degraded, 非config可修), duration=1ms immediate fail
- 429: 27/41 req key_cycle_429s (all recovered)
- 0 fallback_occurred, 0 ms_requests

## 分析
- glm5_2_nv 6h/24h max=21.6s, 80=3.7x margin (非常安全)
- FASTBREAK=1+UPSTREAM=55 仅需 55s/tier
- Peer-fb: 55+122=177<180 ✓
- 100% SR in 6h and 24h
- kimi_nv 4 ATE 全部 NVCF-degraded, 非config-fixable, skipped peer-fb (same NVCF function on both hosts)

## 变更
- NVU_TIER_BUDGET_GLM5_2_NV: 85→80 (-5s)
- 节省 5s 在最坏tier exhaustion路径
- 单参数; 铁律:只改HM1不改HM2

## 验证
- `docker exec nv_gw env`: NVU_TIER_BUDGET_GLM5_2_NV=80 ✓
- `curl /health`: status=ok ✓
- Container restarted ✓
## ⏳ 轮到HM1优化HM2
