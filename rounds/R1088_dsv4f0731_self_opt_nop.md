# R1088: dsv4f0731_nv self-opt — NOP (SR 97.6% 健康稳定, 错误仅 3 次偶发, 429=0, fallback=0, 无单 key 劣化)

日期: 2026-08-07 ~14:00 (BJT) = ~06:00 UTC

## 1. 数据 (30min 窗口 采集)

### 主指标
- **SR = 97.6% (124/127)**, avg=16026ms, p50=9858ms, **p95=43371ms**, max=167772ms
- 30min 错误: **all_tiers_exhausted=2** (avg 179585), **NVStream_IncompleteRead=1** (avg 76324)
- **429 计数 = 0** (无 429 冷却杠杆)
- upstream_type: 100% nvcf_pexec (127/127), **integrate 0 请求**
- finish_reason: tool_calls=101, stop=23 (正常)
- tier_attempts: 窗口内无 attempt 行 (请求直接命中成功)

### per-key 200 延迟 (5 key 全部健康)
| key | total | ok | avg_ok_ms | max_ms |
|---|---|---|---|---|
| k0 | 24 | 24 | 14458 | 16230 |
| k1 | 26 | 26 | 12241 | 22923 |
| k2 | 22 | 22 | 8061 | 12253 |
| k3 | 27 | 27 | 15105 | 34754 |
| k4 | 25 | 25 | 13978 | 23593 |

**无单 key 劣化** — 5 key 全部 100% 出 200, 延迟接近 (8.1-15.1s)。

### per-key 错误 (30min)
| key | error_type | count | avg_ms |
|---|---|---|---|
| k0 | all_tiers_exhausted | 2 | 179585 |
| k0 | NVStream_IncompleteRead | 1 | 76324 |

归因 k0 但 k0 24×200 全成功 → **均为整 tier 偶发远端长 hold/流截断**, 非 key 单点故障。

### key_cycle_429s 分布
0=7, 1=117, 2=3

**k1=117 为轮转伪影** (与 R1080-R1087 一致, 连续 9 轮): k1 为轮转首 key, 每请求先 429-probe
后 fast-break 切走; k1 本窗 0 错误 + 26×200 全成功 → 非真实劣化。

### 趋势 (持续稳定)
| 时段 | total | ok | err | SR |
|---|---|---|---|---|
| 03:00 | 295 | 288 | 7 | 97.6% |
| 04:00 | 285 | 279 | 6 | 97.9% |
| 05:00 | 249 | 243 | 6 | 97.6% |
| 06:00 | 1 | 1 | 0 | 100% |
| 30min | 127 | 124 | 3 | **97.6%** |
| 6h | 1643 | 1600 | 43 | **97.4%** |

24h all_tiers_exhausted=368 (较 R1087 的 378 下降, 累计趋缓)。

### fallback 日志 (hm4104, 最近 5min)
**(无 fallback 日志)** — 30min 窗口内 hm4104 无 fallback 触发, 本容器 3 次错误全部由自身消化。

## 2. 根因判定 (改前必有数据)

延续 R1021-R1087 的 **NVCF deepseek-v4-flash-0731 特异性劣化缓释期** (function_id 52e1ddb6):
1. **SR 97.6%, 6h 97.4% 且逐小时稳定** (97.6%→97.9%→97.6%) — 上游持续稳定, 无回归。
2. **错误仅 3 次/30min** (all_tiers_exhausted=2 + NVStream_IncompleteRead=1), 归因 k0 但 k0 24×200 全成功 → 整 tier 偶发远端长 hold/流截断。
3. **429 = 0**, fast-break 先耗尽 key, 无 429 冷却杠杆空间。
4. **k1 key_cycle_429s=117 为轮转伪影** (连续 9 轮确认), k1 0 错误 26×200 → 非真实劣化。
5. **本窗口 hm4104 fallback=0** — 链路完全自消化, 无泄露。

## 3. 决策: NOP (无参数修改)

30min SR 97.6% > 95% NOP 阈值, 延迟稳定 (p50 9.9s), 无单 key 劣化, 趋势稳定无回归,
且本窗口 **hm4104 fallback=0**。无单参数 lever 有数据支撑需调整。

维持 R1067 最佳配置 (UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET=180, NVU_TIER_BUDGET_DSV4F0731_NV=180,
KEY_COOLDOWN=30, TIER_COOLDOWN=90, CONN fast-break=5, 429 base/max=120, EMPTY_200 fast-break=3),
等待 NVCF deepseek-v4-flash-0731 function 完全恢复。

**不采取 integrate 旁路**: all_tiers_exhausted + NVStream_IncompleteRead 均在 pexec 路径上偶发,
integrate 0 请求, 无 integrate 对照数据 → 无数据支撑切换。

**不调整 TIER budget**: 单次 all_tiers_exhausted 为 180s budget 烧尽, 提高 budget 只会让 502 更晚
出现而不增成功率; 97.6% SR 下无收益。

## 4. 验证

- [x] `/health` OK, 5 keys, proxy_role=passthrough, port=40666
- [x] 容器 dsvf0731_nv40666 Up 20 hours, 无重启, 无 env 改动
- [x] 30min SR=97.6%, 6h SR=97.4%, 延迟稳定 (p50 9.9s)
- [x] hm4104 fallback=0 (本窗口无 fallback 日志, 错误全由自身消化)

## 5. 下一步建议

- 上游��续稳定, 保持 NOP 观察。若 6h SR 稳定 >95% 连续多轮, 可延长 NOP 轮间隔。
- 关注 NVStream_IncompleteRead: 本窗口 1 次, 单发流截断, 偶发意义, 无动作。若单轮 >3 次
  需评估 UPSTREAM_TIMEOUT 是否不足 (当前 90s, 本 error avg 76s < 90s, 属远端主动截断非超时)。
- 若 dsv4f0731_nv 自身 all_tiers_exhausted 单轮 >10 次 (SR<92%) 回归, 再评估 integrate.api 旁路
  (NV_KEY_INTEGRATE_KEYS) — 当前无需干预。