# R1721: HM2→HM1 — TIER_TIMEOUT_BUDGET_S 150→145 (-5s)

## 数据采集
- **6h窗口**: 70 req | 59 OK (84.3% SR) | 11 fail
- **错误分布**: 9 zombie_empty_completion (glm5_2_nv, BIG_INPUT breaker handle) + 2 dsv4p_nv ATE (all_tiers_exhausted)
- **glm5_2_nv**: 58/67 OK (86.6%), max_ok=51.8s, 9 zombie, 100% key_cycle_429s (58 cycle=1, 2 cycle=2)
- **dsv4p_nv**: 1/3 OK (33.3%), 2 ATE at ~70s (BUDGET=65 capped)
- **peer-fallback**: 0 triggered, 0 fallback_occurred
- **Container**: no drift, compose = container ✓
- **nv_gw logs**: 0 errors/warnings

## 分析
max_ok=51.8s (glm5_2), BUDGET=150 headroom=98s oversized:
- 150→145: 节省 5s/ATE, 零 OK 影响 (max_ok=51.8s << 145)
- R1715→R1720 轨迹: BUDGET 165→150 已验证 98s headroom 安全
- 继续 waste trimming 轨迹

## 修改
- `TIER_TIMEOUT_BUDGET_S`: 150 → 145 (-5s)
- 单参数, 铁律:只改HM1不改HM2

## 预算验证
| 路径 | 计算 | 约束 | 状态 |
|------|------|------|------|
| dsv4p ATE→peer-fb | 65+125=190→cap 145 | peer-fb 得 80s ≥ 72 ✓ | ✅ |
| glm5_2 BIG_INPUT→peer-fb | 0+125=125 | < 145 ✓ | ✅ |
| glm5_2 zombie→peer-fb | ~7+125=132 | < 145 ✓ | ✅ |
| OK path | max_ok=51.8s | < 145 safe (93s headroom) | ✅ |

## 验证
- `docker compose up -d nv_gw` → Started ✓
- `docker exec nv_gw env`: TIER_TIMEOUT_BUDGET_S=145 ✓
- `curl /health`: status=ok ✓
- 无漂移: 所有关键参数 compose = container ✓
## ⏳ 轮到HM1优化HM2
