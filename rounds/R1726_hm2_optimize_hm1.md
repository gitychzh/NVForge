# R1726 — HM2优化HM1: BIG_INPUT_COOLDOWN_S 2400→3600 (+1200s)

## 数据采集 (HM1)
- **6h窗口**: 60req/51OK(85.0%SR)/9 fail
  - glm5_2_nv: 50OK/7 zombie_empty_completion (12.3%, avg 9.2s, 3-36s)
  - dsv4p_nv: 1OK/2 ATE (pre-R1725, 69-70s, 修复后零ATE)
- **24h窗口**: 181req/138OK(76.2%SR)/43 fail
  - glm5_2_nv: 137OK/41 zombie (23.0%), avg 9.2s
  - dsv4p_nv: 1OK/2 ATE
- **Tier attempts (6h)**: 55 pexec_success, 3 SSLEOFError, 1 pexec_429 (glm5_2_nv)
- **key_cycle_429s (6h)**: 91.7% (55/60 req), cycle=1: 51, cycle=2: 4
- **peer-fb**: 0 activity (HM2 health reachable ✓, dsv4p ATE pre-R1725 budget gap)
- **HM1 env**: TIER_TIMEOUT_BUDGET_S=145, BIG_INPUT_COOLDOWN_S=2400, FAIL_N=1, KEY=TIER=60

## 分析
- **Zombie cadence v2**: 7 zombies in 6h = effective cadence ~51 min (was 30 min pre-R1716)
  - R1716 COOLDOWN=2400=40min was calibrated for 30min cadence
  - 51min cadence means breaker closes at 40min, next zombie hits at 51min → breaker closed → zombie slips through
  - Only ~1st zombie after restart gets OPEN-broken; remaining 6 zombies evade breaker
- **Fix**: 2400→3600 (+1200s)
  - 3600s=60min = 51min cadence + 9min buffer
  - Guarantees breaker stays OPEN across entire zombie cadence
  - All subsequent zombies fast-failed as ATE → peer-fallback → HM2 → saves ~9.2s/zombie (avg)
- **Budget**: no OK impact (breaker only triggers for big_input >250K chars)
  - glm5_2 OK path: max_ok=51.8s << 145s safe ✓
  - dsv4p ATE→peer-fb: 70+125=195→cap 145, peer-fb gets 75s≥72 ✓
- 单参数; 铁律:只改HM1不改HM2

## 修改
- `NVU_BIG_INPUT_COOLDOWN_S`: 2400 → 3600 (+1200s)
- HM1 docker-compose.yml line 630
- 单参数; 铁律:只改HM1不改HM2

## 预算验证
| 路径 | 计算 | 约束 | 状态 |
|------|------|------|------|
| glm5_2 BIG_INPUT→ATE→peer-fb | 0+125=125 | < 145 ✓ | ✅ |
| dsv4p ATE→peer-fb | 70+125=195→cap 145 | peer-fb 75s ≥ 72 ✓ | ✅ |
| OK path | max_ok=51.8s | < 145 safe (93s headroom) | ✅ |
| BIG_INPUT breaker | 3600s=60min > 51min cadence | +9min buffer | ✅ |

## 验证
- `docker compose up -d nv_gw` → Started ✓
- `docker exec nv_gw env`: BIG_INPUT_COOLDOWN_S=3600 ✓
- `docker exec nv_gw env`: TIER_TIMEOUT_BUDGET_S=145, KEY=TIER=60, PEER_FALLBACK=125 ✓
- `curl /health`: status=ok ✓
- 无漂移: compose=3600, container=3600 ✓
## ⏳ 轮到HM1优化HM2
