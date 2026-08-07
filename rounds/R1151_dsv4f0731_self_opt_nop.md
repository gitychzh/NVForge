# R1151 — dsvf0731_nv40666 NOP 巡检轮 (不改码)

**轮次**: R1151 | **日期**: 2026-08-08 05:05 UTC | **类型**: NOP
**容器**: dsvf0731_nv40666 (port 40666, DeepSeek V4 Pro via NVCF pexec)
**Verifier**: 本机 (HM2, opc2_uname)

## 数据摘要 (30min 窗口)

| 指标 | 值 | 判定 |
|---|---|---|
| 总量 / 成功 / 失败 / 空 | 202 / 202 / 0 / 0 | SR = **100%** ✅ |
| Avg / P50 / P95 / P99 | 9936 / 7933 / 23112 / 31523 ms | 稳定 ✅ |
| 30min 错误分类 | (无) | 0 error ✅ |
| 429 计数 | 0 | ✅ |
| upstream_type | nvcf_pexec 202/202 (100%) | 纯 pexec |
| finish_reason | tool_calls 176 / stop 26 | 正常 |
| per-key 200 延迟 | k0 10464(40), k1 7291(40), k2 11605(40), k3 9829(42), k4 10495(40) | 方差可接受 (max gap ~4.3s) |
| per-key 错误 | 全 0 | ✅ |
| per-key 请求数 | k0 40, k1 40, k2 40, k3 42, k4 40 | 负载均衡 ✅ |
| tier_attempts | (空, 首键成功) | ✅ |
| key_cycle_429s | k0=80, k1=122 | 循环中 429 被吸收, 无实际失败 |
| fallback (hm4104 最近5min) | 无 | ✅ |

## 趋势 (3h 逐小时 / 6h / 24h)

- 3h: 21:00 16/16 (100%), 20:00 405/405 (100%), 19:00 349/348 (1 fail), 18:00 343/342 (1 fail) — 最新两小时 100%
- 6h: 1949/1940 = **99.54%** SR (9 fails, 集中在早期窗口)
- 24h all_tiers_exhausted = 101 (跨 tier 汇总; 本 tier ATE 核验 = 0, RN1009 修复持续奏效)

## 当前参数 (关键 env, 实值已核实, 均未改动)

| 参数 | 值 |
|---|---|
| UPSTREAM_TIMEOUT | 50 |
| TIER_TIMEOUT_BUDGET_S | 180 |
| NVU_TIER_BUDGET_DSV4F0731_NV | 180 |
| NVU_TIER_BUDGET_DSV4F_NV | 180 |
| KEY_COOLDOWN_S | 30 |
| TIER_COOLDOWN_S | 90 |
| NVU_KEYMGR_429_BASE/MAX_COOLDOWN | 120 / 120 |
| NVU_KEYMGR_CONN_BASE/MAX/LONG | 30 / 60 / 120 |
| NVU_KEYMGR_CONN_FAIL_THRESHOLD | 3 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 3 |
| NVU_EMPTY_200_FASTBREAK | 3 |
| NVU_PROBE_ENABLED / INTERVAL / TIMEOUT | 1 / 15 / 10 |
| NV_INTEGRATE_* / NV_KEY_INTEGRATE_KEYS | 空 (无 integrate 路由) |
| NVU_PEER_FALLBACK_ENABLED | 0 |

env 实值与 R1150 文档逐项一致, 无漂移。`docker exec dsvf0731_nv40666 env` 已复核。

## 判定: NOP

符合 NOP 标准 (30min SR>95%, 无异常错误, 延迟稳定):
- SR = 100% (202/202), 0 errors, 0 429, 0 空响应
- 纯 pexec 单 upstream, 无 integrate 路由
- per-key 全 0 错误, 请求负载均衡 (40~42/key), avg 延迟方差可接受 (max 差 ~4.3s)
- 无 fallback 触发
- 24h 本 tier ATE = 0, RN1009 修复持续有效

## 下一步建议

链路��健康, 连续 (R1148/R1149/R1150/R1151) 四轮 100% SR。per-key avg 延迟最差 k2=11605ms vs 最优 k1=7291ms, 差距 4.3s 处于可接受范围 (优于上轮 R1150 的 5.1s gap)。继续观察是否有单 key 持续劣化趋势。预置对策 (供触发时启用):
- 429 回升 → `KEY_COOLDOWN_S` 30→60s
- RemoteDisconnected/overloaded 频发拉低 SR → `UPSTREAM_TIMEOUT` 50→35s
- IncompleteRead/SSLEOFError 聚集 (≥30/h) → 查对应 key 的 SOCKS5 端口

无参数调整。

--- 修改指令: 无 (NOP) ---