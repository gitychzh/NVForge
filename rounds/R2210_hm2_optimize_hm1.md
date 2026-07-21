# R2210 (HM2→HM1): NVU_TIER_BUDGET_DSV4P_NV 48→88 (+40s)

## 数据采集
- HM1: `ssh -p 222 opc_uname@100.109.153.83`, nv_gw 容器
- 6h window (03:00 UTC cutoff)

### DB 统计
| 指标 | 值 |
|------|-----|
| 总请求 | 52 |
| 成功 | 38 |
| 失败 | 14 |
| **成功率** | **73.1%** |

### 失败分解
| 模型 | 错误类型 | 数量 |
|------|---------|------|
| glm5_2_nv | zombie_empty_completion | 10 |
| dsv4p_nv | all_tiers_exhausted | 3 |
| dsv4p_nv | zombie_empty_completion | 1 |

### dsv4p ATE 深入分析
- 3 ATE 全部: `tiers_tried_count=1`, `key_cycle_429s=0`, `duration_ms ~48000`
- `nv_tier_attempts` 表: **0 条记录** → 全被预抢(pre-empted), 从未尝试过任何 key
- 根因: KEY_COOLDOWN_S=64 期间所有 key 都在冷却, budget=48 < 64+24=88, 在键冷却等完之前 budget 已耗尽

### 已确认配置 (重启后)
- `NVU_TIER_BUDGET_DSV4P_NV=88` ✓
- `KEY_COOLDOWN_S=64`
- `TIER_COOLDOWN_S=1`
- `UPSTREAM_TIMEOUT=24`
- `TIER_TIMEOUT_BUDGET_S=153`
- Health: `{"status":"ok"}` ✓

## 决策
**单参数**: NVU_TIER_BUDGET_DSV4P_NV 48→88
**依据**: 3 个 dsv4p ATE 全是预抢(0 tier_attempts)。KEY_COOLDOWN_S=64 + UPSTREAM=24 = 88 是最小值以保证1次key尝试。旧值 48 在键冷却 64s 内耗尽 budget, 连一次 key 都来不及试。
**预算**: KEY+TIER+DSV4P=64+1+88=153 → 等于 BUDGET=153, 刚好。无余量但一行代码保证了不会出现预抢。如果仍不够下一轮可微调。
**单参数**: 遵循少改多轮原则。只改 HM1 不改 HM2。

## 验证
- `docker exec nv_gw env | grep NVU_TIER_BUDGET_DSV4P_NV` → 88 ✓
- 容器名: nv_gw
- Health: `{"status": "ok"}`
- `docker logs nv_gw --tail 20` → 无异常

## ⏳ 轮到HM1优化HM2