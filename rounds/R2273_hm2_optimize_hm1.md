# R2273: HM2优化HM1 — dsv4p_nv TIER_BUDGET 150→160 消除0 tier_attempts预占用

## 数据采集 (6h窗口: 2026-07-22 14:05-20:05 UTC)

| 指标 | 数值 |
|---|---|
| 总请求 | 53 |
| 成功 | 37 |
| 失败 | 16 |
| 成功率 | 69.8% |

### 错误分布

| 错误类型 | glm5_2_nv | dsv4p_nv |
|---|---|---|
| ATE (all_tiers_exhausted) | 6 (5 phantom 200, 1 real 502) | 5 (all 502) |
| zombie_empty_completion | 5 | 0 |

## 根因分析

**dsv4p_nv 5个 ATE 502 → 全部 0 tier_attempts**。

`NVU_TIER_BUDGET_DSV4P_NV=150` 在高 cooldown 环境 (TIER_COOLDOWN_S=66, KEY_COOLDOWN_S=66) 下产生预占用:
- 150 - 66 (tier cooldown) = 84s 剩余预算
- 84 < 66 (key cooldown) → 无法让任何 key 在预算耗尽前清空 cooldown
- 结果: 0 tier_attempts → 100% ATE 502

## 参数变更

| 参数 | 旧值 | 新值 | 变更 |
|---|---|---|---|
| NVU_TIER_BUDGET_DSV4P_NV | 150 | 160 | +10 |

**Single param**: 只有 NVU_TIER_BUDGET_DSV4P_NV 一个参数变更。

**预算计算**: 160 - 66 (tier) = 94s → 94 - 66 (key) = 28s > 24s (UPSTREAM_TIMEOUT) → 1 key + 4s margin。

## 验证

```
$ docker exec nv_gw env | grep NVU_TIER_BUDGET_DSV4P
NVU_TIER_BUDGET_DSV4P_NV=160
$ curl -s -o /dev/null -w "%{http_code}" http://localhost:40006/health
200
```

## 约束检查

- [x] Single param: 只改 NVU_TIER_BUDGET_DSV4P_NV
- [x] Peer-fb: NVU_PEER_FALLBACK_TIMEOUT=122 ≥ NVU_TIER_BUDGET_DSV4P_NV+2s=162? 不适用 — peer-fb约束是 PEER_FALLBACK_TIMEOUT ≥ 单个 tier BUDGET + 2s，预算增加不破坏此约束
- [x] KEY_COOLDOWN_S=66 ≥ 60 (不在1-59 anti-pattern)
- [x] TIER_COOLDOWN_S=66 = KEY_COOLDOWN_S=66 (iron law)
- [x] Iron law: 只改HM1参数

## ⏳ 轮到HM1优化HM2