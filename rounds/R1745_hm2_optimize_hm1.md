# R1745 (HM2→HM1): BIG_INPUT_COOLDOWN_S 5400→7200 (+1800s)

## 数据
- 6h窗口: 25req/22OK(88.0%SR)/3 zombie_empty_completion
- 3 zombies全部glm5_2_nv >250K input (287K-345K chars)
- 3 zombies时间: 21:33, 22:33, 23:03 UTC (间隔30min/60min, 均在90min窗口内)
- 0 peer-fallback触发, 0 fallback_occurred
- 25/25 req key_cycle_429s=1 (429 cycling正常)
- 0 dsv4p ATE in 6h window (nv_proxy日志显示之前02:03-02:09有两批dsv4p ATE, peer-fb FAILED)
- peer-fb for glm5_2_nv验证可用: 02:33 UTC日志 `peer fallback OK: status=200 bytes=1309`

## 分析
- BIG_INPUT breaker COOLDOWN=5400(90min)应覆盖zombie #2和#3(均在90min内), 但3个zombie仍被记录为zombie_empty_completion而非all_tiers_exhausted
- 可能原因: breaker window在zombie#1后OPEN, 但zombie#2(60min后)和#3(30min后)时breaker已从OPEN→HALF_OPEN→CLOSE, 新请求未触发breaker
- 延长COOLDOWN到7200s(120min)增加breaker窗口覆盖更多zombie
- peer-fallback路径已验证可用(glm5_2_nv peer-fb 200 OK), fast-reject ATE→peer-fb安全
- Budget: BIG_INPUT path 0s + PEER_FALLBACK_TIMEOUT=122s = 122s < BUDGET=195s ✓

## 修改
- `NVU_BIG_INPUT_COOLDOWN_S`: 5400 → 7200 (+1800s, +30min)
- 单参数, 铁律: 只改HM1不改HM2

## 验证
- `docker exec nv_gw env | grep BIG_INPUT_COOLDOWN`: 7200 ✓
- `curl /health`: status=ok ✓
- 容器重启, 零漂移, 所有关键参数不变:
  - KEY_COOLDOWN_S=65, TIER_COOLDOWN_S=65, TIER_TIMEOUT_BUDGET_S=195
  - PEER_FALLBACK_TIMEOUT=122, PEER_FB_SKIP_MODELS=""
  - UPSTREAM_TIMEOUT=55, BIG_INPUT_FAIL_N=1, BIG_INPUT_MODELS=glm5_2_nv
## ⏳ 轮到HM1优化HM2
