# R1087: dsv4f0731_nv self-opt — NOP (SR 97.5% 健康稳定, 错误仅 3 次偶发, 429=0, 无单 key 劣化, 趋势稳定)

日期: 2026-08-07 ~13:14 (BJT) = ~05:14 UTC

## 1. 数据 (30min 窗口 采集)

### 主指标
- **SR = 97.5% (115/118)**, avg=16933ms, p50=10089ms, **p95=52607ms**, max=173420ms
- 30min 错误: **all_tiers_exhausted=2** (avg 178369ms), **stream_absolute_cap=1** (avg 157510ms)
- **429 计数 = 0** (无 429 冷却杠杆)
- upstream_type: 100% nvcf_pexec (118/118), **integrate 0 请求**
- finish_reason: tool_calls=90, stop=25 (正常)
- tier_attempts: 窗口内无 attempt 行 (请求直接命中成功)

### per-key 200 延迟 (5 key 全部健康)
| key | total | ok | avg_ok_ms | max_ms |
|---|---|---|---|---|
| k0 | 26 | 26 | 16745 | 45020 |
| k1 | 22 | 22 | 14763 | 53661 |
| k2 | 21 | 21 | 10778 | 26218 |
| k3 | 25 | 25 | 11916 | 19906 |
| k4 | 21 | 21 | 9494 | 17510 |

**无单 key 劣化** — 5 key 全部 100% 出 200, 延迟接近 (9.5-16.7s)。

### per-key 错误 (30min)
| key | error_type | count | avg_ms |
|---|---|---|---|
| k0 | all_tiers_exhausted | 2 | 178369 |
| k4 | stream_absolute_cap | 1 | 157510 |

归因 k0/k4 但 k0 26×200、k4 21×200 全成功 → **均为整 tier 偶发远端长 hold/cap**, 非 key 单点故障。

### key_cycle_429s 分布
0=8, 1=108, 3=2

**k1=108 为轮转伪影** (与 R1080-R1086 一致, 连续 8 轮): k1 为轮转首 key, 每请求先 429-probe 后 fast-break 切走; k1 本窗 0 错误 + 22×200 全成功 → 非真实劣化。

### 趋势 (持续稳定)
| 时段 | total | ok | err | SR |
|---|---|---|---|---|
| 02:00 | 198 | 195 | 3 | 98.5% |
| 03:00 | 295 | 288 | 7 | 97.6% |
| 04:00 | 285 | 279 | 6 | 97.9% |
| 05:00 | 52 | 50 | 2 | 96.2% |
| 30min | 118 | 115 | 3 | **97.5%** |
| 6h | 1595 | 1543 | 52 | **96.7%** |

24h all_tiers_exhausted=378 (较 R1086 的 381 基本持平, 累计趋缓)。

### fallback 日志 (hm4104, 最近 5min)
采集窗口内有 **1 次 fallback 触发** (13:09):
```
{"ts": "2026-08-07T13:09:16.890055", "tag": "PRIMARY-FAIL-STREAM", "msg": "nv_gw 流式 server_5xx status=502 after 180067ms, 切 fallback: upstream 502"}
{"ts": "2026-08-07T13:09:31.858013", "tag": "FALLBACK-STREAM", "msg": "从 primary 切到 ms_gw 流式, 提醒插入首 delta 前"}
```
**归因**: 该 fallback 来自 **主 nv_gw (40006)** 链路的 502 (after ~180s = TIER_TIMEOUT_BUDGET 烧尽), 非本容器 (40666) 直接故障。40766 自身窗口内 118 请求 115 成功, 无泄露。单次事件, 非"频繁触发", 不到动作阈值。

## 2. 根因判定 (改前必有数据)

延续 R1021-R1086 的 **NVCF deepseek-v4-flash-0731 特异性劣化缓释期** (function_id 52e1ddb6):
1. **SR 97.5%, 6h 96.7% 且逐小时稳定** (98.5%→97.6%→97.9%→96.2%) — 上游持续稳定, 无回归。
2. **错误仅 3 次/30min** (all_tiers_exhausted=2 + stream_absolute_cap=1), 归因 k0/k4 但两 key 均 100% 出 200 → 整 tier 偶发远端长 hold/cap。
3. **429 = 0**, fast-break 先耗尽 key, 无 429 冷却杠杆空间。
4. **k1 key_cycle_429s=108 为轮转伪影** (连续 8 轮确认), k1 0 错误 22×200 → 非真实劣化。
5. **本容器窗口内 118/118 全命中成功, 自身无泄露**; 13:09 的 1 次 fallback 归因主 nv_gw (40006) 非 40666。

## 3. 决策: NOP (无参数修改)

30min SR 97.5% > 95% NOP 阈值, 延迟稳定 (p50 10.1s), 无单 key 劣化, 趋势稳定无回归。
本容器链路自消化, 无单参数 lever 有数据支撑需调整。

维持 R1067 最佳配置 (UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET=180, NVU_TIER_BUDGET_DSV4F0731_NV=180,
KEY_COOLDOWN=30, TIER_COOLDOWN=90, CONN fast-break=5, 429 base/max=120, EMPTY_200 fast-break=3),
等待 NVCF deepseek-v4-flash-0731 function 完全恢复。

**不采取 integrate 旁路**: all_tiers_exhausted + stream_absolute_cap 均在 pexec 路径上偶发,
integrate 0 请��, 无 integrate 对照数据 → 无数据支撑切换。

**不调整 EMPTY_200_FASTBREAK**: 本窗口无 empty_200 (较 R1086 的 2 次进一步回落), 无动作。

**不调整 TIER budget**: all_tiers_exhausted 为 180s budget 烧尽, 提高 budget 只会让 502 更晚
出现而不增成功率; 97.5% SR 下无收益。

## 4. 验证

- [x] `/health` OK, 5 keys, proxy_role=passthrough, port=40666
- [x] 容器 dsvf0731_nv40666 Up 20 hours, 无重启, 无 env 改动
- [x] 30min SR=97.5%, 6h SR=96.7%, 延迟稳定 (p50 10.1s)
- [x] 本容器自身无 fallback 泄露 (13:09 单次 fallback 归因主 nv_gw 40006, 非 40666)

## 5. 下一步建议

- 上游持续稳定, 保持 NOP 观察。若 6h SR 稳定 >95% 连续 2-3 轮, 可延长 NOP 轮间隔。
- 关注主 nv_gw (40006) 13:09 的 502 (180s budget 烧尽) 是否反复: 若 hm4104 fallback 频繁
  (单轮 >3 次), 需评估 40006 侧 TIER_TIMEOUT_BUDGET, 但该容器 (40666) 参数不受影响。
- 若 dsv4f0731_nv 自身 all_tiers_exhausted 单轮 >10 次 (SR<92%) 回归, 再评估 integrate.api 旁路
  (NV_KEY_INTEGRATE_KEYS) — 当前无需干预。