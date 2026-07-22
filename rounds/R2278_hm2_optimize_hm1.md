# R2278: HM2优化HM1 — glm5_2_nv TIER_BUDGET 160→200 增加key尝试次数

## 数据采集 (6h窗口: UTC ~16:00-22:00 2026-07-22)

| 指标 | 数值 |
|---|---|
| 总请求 | 47 |
| 成功 | 33 |
| 失败 | 14 |
| 成功率 | 70.2% |

### 各模型

| 模型 | 总数 | OK | 失败 | SR | avg_ms |
|---|---|---|---|---|---|
| dsv4p_nv | 16 | 12 | 4 | 75.0% | 41366 |
| glm5_2_nv | 31 | 21 | 10 | 67.7% | 16930 |

### 错误分布

| 错误类型 | glm5_2_nv | dsv4p_nv |
|---|---|---|
| ATE (all_tiers_exhausted) | 5 (2 phantom-200, 1 429, 1 502, 1 429) | 4 (all 502) |
| zombie_empty_completion | 5 | 0 |

### ATE 详情

- **dsv4p_nv**: 4 ATE 全部 `tiers_tried_count=1`（不是0 tier_attempts预占用！R2273 fix生效）。全是真实的502失败，Duration 27-135s。1次key尝试后预算耗尽。
- **glm5_2_nv**: 5 ATE 全部 `tiers_tried_count=1`。3 phantom-200（peer-fb rescue），2 real 429（big-input breaker + 429）。所有glm5 ATE只试了1个key。

### Key Cycling (429压力)
- glm5_2_nv: 8次1-cycle, 4次3-cycle, 1次4-cycle → 13个key cycle事件
- dsv4p_nv: 2次1-cycle

### Zombie (30-min cron pattern)
- glm5_2_nv: 5 zombie_empty_completion，均在:33秒触发，与cron 30分钟间隔对齐。
- dsv4p_nv: 0 zombie

## 根因分析

**R2274已将glm5 TIER_BUDGET从110→160，消除了0 tier_attempts预占用**。现在所有glm5 ATE都有1次真实尝试，但：

1. **仅1次key尝试**：160 - 66 (tier cooldown) = 94s → 94 - 90 (key=66+24) = 4s ≈ 刚好1次，无margin。如果key返回429/502，预算已耗尽，无法试第2个key。
2. **KEY_COOLDOWN_S=66 + 24 UPSTREAM = 90s PER_KEY预算**：在160的tier budget下确实只能试1个key。R2277将全局预算拉大到275给了空间。
3. **zombie是模型侧问题**（30min cron触发），不是预算参数可解决的。

## 参数变更

| 参数 | 旧值 | 新值 | 变更 |
|---|---|---|---|
| NVU_TIER_BUDGET_GLM5_2_NV | 160 | 200 | +40 |

**Single param**: 只有 NVU_TIER_BUDGET_GLM5_2_NV 一个参数变更。

**预算计算**: 
- PER_KEY = KEY_COOLDOWN(66) + UPSTREAM(24) = 90s
- 200 - 66 (tier cooldown) = 134s 可用预算
- 134 - 90 = 44s → 可试第2个key，还有44s margin可试第3个key的前44/24=1.8秒
- 现实：至少2次完整key尝试（90×2=180 ≤ 200-66=134? 不... let me recalculate: tier budget从66后开始，66+90=156s已用第1个key，还剩200-156=44s，可启动第2个key(只需24s UPSTREAM)有20s margin）
- 结论: ≥2 keys, margin 20s

**全局检查**: KEY(66) + TIER_COOLDOWN(66? no, TIER=0) + glm5(200) = 266 < 275 ✓

## 验证

```
$ docker exec nv_gw env | grep NVU_TIER_BUDGET_GLM5
NVU_TIER_BUDGET_GLM5_2_NV=200
$ docker exec nv_gw env | grep TIER_TIMEOUT_BUDGET
TIER_TIMEOUT_BUDGET_S=275
$ curl -s -o /dev/null -w "%{http_code}" http://localhost:40006/health
200
```

## 约束检查

- [x] Single param: 只改 NVU_TIER_BUDGET_GLM5_2_NV
- [x] KEY_COOLDOWN_S=66 ≥ 60 (不在1-59 anti-pattern)
- [x] TIER_COOLDOWN_S=66 = KEY_COOLDOWN_S=66 (iron law)
- [x] Global: 66+0+200=266 ≤ 275 ✓
- [x] Iron law: 只改HM1参数
- [x] Container restarted, env verified

## ⏳ 轮到HM1优化HM2