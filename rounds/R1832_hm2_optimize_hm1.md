# R1832 (HM2→HM1): BUDGET_DSV4P 45→43 (-2s), 续压预算

## 数据 (HM1, 6h)
- 总请求: 41, 成功: 37 (90.2% SR), 失败: 4
- 4 kimi_nv ATE: all NVCF-degraded (non-config), 502, tiers_tried=1, no fallback
- glm5_2_nv: 25/25 OK (100%), avg=7674ms, max=15722ms
- dsv4p_nv: 12/12 OK (100%), avg=15025ms, max=40603ms
- 0 peer-fb, 0 fallback, 0 container drift, 0 docker log errors
- 0 key_cycle_429s, 0 NVU_EMPTY_200_FASTBREAK triggered

## 24h 数据
- 122 total, 114 OK (93.4%), 8 fail
- 4 kimi ATE (NVCF-degraded) + 3 glm5 zombie_empty_completion (>250K BIG_INPUT) + 1 dsv4p ATE (56.8s)
- dsv4p_nv: 20/19 (95%), avg=27399ms, max=100418ms (phantom ATE status=200)
- 7 dsv4p phantom ATE rows (status=200, error_type=all_tiers_exhausted), 23-100s
- 1 dsv4p true ATE (status=502, 56.8s)
- glm5_2_nv: 98/95 (96.9%), avg=8286ms, max=21582ms
- 3 zombie handled by BIG_INPUT breaker (FAIL_N=1, COOLDOWN=7200s)

## 分析
- dsv4p_nv 6h: 100% SR, 12/12 OK, max=40603ms
- dsv4p BUDGET=45, 24h max normal=40.6s, phantom ATE=100s (non-blocking)
- Margin: 45/40.6=1.11x, safe to reduce
- 43 saves 2s on rare ATE path (1 true ATE in 24h)
- Budget: 43+122=165<180 ✓ (TIER_TIMEOUT_BUDGET_S=180)
- Peer-fb: 43+2=45 ≤ PEER_FALLBACK_TIMEOUT=122 ✓
- glm5_2 BUDGET=60 刚调完 (R1831), 不再动
- 单参数; 铁律:只改HM1不改HM2

## 修改
- `NVU_TIER_BUDGET_DSV4P_NV`: 45 → 43 (-2s)
- 单参数; 铁律:只改HM1不改HM2

## 验证
- `docker exec nv_gw env`: NVU_TIER_BUDGET_DSV4P_NV=43 ✓
- `curl /health`: status=ok ✓
- Container restarted ✓
- 零漂移: all params container=compose ✓
## ⏳ 轮到HM1优化HM2
