# R1728 — HM2优化HM1: NVU_BIG_INPUT_COOLDOWN_S 3600→5400 (+1800s)

## 数据采集 (HM1, 6h post-R1727)
- **6h窗口**: 60req/52OK(86.7%SR)/8 fail
  - glm5_2_nv: 51OK/7 zombie_empty_completion (all big-input 314K-345K chars)
  - dsv4p_nv: 1OK/2 ATE (502, 69-70s, NVCF function degradation)
- **zombie cadence**: 7 zombie in 6h = 51.4min avg interval
- **zombie duration**: avg 8,210ms, range 3,038-13,773ms
- **0 NVCFPexecTimeout** — UPSTREAM=53 not binding
- **HM1 env**: UPSTREAM=53, BUDGET=145, COOLDOWN=3600, KEY=TIER=60, PEER_FB=125

## 分析
- 7 zombie全是big-input glm5_2_nv (314K-345K chars), 0 small-input zombie
- COOLDOWN=3600s(60min) < zombie cadence 51.4min → cooldown insufficient
- 5400s(90min) reduces theoretical max zombies from 6/6h to 4/6h
- Trade: cooldown期间big-input glm5_2 → fast-reject ATE (~0ms) 替代 slow zombie (3-14s)
- 单参数; 铁律:只改HM1不改HM2

## 修改
- `NVU_BIG_INPUT_COOLDOWN_S`: 3600 → 5400 (+1800s, +30min)
- HM1 docker-compose.yml line 630
- 单参数; 铁律:只改HM1不改HM2

## 预算验证
| 路径 | 计算 | 约束 | 状态 |
|------|------|------|------|
| BIG_INPUT→ATE→peer-fb | 0+125=125 | < 145 ✓ | ✅ |
| dsv4p ATE→peer-fb | 70+125=195→cap 145 | peer-fb 75s ≥ 72 ✓ | ✅ |
| OK path | p99=49.4s, max=51.8s | UPSTREAM=53 buffer=3.6s ≥ 3s ✓ | ✅ |
| FORCE_STREAM_UPGRADE | 66 | ≥ UPSTREAM=53 ✓ | ✅ |

## 验证
- `docker compose up -d nv_gw` → Recreated+Started ✓
- `docker exec nv_gw env`: BIG_INPUT_COOLDOWN_S=5400 ✓
- `docker exec nv_gw env`: UPSTREAM=53, BUDGET=145, KEY=TIER=60, PEER_FB=125, FASTBREAK=1 ✓
- `curl /health`: status=ok ✓
- 无漂移: compose=5400, container=5400 ✓
## ⏳ 轮到HM1优化HM2
