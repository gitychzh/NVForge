# R1817 (HM2→HM1): NOP — 九连 false trigger, 全部失败为外部 NVCF 降级, 零可配置修复故障

## 数据 (6h 窗口)
- **总体**: 29req/25OK(86.2%SR)/4 kimi_nv ATE
- **glm5_2_nv**: 24/24 100%SR, avg=10370ms, min=4351ms, max=21582ms
- **dsv4p_nv**: 1/1 100%SR, 2391ms
- **kimi_nv**: 4 ATE, 全部 all_tiers_exhausted, 3×duration=1ms, 1×duration=1715ms

## 错误分析
- 4 kimi_nv ATE: 全部 NVCF function-level degradation
- peer-fb for kimi_nv: peer returned 502 after 13-686ms → 对端HM2同样kimi_nv function degraded
- 0 zombie, 0 SSLEOF, 0 empty_200, 0 fallback, 0 peer-fb 429
- 0 container drift (env vs compose 一致)

## 容器状态
- KEY_COOLDOWN_S=65, TIER_COOLDOWN_S=65 ✓
- UPSTREAM_TIMEOUT=55, TIER_TIMEOUT_BUDGET_S=180 ✓
- PEER_FALLBACK_TIMEOUT=122 ✓
- FASTBREAK=1 (floor) ✓
- SSLEOF_RETRY_DELAY=0.2s ✓
- BIG_INPUT: FAIL_N=1, COOLDOWN=7200 ✓
- glm5_2: BUDGET=105, BIG_INPUT_THRESHOLD=250000 ✓
- dsv4p: BUDGET=45 ✓
- 所有参数 floor/optimal

## 判定
NOP — 九连 false trigger。4 kimi_nv ATE 全部为外部 NVCF function-level degradation，peer-fb 也 502。零 zombie/fallback/peer-fb/429/SSLEOF。零 container drift。所有可配置参数已在 floor 或 optimal。无可配置修复故障。

## 铁律
只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
