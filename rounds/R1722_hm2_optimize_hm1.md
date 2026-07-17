# R1722 — HM2优化HM1: TIER_TIMEOUT_BUDGET_S 145→140 (-5s)

## 数据采集 (HM1)
- **6h窗口**: 62req/51OK(82.3%SR)/11 fail
  - 9 zombie_empty_completion (glm5_2_nv, avg 8.8s, 30min cadence)
  - 2 dsv4p ATE (avg 69.5s)
- **Tier errors**: 4 pexec_SSLEOFError (glm5_2_nv, avg 10.9s), 1 pexec_429
- **max_ok**: 51.8s (glm5_2_nv), dsv4p OK=25.1s
- **容器状态**: 无漂移, 无peer-fb错误, 无连接错误, health=ok
- **HM2约束**: BUDGET_DSV4P_NV=70

## 分析
- TIER_TIMEOUT_BUDGET_S=145 有93s headroom (max_ok=51.8s), 继续 trimming 轨迹
- 145→140 (−5s), 仍留88s headroom, 远超需求
- 单参数, 继续 waste trimming

## 修改
- `TIER_TIMEOUT_BUDGET_S`: 145 → 140 (-5s)
- 单参数, 铁律:只改HM1不改HM2

## 预算验证
| 路径 | 计算 | 约束 | 状态 |
|------|------|------|------|
| dsv4p ATE→peer-fb | 65+125=190→cap 140 | peer-fb 得 75s ≥ 72 (HM2 70+2) ✓ | ✅ |
| glm5_2 BIG_INPUT→peer-fb | 0+125=125 | < 140 ✓ | ✅ |
| glm5_2 zombie→peer-fb | ~7+125=132 | < 140 ✓ | ✅ |
| OK path | max_ok=51.8s | < 140 safe (88s headroom) | ✅ |

## 验证
- `docker compose up -d nv_gw` → Started ✓
- `docker exec nv_gw env`: TIER_TIMEOUT_BUDGET_S=140 ✓
- `curl /health`: status=ok ✓
- 无漂移: 所有关键参数 compose = container ✓
## ⏳ 轮到HM1优化HM2
