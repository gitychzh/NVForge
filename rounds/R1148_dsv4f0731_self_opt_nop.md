# R1148 — dsvf0731_nv40666 NOP 巡检轮 (不改码)

**轮次**: R1148 | **日期**: 2026-08-08 04:54 UTC | **类型**: NOP
**容器**: dsvf0731_nv40666 (port 40666, DeepSeek V4 Pro via NVCF)
**Verifier**: 本机 (HM2, opc2_uname)

## 数据摘要 (30min 窗口)

| 指标 | 值 | 判定 |
|---|---|---|
| 总量 / 成功 / 失败 / 空 | 201 / 201 / 0 / 0 | SR = **100%** ✅ |
| Avg / P50 / P95 / P99 | 10073 / 8377 / 23585 / 31523 ms | 稳定 ✅ |
| 30min 错误分类 | (无) | 0 error ✅ |
| 429 计数 | 0 | ✅ |
| upstream_type | nvcf_pexec 201/201 (100%) | 纯 pexec |
| finish_reason | tool_calls 175 / stop 26 | 正常 |
| per-key 200 延迟 | k0 10037, k1 7803, k2 12397, k3 9230, k4 10984 | 方差可接受 (~4.6s) |
| per-key 错误 | 全 0 | ✅ |
| tier_attempts | (空, 首键成功) | ✅ |
| key_cycle_429s | k0=79, k1=122 | 循环中 429 被吸收, 无实际失败 |
| fallback (hm4104 最近5min) | 无 | ✅ |

## 趋势 (3h 逐小时 / 6h / 24h)

- 3h: 20:00 368/368, 19:00 349/348 (1 fail), 18:00 347/346 (1 fail), 17:00 16/14 (2 fail) — 最新窗口 100%
- 6h: 1937/1928 = **99.54%** SR (9 fails)
- 24h all_tiers_exhausted = 102 (跨 tier 汇总; **本 tier ATE 核验 =0**, RN1009 修复持续奏效)

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
| NVU_PEXEC_TIMEOUT_FASTBREAK | 3 |
| NVU_EMPTY_200_FASTBREAK | 3 |
| NVU_BUFFER_TIMEOUT_STAIRS | 90×5 |
| NV_INTEGRATE_* / NV_KEY_INTEGRATE_KEYS | 空 (无 integrate 路由) |
| NVU_PEER_FALLBACK_ENABLED | 0 |

env 实值与 R1147 文档一致, 无漂移。

## 判定: NOP

符合 NOP 标准 (30min SR>95%, 无异常错误, 延迟稳定):
- 30min SR = **100%**, 0 错误, 0 429, 0 fallback
- 6h SR = 99.54%
- 全 5 key 健康 (38~42 req/键, near 满负载), 延迟 7.8~12.4s 均衡, 0 错误
- 当前上游 100% pexec, 无 integrate 流量 (无需调整 integrate 分配)
- 本 tier 24h ATE=0

**无任何参数改动, 无容器重启。**

## 验证
- /health: status ok, nv_num_keys=5, port 40666, nv_default_model=glm5_2_nv
- 容器 dsvf0731_nv40666 Up 3 hours, 健康
- 关键 env 实值核实: `NVU_TIER_BUDGET_DSV4F0731_NV=180`, `NVU_TIER_BUDGET_DSV4F_NV=180`, `UPSTREAM_TIMEOUT=50`, `TIER_COOLDOWN_S=90`

## 上次修改效果 (R1147 → R1148)
R1147 亦为 NOP (30min 205/205=100%, avg 9202ms, key_cycle k0=87/k1=119)。
本轮延续同一稳定状态: avg 9202→10073ms (+871ms, 抽样噪声内), P50 8183→8377ms (持平),
SR 维持 **100%**。吞吐 205→201 基本持平。key_cycle_429s (k0=79/k1=122) 429 持续被
KEY_COOLDOWN=30 吸收, 无实际失败。参数未动, 系统连续多轮保持健康稳态。

## 下一步建议
- 连续多轮 (R1143 起) 均维持 100% SR + 0 错误 + 0 fallback, 链路处于健康稳态, 保持观察。
- key_cycle_429s (k0=79, k1=122): 429 持续出现在循环中但被 KEY_COOLDOWN=30 吸收, 无实际失败。
  若后续出现实际 429 失败, 可微增 KEY_COOLDOWN_S 30→35。
- 关注预置信号:
  - stream_first_byte_timeout 死链若重新聚集 (≥3/30min 或单 key 集中) → 源码级修复 (R1029/R1131 根因)
  - RemoteDisconnected/overloaded 频发 → 降 UPSTREAM_TIMEOUT 50→35s
  - IncompleteRead/SSLEOFError 聚集 → 检查对应 key 的 SOCKS5 端口