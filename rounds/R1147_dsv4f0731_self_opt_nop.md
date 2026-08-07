# R1147 — dsvf0731_nv40666 NOP 巡检轮 (不改码)

**轮次**: R1147 | **日期**: 2026-08-08 04:38 UTC | **类型**: NOP
**容器**: dsvf0731_nv40666 (port 40666, DeepSeek V4 Pro via NVCF)

## 数据摘要 (30min 窗口)

| 指标 | 值 | 判定 |
|---|---|---|
| 总量 / 成功 / 失败 / 空 | 205 / 205 / 0 / 0 | SR = **100%** ✅ |
| Avg / P50 / P95 / max | 9202 / 8183 / 21023 / 25493 ms | 稳定 ✅ |
| 30min 错误分类 | (无) | 0 error ✅ |
| 429 计数 | 0 | ✅ |
| upstream_type | nvcf_pexec 205/205 (100%) | 纯 pexec |
| finish_reason | tool_calls 176 / stop 29 | 正常 |
| per-key 200 延迟 | k0 9648, k1 7281, k2 10777, k3 9609, k4 8776 | 方差可接受 (~3.5s) |
| per-key 错误 | 全 0 | ✅ |
| tier_attempts | (空, 首健成功) | ✅ |
| key_cycle_429s | k0=87, k1=119 | 循环中 429 被吸收, 无实际失败 |
| fallback (hm4104 最近5min) | 无 | ✅ |

## 趋势 (3h 逐小时 / 6h / 24h)

- 3h: 20:00 259/259, 19:00 349/348 (1 fail), 18:00 347/346 (1 fail), 17:00 90/85 (5 fail) — 每小时 SR ≥ 94.4%, 当前窗口 100%
- 6h: 1918/1909 = **99.53%** SR (9 fails)
- 24h all_tiers_exhausted = 105 (历史累积, 当前窗口 0)

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
| NV_INTEGRATE_* / NV_KEY_INTEGRATE_KEYS | 空 (无 integrate 路由) |

## 判定: NOP

符合 NOP 标准 (30min SR>95%, 无异常错误, 延迟稳定):
- 30min SR = 100%, 0 错误, 0 429, 0 fallback
- 6h SR = 99.53%
- 全 5 key 健康, 延迟中等方差 (k1 7281 ~ k2 10777, ~3.5s 方差, 但均低于 P95 且 0 错误)
- 当前上游 100% pexec, 无 integrate 流量 (无需调整 integrate 分配)

**无任何参数改动, 无容器重启。**

## 验证
- /health: status ok, nv_num_keys=5, port 40666, nv_default_model=glm5_2_nv
- 容器 dsvf0731_nv40666 Up 2 hours, 健康

## 上次修改效果
- R1146 亦为 NOP (30min 206/206=100%, avg 9290ms, key_cycle k0=87/k1=119)。本轮延续同一状态: avg 22902→9202ms (略降), SR 维持 100%。吞吐由 206→205 基本持平。key_cycle_429s 与上轮持平 (k0=87/k1=119)，429 持续被 KEY_COOLDOWN=30 吸收, 无实际失败。参数未动, 效果稳定偏优。

## 下一步建议
- 连续多轮 (R1143 起) 均维持 100% SR + 0 错误 + 0 fallback, 链路处于健康稳态。
- 观察 key_cycle_429s (k0=87, k1=119): 429 持续出现在循环中但被 KEY_COOLDOWN=30 吸收, 无实际失败。若后续出现实际 429 失败, 可考虑微增 KEY_COOLDOWN_S 30→35。
- 当前无 integrate 流量; 若未来引入 integrate 路由, 需对比 pexec/integrate SR 再决定 key 分配。