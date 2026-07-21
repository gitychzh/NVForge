# R2163 (HM2→HM1): KEY_COOLDOWN_S 46→44 (-2s)

## 改动
- **参数**: `KEY_COOLDOWN_S: 46 → 44` (-2s)
- **位置**: HM1 `/opt/cc-infra/docker-compose.yml` line 500 (nv_gw section)
- **模式**: KEY→TIER交替 (R2162 TIER 30→28, R2163 KEY 46→44)

## 6h 数据 (DB, R2162→R2163)
- **总量**: 37 req / 31 OK (83.8% SR)
- **glm5_2_nv**: 34 req / 31 OK / 3 zombie_empty_completion (00:33, 01:33, 02:33 UTC)
- **dsv4p_nv**: 3 req / 0 OK / 3 all_tiers_exhausted (03:39-03:40 UTC, pre-R2160)
- **30min窗口**: 2/2 OK (100%)
- **最近10条**: 08:33-05:33 全glm5_2_nv 200 OK (avg 5.3-24.8s), 03:39-03:40 2条dsv4p ATE

## 错误分析
- **3 ATE dsv4p_nv**: 全在 03:39-03:40 UTC (pre-R2160)，tiers_tried=1, fallback_tiers_used={dsv4p_nv}。NVCF function 74f02205 持续挂，非nv_gw旋钮能修
- **3 zombie glm5_2**: 00:33 (6314ms), 01:33 (13859ms), 02:33 (10297ms)。已知良性类，pexec_success→empty-200 模式
- **0 peer-fallback**: 24+122=146<153 ✓ (peer-fb trigger condition met)
- **0 fallback events**: 无下游ms_gw或peer-fb触发

## glm5_2 tier layer
- 34 pexec_success, 9 timeout, 6 pexec_429, 5 SSLEOFError
- key_cycle_429s: 26次1循环, 8次≥2循环 (100% universal key-cycle pattern)
- 低流量(5.7req/h) + KEY_COOLDOWN=46 → 第一个key永久在冷却，always cycle到key2

## 预算验证
- KEY+TIER+GLM5_2 = 44+28+28 = 100 < 153 BUDGET (53s margin) ✓
- Peer-fb: UPSTREAM(24) + PEER_FALLBACK(122) = 146 < 153 (7s margin) ✓
- dsv4p ATE tier: 48s budget + 122s peer-fb = 170 > 153 (capped, peer-fb gets 153-48=105s > 72s HM2 budget ✓)

## 重启验证
- `docker compose stop nv_gw && docker compose up -d nv_gw` ✓
- Live env: `KEY_COOLDOWN_S=44` ✓
- Health: `{"status":"ok"}` ✓
- 其他参数无漂移: TIER_COOLDOWN_S=28, TIER_TIMEOUT_BUDGET_S=153, UPSTREAM_TIMEOUT=24, NVU_TIER_BUDGET_GLM5_2_NV=28, NVU_TIER_BUDGET_DSV4P_NV=48 ✓

## 评判
- 少改: 单参数 -2s，多轮积累
- 更快请求: 降低key间冷却2s，减少key轮转等待(universal key-cycle下每req多等2s消除)
- 超低延迟: 成功路径延迟无影响(冷却只在key耗尽时触发)
- 稳定优先: 44+28+28=100 << 153 BUDGET，53s安全边际
- 铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
