# R1140 — dsvf0731_nv40666 NOP 巡检轮 (不改码)

**轮次**: R1140 | **日期**: 2026-08-08 04:12 UTC | **类型**: NOP
**容器**: dsvf0731_nv40666 (port 40666, DeepSeek V4 Pro via NVCF)

## 数据摘要 (30min 窗口)

| 指标 | 值 | 判定 |
|---|---|---|
| 总量 / 成功 / 失败 / 空 | 207 / 207 / 0 / 0 | SR = **100%** ✅ |
| Avg / P50 / P95 / max | 9302 / 7951 / 21491 / 24442 ms | 稳定 ✅ |
| 30min 错误分类 | (无) | 0 error ✅ |
| 429 计数 | 0 | ✅ |
| upstream_type | nvcf_pexec 206/206 (100%) | 纯 pexec |
| finish_reason | tool_calls 181 / stop 25 | 正常 |
| per-key 200 延迟 | k0 9386, k1 8945, k2 9927, k3 7601, k4 10529 | 方差可接受 (<3s) |
| per-key 错误 | 全 0 | ✅ |
| key_cycle_429s | k0=88, k1=118 | 循环中有 429 但被吸收, 无实际失败 |
| fallback (hm4104 最近5min) | 无 | ✅ |

## 趋势 (3h 逐小时 / 6h / 24h)

- 3h: 17:00 213/218 (av), 18:00 346/347, 19:00 348/349, 20:00 84/84 — 每小时 SR ≥ 97.7%
- 6h: 1852/1862 = **99.46%** SR
- 24h all_tiers_exhausted = 109 (历史累积, 当前窗口 0)

## 当前参数 (关键 env, 均未改动)

| 参数 | 值 |
|---|---|
| UPSTREAM_TIMEOUT | 50 |
| TIER_TIMEOUT_BUDGET_S | 180 |
| NVU_TIER_BUDGET_DSV4F0731_NV | 180 |
| KEY_COOLDOWN_S | 30 |
| TIER_COOLDOWN_S | 90 |
| NVU_KEYMGR_429_BASE/MAX_COOLDOWN | 120 / 120 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 3 |
| NVU_EMPTY_200_FASTBREAK | 3 |

## 判定: NOP

符合 NOP 标准 (30min SR>95%, 无异常错误, 延迟稳定):
- 30min SR = 100%, 0 错误, 0 429, 0 fallback
- 6h SR = 99.46%
- 全 5 key 健康, 延迟方差小
- 当前上游 100% pexec, 无 integrate 流量被路由 (无需调整 integrate 分配)

**无任何参数改动, 无容器重启。**

## 验证
- /health: status ok, nv_num_keys=5, port 40666
- 容器 Up 2 hours, 健康

## 下一步建议
- 观察 key_cycle_429s (k0=88, k1=118): 429 出现在循环中但被 KEY_COOLDOWN 吸收, 无实际失败。若后续出现实际 429 失败, 可考虑微增 KEY_COOLDOWN_S 30→35。
- 当前无 optimize/integrate 流量; 若未来引入 integrate 路由, 需对比 pexec/integrate SR 再决定 key 分配。