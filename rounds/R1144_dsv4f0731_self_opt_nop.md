# R1144 — dsvf0731_nv40666 NOP 巡检轮 (不改码)

**轮次**: R1144 | **日期**: 2026-08-08 04:22 UTC | **类型**: NOP
**容器**: dsvf0731_nv40666 (port 40666, DeepSeek V4 Pro via NVCF)

## 数据摘要 (30min 窗口)

| 指标 | 值 | 判定 |
|---|---|---|
| 总量 / 成功 / 失败 / 空 | 212 / 212 / 0 / 0 | SR = **100%** ✅ |
| Avg / P50 / P95 / max | 8778 / 7775 / 20619 / 23884 ms | 稳定 ✅ |
| 30min 错误分类 | (无) | 0 error ✅ |
| 429 计数 | 0 | ✅ |
| upstream_type | nvcf_pexec 212/212 (100%) | 纯 pexec |
| finish_reason | tool_calls 183 / stop 29 | 正常 |
| per-key 200 延迟 | k0 8413, k1 8439, k2 8600, k3 8373, k4 10001 | 方差可接受 (~1.6s) |
| per-key 错误 | 全 0 | ✅ |
| key_cycle_429s | k0=96, k1=116 | 循环中有 429 但被吸收, 无实际失败 |
| fallback (hm4104 最近5min) | 无 | ✅ |

## 趋势 (3h 逐小时 / 6h / 24h)

- 3h: 20:00 157/157, 19:00 349/348 (1 fail), 18:00 347/346 (1 fail), 17:00 176/171 (5 fail) — 每小时 SR ≥ 97%
- 6h: 1893/1883 = **99.47%** SR (10 fails)
- 24h all_tiers_exhausted = 107 (历史累积, 当前窗口 0)

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
- 6h SR = 99.47%
- 全 5 key 健康, 延迟小方差 (k0 8413 ~ k4 10001, ~1.6s 方差)
- 当前上游 100% pexec, 无 integrate 流量被路由 (无需调整 integrate 分配)

**无任何参数改动, 无容器重启。**

## 验证
- /health: status ok, nv_num_keys=5, port 40666, nv_default_model=glm5_2_nv
- 容器 dsvf0731_nv40666 Up 2 hours, 健康

## 上次修改效果
- R1143 亦为 NOP (30min 203/203=100%, avg 9037ms, key_cycle_429s k0=89/k1=114)。本轮延续同一状态, 无退化: avg 8778ms (略优), SR 维持 100%。key_cycle_429s 由 k0=89/k1=114 微升至 k0=96/k1=116, 但无实际 429 失败。参数未动, 效果稳定。

## 下一步建议
- 观察 key_cycle_429s (k0=96, k1=116): 429 持续出现在循环中但被 KEY_COOLDOWN=30 吸收, 无实际失败。若后续出现实际 429 失败, 可考虑微增 KEY_COOLDOWN_S 30→35。
- 当前无 integrate 流量; 若未来引入 integrate 路由, 需对比 pexec/integrate SR 再决定 key 分配。