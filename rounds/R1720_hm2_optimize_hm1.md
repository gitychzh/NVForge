# R1720: HM2→HM1 — UPSTREAM_TIMEOUT 57→55 (-2s)

## 数据采集
- **6h窗口**: 70 req | 59 OK (84.3% SR) | 11 fail
- **错误分布**: 9 zombie_empty_completion (glm5_2_nv, BIG_INPUT breaker handle) + 2 dsv4p_nv ATE (all_tiers_exhausted, pre-R1719 restart)
- **glm5_2_nv**: 58/67 OK (86.6%), max_ok=51.8s, 9 zombie, 100% key_cycle_429s
- **dsv4p_nv**: 1/3 OK (33.3%), 2 ATE at 69-70s (UPSTREAM=60 era, pre-R1719)
- **peer-fallback**: 0 triggered (container restarted R1719, breaker state reset)
- **Container**: no drift, compose = container ✓

## 分析
max_ok=51.8s (glm5_2), UPSTREAM=57 buffer=5.2s:
- 57→55: 节省 2s/ATE, max_ok 51.8s buffer=3.2s 安全
- dsv4p ATE: BUDGET=65 caps at 65s regardless of UPSTREAM (65 < 57 + 5key overhead)
- 继续 UPSTREAM 微修轨迹 (R1719: 60→57, R1720: 57→55)

## 修改
- `UPSTREAM_TIMEOUT`: 57 → 55 (-2s)
- 单参数, 铁律:只改HM1不改HM2

## 预算验证
| 路径 | 计算 | 约束 | 状态 |
|------|------|------|------|
| dsv4p ATE→peer-fb | 65+125=190→cap 150 | peer-fb 得 85s ≥ 72 ✓ | ✅ |
| glm5_2 BIG_INPUT→peer-fb | 0+125=125 | < 150 ✓ | ✅ |
| glm5_2 zombie→peer-fb | ~7+125=132 | < 150 ✓ | ✅ |

## 验证
- `docker compose up -d nv_gw` → Started ✓
- `docker exec nv_gw env`: UPSTREAM_TIMEOUT=55 ✓
- `curl /health`: status=ok ✓
- 无漂移: 所有关键参数 compose = container ✓
## ⏳ 轮到HM1优化HM2
