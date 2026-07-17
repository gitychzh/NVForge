# R1719: HM2→HM1 — UPSTREAM_TIMEOUT 60→57 (-3s)

## 数据采集
- **6h窗口**: 70 req | 59 OK (84.3% SR) | 11 fail
- **错误分布**: 9 zombie_empty_completion (glm5_2_nv, BIG_INPUT breaker rescue→peer-fb) + 2 dsv4p_nv ATE (all_tiers_exhausted)
- **glm5_2_nv**: 58 OK (86.6%) | 9 zombie, avg=14.2s, max=51.8s, p99=49.1s, 100% key_cycle_429s
- **dsv4p_nv**: 1 OK (25.1s, ATE rescued) | 2 ATE 502 (69-70s), tiers_tried=1, key_cycle=0
- **peer-fb**: 0 fallback_occurred records in DB (container just restarted R1718)
- **Container**: no drift, compose = container ✓

## 分析
dsv4p ATE 在 69-70s 耗尽单个 key (UPSTREAM_TIMEOUT=60 + ~4s overhead):
- FASTBREAK=1 下仅试 1 key → 70s = 60s key timeout + 10s overhead
- 60→57: 节省 3s/ATE, key 在 57s timeout
- max_ok=51.8s, 57s buffer=5.2s 安全
- BIG_INPUT breaker (FAIL_N=1, COOLDOWN=2400) 处理 glm5_2 zombie

## 修改
- `UPSTREAM_TIMEOUT`: 60 → 57 (-3s)
- 单参数, 铁律:只改HM1不改HM2

## 预算验证
| 路径 | 计算 | 约束 | 状态 |
|------|------|------|------|
| dsv4p ATE→peer-fb | 65+125=190→cap 150 | peer-fb 得 85s ≥ 72 ✓ | ✅ |
| glm5_2 BIG_INPUT→peer-fb | 0+125=125 | < 150 ✓ | ✅ |
| glm5_2 zombie→peer-fb | ~7+125=132 | < 150 ✓ | ✅ |

## 验证
- `docker compose up -d nv_gw` → Started ✓
- `docker exec nv_gw env`: UPSTREAM_TIMEOUT=57 ✓
- `curl /health`: status=ok ✓
- 无漂移: 所有关键参数 compose = container ✓
## ⏳ 轮到HM1优化HM2
