# R1153 — dsvf0731_nv40666 NOP 巡检轮 (不改码)

**轮次**: R1153 | **日期**: 2026-08-08 ~05:20 Beijing | **类型**: NOP
**容器**: dsvf0731_nv40666 (port 40666, DeepSeek V4 Pro via NVCF pexec)
**Verifier**: 本机 (HM2, opc2_uname)

## 数据摘要 (30min 窗口)

| 指标 | 值 | 判定 |
|---|---|---|
| 总量 / 成功 / 失败 / 空 | 184 / 184 / 0 / 0 | SR = **100%** ✅ |
| Avg / P50 / P95 / P99 | 9619 / 7926 / 21859 / 31294 ms | 稳定 ✅ |
| 30min 错误分类 | (无) | 0 error ✅ |
| 429 计数 | 0 | ✅ |
| upstream_type | nvcf_pexec 184/184 (100%) | 纯 pexec |
| finish_reason | tool_calls 158 / stop 26 | 正常 |
| per-key 200 延迟 | k0 9294(37), k1 9255(38), k2 9424(37), k3 9347(36), k4 10811(36) | 方差优秀 (max gap ~1.6s) |
| per-key 错误 | 全 0 | ✅ |
| per-key 请求数 | k0 37, k1 38, k2 37, k3 36, k4 36 | 负载均衡 ✅ |
| tier_attempts | (空, 首键成功) | ✅ |
| key_cycle_429s | k0=68, k1=116 | 循环中 429 被吸收, 无实际失败 |
| fallback (hm4104 最近5min) | 无 | ✅ |

## 趋势 (3h 逐小时 / 6h / 24h)

- 3h: 21:00 112/112 (100%), 20:00 405/405 (100%), 19:00 349/348 (1 fail), 18:00 230/229 (1 fail) — 最新一小时 100%
- 6h: 1968/1960 = **99.59% SR** (8 fails, 集中在早期窗口)
- 24h all_tiers_exhausted = 99 (跨 tier 汇总; 本 tier ATE 核验 = 0, RN1009 修复持续奏效)

## 当前参数 (关键 env, 实值已核实, 均未改动)

| 参数 | 值 |
|---|---|
| UPSTREAM_TIMEOUT | 50 |
| TIER_TIMEOUT_BUDGET_S | 180 |
| NVU_TIER_BUDGET_DSV4F0731_NV | 180 (未显式列出, 走 TIER_TIMEOUT_BUDGET_S=180 兜底预算) |
| KEY_COOLDOWN_S | 30 |
| TIER_COOLDOWN_S | 90 |
| NVU_KEYMGR_429_BASE/MAX_COOLDOWN | 120 / 120 |
| NVU_KEYMGR_CONN_BASE/MAX/LONG | 30 / 60 / 120 |
| NVU_KEYMGR_CONN_FAIL_THRESHOLD | 3 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 3 |
| NVU_EMPTY_200_FASTBREAK | 3 |
| NV_INTEGRATE_* / NV_KEY_INTEGRATE_KEYS | 空 (无 integrate 路由) |
| NVU_PEER_FALLBACK_ENABLED | 0 |

env 实值与 R1152 文档逐项一致, 无漂移。`docker exec dsvf0731_nv40666 env` 已复核。

## 判定: NOP

符合 NOP 标准 (30min SR>95%, 无异常错误, 延迟稳定):
- SR = 100% (184/184), 0 errors, 0 429, 0 空响应
- 纯 pexec 单 upstream, 无 integrate 路由
- per-key 全 0 错误, 请求负载均衡 (36~38/key), avg 延迟方差优秀 (max 差 ~1.6s, 优于上轮 R1152 的 2.0s / R1151 的 4.3s)
- 无 fallback 触发
- 24h 本 tier ATE = 0, RN1009 修复持续有效; key_cycle_429s 计数 (68/116) 低于上轮 (71/117), 429 持续收敛

## 下一步建议

链路健康, 连续 (R1148/R1149/R1150/R1151/R1152/R1153) 六轮 100% SR。per-key avg 延迟各方差极佳 (max 差 1.6s), 无劣化 key。继续观察是否有单 key 持续劣化趋势。预置对策 (供触发时启用):
- 429 回升 → `KEY_COOLDOWN_S` 30→60s
- RemoteDisconnected/overloaded 频发拉低 SR → `UPSTREAM_TIMEOUT` 50→35s
- IncompleteRead/SSLEOFError 聚集 (≥30/h) → 查对应 key 的 SOCKS5 端口

无参数调整。

--- 修改指令: 无 (NOP) ---