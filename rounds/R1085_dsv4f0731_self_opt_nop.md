# R1085: dsv4f0731_nv self-opt — NOP (SR 98.7% 健康稳定, 错误各 1 次偶发, 无 fallback, 趋势上行)

日期: 2026-08-07 ~12:06 (BJT) = ~04:06 UTC

## 1. 数据 (30min 窗口 采集)

### 主指标
- **SR = 98.7% (151/153)**, avg=15424ms, p50=9667ms, **p95=58470ms**
- 30min 错误: **all_tiers_exhausted=1** (avg 174163), **zombie_empty_completion=1** (avg 39596)
- **429 计数 = 0** (无 429 冷却杠杆)
- upstream_type: 100% nvcf_pexec (153/153), **integrate 0 请求**
- finish_reason: tool_calls=125, stop=26 (正常)
- tier_attempts: 窗口内无 attempt 行 (请求直接命中成功)

### per-key 200 延迟 (5 key 全部健康)
| key | total | ok | avg_ok_ms | max_ms |
|---|---|---|---|---|
| k0 | 32 | 32 | 15595 | 55839 |
| k1 | 29 | 29 | 11021 | 13669 |
| k2 | 31 | 31 | 14331 | 51682 |
| k3 | 28 | 28 | 12100 | 23992 |
| k4 | 31 | 31 | 17560 | 78074 |

**无单 key 劣化** — 5 key 全部 100% 出 200, 延迟接近 (11.0-17.6s)。

### per-key 错误 (30min)
| key | error_type | count | avg_ms |
|---|---|---|---|
| k0 | all_tiers_exhausted | 1 | 174163 |
| k0 | zombie_empty_completion | 1 | 39596 |

各错误类型各 1 次, 归因 k0 但 k0 本窗 32×200 全成功 → **均为整 tier 偶发远端长 hold**, 非 key 单点故障。

### key_cycle_429s 分布
0=17, 1=134, 2=2

**k1=134 为轮转伪影** (与 R1080-R1084 一致, 连续 6 轮): k1 为轮转首 key, 每请求先 429-probe 后 fast-break 切走; k1 本窗 0 错误 + 29×200 全成功 → 非真实劣化。

### 趋势 (持续上行, 恢复稳定)
| 时段 | total | ok | err | SR |
|---|---|---|---|---|
| 01:00 | 224 | 214 | 10 | 95.5% |
| 02:00 | 261 | 256 | 5 | 98.1% |
| 03:00 | 295 | 288 | 7 | 97.6% |
| 04:00 | 32 | 31 | 1 | 96.9% |
| 30min | 153 | 151 | 2 | **98.7%** |
| 6h | 1493 | 1419 | 74 | **95.0%** |

24h all_tiers_exhausted=409 (历史累计, 非当前风暴)。

### fallback 日志 (hm4104, 最近 5min)
**(无 fallback 日志)** — 30min 窗口内 hm4104 无 fallback 触发, 本容器错误全部由自身消化。

## 2. 根因判定 (改前必有数据)

延续 R1021-R1084 的 **NVCF 模型特异性劣化风暴** (function_id 52e1ddb6) 缓释期:
1. **SR 98.7%, 6h 95.0% 且逐小时上行** (95.5%→98.1%→97.6%) — 上游持续恢复、稳定。
2. **错误仅 2 次/30min** (all_tiers_exhausted=1 预算烧尽 + zombie_empty_completion=1 空 200), 归因 k0 但 k0 32×200 全成功 → 非 key 单点, 为整 tier 偶发远方长 hold。
3. **429 = 0**, fast-break 先耗尽 key, 无 429 冷却杠杆空间。
4. **k1 key_cycle_429s=134 为轮转伪影** (连续 6 轮确认), k1 0 错误 29×200 → 非真实劣化。
5. **pexec_success 链路健康** (avg 延迟 11.0-17.6s), 故障仅在 NVCF function 远端偶发长 hold。
6. **本窗口 hm4104 fallback=0** — 链路完全自消化。

## 3. 决策: NOP (无参数修改)

30min SR 98.7% > 95% NOP 阈值, 延迟稳定 (p50 9.7s), 无单 key 劣化, 趋势上行, 且本窗口 **hm4104 fallback=0**。无单参数 lever 有数据支撑需调整。

维持 R1067 最佳配置 (UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET=180, NVU_TIER_BUDGET_DSV4F0731_NV=180,
KEY_COOLDOWN=30, TIER_COOLDOWN=90, CONN fast-break=5, 429 base/max=120, EMPTY_200 fast-break=3),
等待 NVCF deepseek-v4-flash-0731 function 完全恢复。

**不采取 integrate 旁路**: stream_absolute_cap + all_tiers_exhausted 均在 pexec 路径上偶发,
integrate 0 请求, 无 integrate 对照数据 → 无数据支撑切换。

**不调整 TIER budget**: 单次 all_tiers_exhausted 为 180s budget 烧尽, 提高 budget 只会让 502 更晚
出现而不增成功率; 降低预算会剪断本可成功的慢请求。98.7% SR 下无收益。

## 4. 验证

- [x] `/health` OK, 5 keys, proxy_role=passthrough, port=40666
- [x] 容器 dsvf0731_nv40666 Up 19 hours, 无重启, 无 env 改动
- [x] 30min SR=98.7%, 6h SR=95.0%, 延迟稳定 (p50 9.7s)
- [x] hm4104 fallback=0 (本窗口无 fallback 日志, 错误全由自身消化)

## 5. 下一步建议

- 上游持续恢复中, 保持 NOP 观察。若 6h SR 稳定 >95% 连续 2-3 轮, 可延长 NOP 轮间隔。
- 若 all_tiers_exhausted 单轮 >10 次 (SR<92%) 回归, 再评估 integrate.api 旁路
  (NV_KEY_INTEGRATE_KEYS) — 当前无需干预。
- 关注 zombie_empty_completion 是否累积: 若单轮 >3 次, 需评估 EMPTY_200_FASTBREAK=3 是否应
  下调 (当前 1 次, 偶发意义, 无动作)。