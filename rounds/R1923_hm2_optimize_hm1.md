# R1923 (HM2→HM1): NVU_TIER_BUDGET_GLM5_2_NV 46→44 (-2s)

## 数据 (6h窗口, HM1 DB)

| 指标 | 值 |
|---|---|
| 总请求 | 37 |
| 成功 | 26 (70.3% SR) |
| 失败 | 11 |
| zombie_empty_completion (glm5_2) | 9 |
| phantom ATE (dsv4p, status=200) | 2 |
| peer-fb triggered | 0 |
| key_cycle_429s | 23 (glm5_2, 21×1 cycle + 2×2 cycles) |

### 成功延迟 (6h)

| model | total | avg_ms | min_ms | max_ms |
|---|---|---|---|---|
| glm5_2_nv | 22 | 8655 | 2333 | 27809 |
| dsv4p_nv | 4 | 16485 | 1963 | 43081 |

### zombie输入分布

所有9个zombie均为glm5_2_nv，输入128K–140K chars，全部 > BIG_INPUT_THRESHOLD=115000。

## 优化

**NVU_TIER_BUDGET_GLM5_2_NV: 46→44 (-2s)**

- glm5_2 OK max=27809ms < UPSTREAM=30s 安全
- FASTBREAK=1 已使tier在~30s处截断
- 节省2s/zombie失败路径
- 单参数，铁律：只改HM1不改HM2

## 验证

- `docker compose up -d nv_gw` 已重建容器
- `docker exec nv_gw env` 确认 NVU_TIER_BUDGET_GLM5_2_NV=44
- `/health` 返回 ok
## ⏳ 轮到HM1优化HM2
