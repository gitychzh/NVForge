# R1150 — dsvf0731_nv40666 NOP 巡检轮 (不改码)

**轮次**: R1150 | **日期**: 2026-08-08 05:00 UTC | **类型**: NOP
**容器**: dsvf0731_nv40666 (port 40666, DeepSeek V4 Pro via NVCF)
**Verifier**: 本机 (HM2, opc2_uname)

## 数据摘要 (30min 窗口)

| 指标 | 值 | 判定 |
|---|---|---|
| 总量 / 成功 / 失败 / 空 | 200 / 200 / 0 / 0 | SR = **100%** ✅ |
| Avg / P50 / P95 | 9756 / 7890 / 23165 ms | 稳定 ✅ |
| 30min 错误分类 | (无) | 0 error ✅ |
| 429 计数 | 0 | ✅ |
| upstream_type | nvcf_pexec 200/200 (100%) | 纯 pexec |
| finish_reason | tool_calls 173 / stop 27 | 正常 |
| per-key 200 延迟 | k0 9934, k1 7181, k2 12226, k3 8768, k4 10786 | 方差可接受 (avg 差 <5.1s) |
| per-key 错误 | 全 0 | ✅ |
| per-key 请求数 | k0 39, k1 40, k2 39, k3 42, k4 40 | 负载均衡 ✅ |
| tier_attempts | (空, 首键成功) | ✅ |
| key_cycle_429s | k0=82, k1=119 | 循环中 429 被吸收, 无实际失败 |
| fallback (hm4104 最近5min) | 无 | ✅ |

## 趋势 (3h 逐小时 / 6h / 24h)

- 3h: 21:00 1/1, 20:00 405/405, 19:00 349/348 (1 fail), 18:00 345/344 (1 fail) — 最新完整窗口 100%
- 6h: 1941/1932 = **99.54%** SR (9 fails, 集中在早期窗口)
- 24h all_tiers_exhausted = 101 (跨 tier 汇总; **本 tier ATE 核验 = 0**, RN1009 修复持续奏效)

## 当前参数 (关键 env, 实值已核实, 均未改动)

| 参数 | 值 |
|---|---|
| UPSTREAM_TIMEOUT | 50 |
| TIER_TIMEOUT_BUDGET_S | 180 |
| NVU_TIER_BUDGET_DSV4F0731_NV | 180 |
| KEY_COOLDOWN_S | 30 |
| TIER_COOLDOWN_S | 90 |
| NVU_KEYMGR_429_BASE/MAX_COOLDOWN | 120 / 120 |
| NVU_KEYMGR_CONN_BASE/MAX/LONG | 30 / 60 / 120 |
| NVU_KEYMGR_CONN_FAIL_THRESHOLD | 3 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 3 |
| NVU_EMPTY_200_FASTBREAK | 3 |
| NVU_BUFFER_TIMEOUT_STAIRS | 90×5 |
| NV_INTEGRATE_* / NV_KEY_INTEGRATE_KEYS | 空 (无 integrate 路由) |
| NVU_PEER_FALLBACK_ENABLED | 0 |

env 实值与 R1149 文档一致, 无漂移。

## 判定: NOP

符合 NOP 标准 (30min SR>95%, 无异常错误, 延迟稳定):
- SR = 100% (200/200), 0 errors, 0 429
- 纯 pexec 单 upstream, 无 integrate 路由
- per-key 全 0 错误, 请求负载均衡, avg 延迟方差可接受
- 无 fallback 触发
- 24h 本 tier ATE = 0, RN1009 修复持续有效

## 下一步建议

链路极健康, 连续 (R1148/R1149/R1150) 三轮 100% SR。per-key avg 延迟最差 k2=12226ms vs 最忧 k1=7181ms, 差距 5.1s 处于可接受范围。继续观察是否有单 key 持续劣化趋势; 若非 persistent, 无需干预。无参数调整。

--- 修改指令: 无 (NOP) ---