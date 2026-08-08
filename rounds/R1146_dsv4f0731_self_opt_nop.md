# R1146 — dsvf0731_nv40666 NOP 巡检轮 (不改码)

**轮次**: R1146 | **日期**: 2026-08-08 04:36 UTC | **类型**: NOP
**容器**: dsvf0731_nv40666 (port 40666, DeepSeek V4 Pro via NVCF)

## 数据摘要 (30min 窗口)

| 指标 | 值 | 判定 |
|---|---|---|
| 总量 / 成功 / 失败 / 空 | 206 / 206 / 0 / 0 | SR = **100%** ✅ |
| Avg / P50 / P95 / max | 9290 / 8198 / 20988 / 25492 ms | 稳定 ✅ |
| 30min 错误分类 | (无) | 0 error ✅ |
| 429 计数 | 0 | ✅ |
| upstream_type | nvcf_pexec 206/206 (100%) | 纯 pexec |
| finish_reason | tool_calls 177 / stop 29 | 正常 |
| per-key 200 延迟 | k0 9657, k1 7481, k2 10903, k3 9160, k4 9339 | 方差可接受 (~3.4s) |
| per-key 错误 | 全 0 | ✅ |
| tier_attempts | (空, 首健成功) | ✅ |
| key_cycle_429s | k0=87, k1=119 | 循环中 429 被吸收, 无实际失败 |
| fallback (hm4104 最近5min) | 无 | ✅ |

## 趋势 (3h 逐小时 / 6h / 24h)

- 3h: 20:00 248/248, 19:00 348/348, 18:00 346/347 (1 fail), 17:00 94/99 (5 fail) — 每小时 SR ≥ 95%
- 6h: 1917/1908 = **99.53%** SR (9 fails)
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
- 全 5 key 健康, 延迟中等方差 (k1 7481 ~ k2 10903, ~3.4s 方差, 但均低于 P95 且 0 错误)
- 当前上游 100% pexec, 无 integrate 流量 (无需调整 integrate 分配)

**无任何参数改动, 无容器重启。**

## 验证
- /health: status ok, nv_num_keys=5, port 40666, nv_default_model=glm5_2_nv
- 容器 dsvf0731_nv40666 Up 2 hours, 健康

## 上次修改效果
- R1145 亦为 NOP (30min 215/215=100%, avg 8716ms, key_cycle k0=96/k1=119)。本轮延续同一状态, 无退化: avg 9290ms (微升但仍在稳定范围), SR 维持 100%。key_cycle_429s 由 k0=96/k1=119 降至 k0=87/k1=119 —— k0 的循环内 429 计数下滑, 说明 429 被 KEY_COOLDOWN=30 更好吸收, 无实际失败。参数未动, 效果稳定偏优。

## 下一步建议
- 连续 3 轮 (R1143/R1144/R1145) 均维持 100% SR + 0 错误 + 0 fallback, 链路处于健康稳态。
- 观察 key_cycle_429s (k0=87, k1=119): 429 持续出现在循环中但被 KEY_COOLDOWN=30 吸收, 无实际失败。若后续出现实际 429 失败, 可考虑微增 KEY_COOLDOWN_S 30→35。
- 当前无 integrate 流量; 若未来引入 integrate 路由, 需对比 pexec/integrate SR 再决定 key 分配。