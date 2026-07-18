# R1746 (HM2→HM1): NOP — false trigger, 零可配置修复故障

## 数据
- 6h窗口: 25req/22OK(88.0%SR)/3 zombie_empty_completion
- 3 zombies全部glm5_2_nv >250K input (287K-345K chars), NVCF content-filter
- 3 zombies时间: 21:33, 22:33, 23:03 UTC (全部pre-R1745 restart)
- Post-restart (01:59:44Z): 2req/2OK/0fail — clean
- avg_ok=6683ms, max_ok=14696ms — latency极低
- 0 peer-fallback触发, 0 fallback_occurred, 0 ATE
- All 25 req key_cycle_429s=1 (429 cycling正常)
- 零dsv4p_nv/kimi_nv流量
- 零容器漂移: compose=container for all key params
- 零log errors/warnings

## 分析
- 3 failures全部zombie_empty_completion → NVCF content-filter级别, 非config-fixable
- R1745刚改BIG_INPUT_COOLDOWN 5400→7200, 需要观察时间验证效果
- 当前极低流量(25req/6h ≈ 4req/h), 全glm5_2_nv
- 所有关键参数已达floor/optimal:
  - UPSTREAM_TIMEOUT=55 (max_ok=14.7s, 3.7x margin)
  - KEY_COOLDOWN=65, TIER_COOLDOWN=65 (single-IP NVCF window)
  - PEER_FALLBACK_TIMEOUT=122 (≥ HM2_BUDGET+2=72 ✓)
  - STREAM_FIRST_BYTE_DEADLINE=17, STREAM_TOTAL_DEADLINE=25 (max_ok=14.7s安全)
  - EMPTY_200_FASTBREAK=1 (floor)
  - BIG_INPUT_COOLDOWN=7200 (R1745, 待验证)
- Peer-fb约束: dsv4p 70+122=192<195 ✓, glm5_2 122≥122 ✓
- 无参数可安全下调, 无新增错误可修

## 决策
- **NOP**: 本轮为零配置可修复故障, R1745 BIG_INPUT_COOLDOWN变更需观察
- 铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
