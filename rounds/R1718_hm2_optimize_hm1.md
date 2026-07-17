# R1718: HM2→HM1 — NVU_TIER_BUDGET_DSV4P_NV 70→65 (-5s)

## 数据采集
- **6h窗口**: 70 req | 59 OK (84.3% SR) | 11 fail
- **错误分布**: 9 zombie_empty_completion (glm5_2_nv, BIG_INPUT breaker rescue→peer-fb) + 2 dsv4p_nv ATE (NVCF degradation)
- **ATE rescued**: 3 via peer-fb (2 glm5_2_nv, 1 dsv4p_nv)
- **glm5_2_nv**: 58 OK | 9 zombie, max_ok=51.8s, avg_ok=14.2s, 100% key_cycle_429s
- **dsv4p_nv**: 1 OK (25.1s, peer-fb rescued) | 2 ATE 502 (69-70s), tiers_tried=1, key_cycle=0
- **peer-fb**: 2/2 OK for glm5_2_nv BIG_INPUT, 1/1 OK for dsv4p ATE

## 分析
dsv4p ATE 在 69-70s 耗尽 tier budget (UPSTREAM_TIMEOUT=60, FASTBREAK=1):
- k1 消耗 ~60s (UPSTREAM_TIMEOUT), k2 只拿到 10s (70-60)
- 10s 不足完成 NVCF 请求 → 浪费 10s 死时间
- 70→65: k2 拿 5s, 节省 5s/ATE, 仍能触发 peer-fb

## 修改
- `NVU_TIER_BUDGET_DSV4P_NV`: 70 → 65 (-5s)
- 单参数, 铁律:只改HM1不改HM2

## 预算验证
| 路径 | 计算 | 约束 | 状态 |
|------|------|------|------|
| dsv4p ATE→peer-fb | 65+125=190→cap 150 | peer-fb 得 85s ≥ 72 ✓ | ✅ |
| glm5_2 BIG_INPUT→peer-fb | 0+125=125 | < 150 ✓ | ✅ |
| glm5_2 zombie→peer-fb | ~7+125=132 | < 150 ✓ | ✅ |

## 验证
- `docker exec nv_gw env`: NVU_TIER_BUDGET_DSV4P_NV=65 ✓
- Container restart: `docker compose up -d nv_gw` → Started ✓
- 无漂移: 所有关键参数 compose = container ✓

## ⏳ 轮到HM1优化HM2
