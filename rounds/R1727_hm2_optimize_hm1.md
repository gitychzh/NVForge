# R1727 — HM2优化HM1: UPSTREAM_TIMEOUT 55→53 (-2s)

## 数据采集 (HM1, 6h post-R1726)
- **6h窗口**: 60req/52OK(86.7%SR)/8 fail
  - glm5_2_nv: 51OK/6 zombie_empty_completion (10.5%), p50=10.4s, p95=40.5s, max_ok=51.8s
  - dsv4p_nv: 1OK/2 ATE (pre-R1725 budget gap, 70s)
- **Tier attempts (6h)**: 55 pexec_success, 2 SSLEOFError, 1 pexec_429
- **key_cycle_429s (6h)**: 91.7% (55/60 req), cycle=1: 52, cycle=2: 3
- **0 NVCFPexecTimeout** — UPSTREAM not the binding constraint
- **HM1 env**: UPSTREAM=55, BUDGET=145, BIG_INPUT_COOLDOWN=3600, KEY=TIER=60, PEER_FB=125

## 分析
- p99=49.4s, UPSTREAM=55 → buffer=5.6s → 53 → buffer=3.6s ≥ 3s (R751 rule) ✓
- 0 NVCFPexecTimeout means no request is hitting UPSTREAM binding
- R1720 reduced 57→55 with similar data (max_ok=51.8s, p99=49.1s)
- -2s saves 2s on every timeout scenario (zombie, pexec timeout, stream stuck)
- Single parameter; iron law: only change HM1 never HM2

## 修改
- `UPSTREAM_TIMEOUT`: 55 → 53 (-2s)
- HM1 docker-compose.yml line 487
- 单参数; 铁律:只改HM1不改HM2

## 预算验证
| 路径 | 计算 | 约束 | 状态 |
|------|------|------|------|
| dsv4p ATE→peer-fb | 70+125=195→cap 145 | peer-fb 75s ≥ 72 ✓ | ✅ |
| BIG_INPUT→ATE→peer-fb | 0+125=125 | < 145 ✓ | ✅ |
| OK path | p99=49.4s, max=51.8s | UPSTREAM=53 buffer=3.6s ≥ 3s ✓ | ✅ |
| FORCE_STREAM_UPGRADE | 66 | ≥ UPSTREAM=53 ✓ | ✅ |

## 验证
- `docker compose up -d nv_gw` → Started ✓
- `docker exec nv_gw env`: UPSTREAM_TIMEOUT=53 ✓
- `docker exec nv_gw env`: BUDGET=145, KEY=TIER=60, PEER_FB=125, BIG_INPUT=3600 ✓
- `curl /health`: status=ok ✓
- 无漂移: compose=53, container=53 ✓
## ⏳ 轮到HM1优化HM2
