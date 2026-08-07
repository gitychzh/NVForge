# R1086: dsv4f0731_nv self-opt — NOP (SR 97.9% 健康稳定, 错误各 1-2 次偶发, 无 fallback, 趋势稳定)

日期: 2026-08-07 ~13:00 (BJT) = ~05:00 UTC

## 1. 数据 (30min 窗口 采集)

### 主指标
- **SR = 97.9% (143/146)**, avg=16858ms, p50=10343ms, **p95=56759ms**, max=132789ms
- 30min 错误: **all_tiers_exhausted=1** (avg 176679), **zombie_empty_completion=2** (avg 6163)
- **429 计数 = 0** (无 429 冷却杠杆)
- upstream_type: 100% nvcf_pexec (146/146), **integrate 0 请求**
- finish_reason: tool_calls=121, stop=22 (正常)
- tier_attempts: 窗口内无 attempt 行 (请求直接命中成功)

### per-key 200 延迟 (5 key 全部健康)
| key | total | ok | avg_ok_ms | max_ms |
|---|---|---|---|---|
| k0 | 30 | 30 | 19360 | 81973 |
| k1 | 30 | 30 | 18467 | 57834 |
| k2 | 26 | 26 | 11250 | 27471 |
| k3 | 27 | 27 | 16469 | 59223 |
| k4 | 30 | 30 | 13341 | 38406 |

**无单 key 劣化** — 5 key 全部 100% 出 200, 延迟接近 (11.2-19.4s)。

### per-key 错误 (30min)
| key | error_type | count | avg_ms |
|---|---|---|---|
| k0 | all_tiers_exhausted | 1 | 176679 |
| k0 | zombie_empty_completion | 1 | 2958 |
| k3 | zombie_empty_completion | 1 | 9367 |

归因 k0/k3 但 k0 30×200、k3 27×200 全成功 → **均为整 tier 偶发远端长 hold/空 200**, 非 key 单点故障。

### key_cycle_429s 分布
0=17, 1=125, 2=2, 3=2

**k1=125 为轮转伪影** (与 R1080-R1085 一致, 连续 7 轮): k1 为轮转首 key, 每请求先 429-probe 后 fast-break 切走; k1 本窗 0 错误 + 30×200 全成功 → 非真实劣化。

### 趋势 (持续稳定)
| 时段 | total | ok | err | SR |
|---|---|---|---|---|
| 02:00 | 260 | 255 | 5 | 98.1% |
| 03:00 | 295 | 288 | 7 | 97.6% |
| 04:00 | 285 | 279 | 6 | 97.9% |
| 05:00 | 1 | 1 | 0 | 100% |
| 30min | 146 | 143 | 3 | **97.9%** |
| 6h | 1603 | 1550 | 53 | **96.7%** |

24h all_tiers_exhausted=381 (较 R1085 的 409 下降, 历史累计趋缓)。

### fallback 日志 (hm4104, 最近 5min)
**(无 fallback 日志)** — 30min 窗口内 hm4104 无 fallback 触发, 本容器 3 次错误全部由自身消化 (不同于 R1084 的 content_filter 兜底, 本窗口无泄露)。

## 2. 根因判定 (改前必有数据)

延续 R1021-R1085 的 **NVCF 模型特异性劣化风暴** (function_id 52e1ddb6) 缓释期:
1. **SR 97.9%, 6h 96.7% 且逐小时稳定** (98.1%→97.6%→97.9%) — 上游持续稳定, 无回归。
2. **错误仅 3 次/30min** (all_tiers_exhausted=1 + zombie_empty_completion=2), 归因 k0/k3 但两 key 均 100% 出 200 → 整 tier 偶发远端长 hold/空 200。
3. **zombie_empty_completion=2 较 R1085 的 1 轻微上升**, 但仍远低于 3 次动作阈值, 且本窗口 hm4104 fallback=0 → 链路自消化, 无泄露。
4. **429 = 0**, fast-break 先耗尽 key, 无 429 冷却杠杆空间。
5. **k1 key_cycle_429s=125 为轮转伪影** (连续 7 轮确认), k1 0 错误 30×200 → 非真实劣化。
6. **本窗口 hm4104 fallback=0** — 链路完全自消化。

## 3. 决策: NOP (无参数修改)

30min SR 97.9% > 95% NOP 阈值, 延迟稳定 (p50 10.3s), 无单 key 劣化, 趋势稳定无回归,
且本窗口 **hm4104 fallback=0**。无单参数 lever 有数据支撑需调整。

维持 R1067 最佳配置 (UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET=180, NVU_TIER_BUDGET_DSV4F0731_NV=180,
KEY_COOLDOWN=30, TIER_COOLDOWN=90, CONN fast-break=5, 429 base/max=120, EMPTY_200 fast-break=3),
等待 NVCF deepseek-v4-flash-0731 function 完全恢复。

**不采取 integrate 旁路**: all_tiers_exhausted + zombie_empty_completion 均在 pexec 路径上偶发,
integrate 0 请求, 无 integrate 对照数据 → 无数据支撑切换。

**不调整 EMPTY_200_FASTBREAK**: 当前 2 次/30min, 低于 3 次动作阈值, 下调会误伤正常批量空响应判断。

**不调整 TIER budget**: 单次 all_tiers_exhausted 为 180s budget 烧尽, 提高 budget 只会让 502 更晚
出现而不增成功率; 97.9% SR 下无收益。

## 4. 验证

- [x] `/health` OK, 5 keys, proxy_role=passthrough, port=40666
- [x] 容器 dsvf0731_nv40666 Up 19 hours, 无重启, 无 env 改动
- [x] 30min SR=97.9%, 6h SR=96.7%, 延迟稳定 (p50 10.3s)
- [x] hm4104 fallback=0 (本窗口无 fallback 日志, 错误全由自身消化)

## 5. 下一步建议

- 上游持续稳定, 保持 NOP 观察。若 6h SR 稳定 >95% 连续 2-3 轮, 可延长 NOP 轮间隔。
- 关注 zombie_empty_completion 是否持续累积: 若单轮 >3 次, 需评估 EMPTY_200_FASTBREAK=3 是否应
  下调 (本窗口 2 次, 偶发意义, 无动作)。
- 若 all_tiers_exhausted 单轮 >10 次 (SR<92%) 回归, 再评估 integrate.api 旁路
  (NV_KEY_INTEGRATE_KEYS) — 当前无需干预。