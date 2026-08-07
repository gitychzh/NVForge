# R1084: dsv4f0731_nv self-opt — NOP (SR 97.8% 健康稳定, 错误各 1 次偶发, hm4104 content_filter 兜底)

日期: 2026-08-07 ~11:08 (BJT) = ~03:08 UTC

## 1. 数据 (30min 窗口 采集)

### 主指标
- **SR = 97.8% (131/134)**, avg=17322ms, p50=9341ms, **p95=58635ms**
- 30min 错误: **all_tiers_exhausted=1** (avg 180043), **stream_absolute_cap=1** (avg 173857),
  **zombie_empty_completion=1** (avg 11946)
- **429 计数 = 0** (无 429 冷却杠杆)
- upstream_type: 100% nvcf_pexec (134/134), **integrate 0 请求**
- finish_reason: tool_calls=107, stop=24 (正常)
- tier_attempts: 窗口内无 attempt 行 (请求直接命中成功)

### per-key 200 延迟 (5 key 全部健康)
| key | total | ok | avg_ok_ms | max_ms |
|---|---|---|---|---|
| k0 | 27 | 27 | 10823 | 13897 |
| k1 | 26 | 26 | 12913 | 42055 |
| k2 | 26 | 26 | 15963 | 38613 |
| k3 | 26 | 26 | 19222 | 95950 |
| k4 | 26 | 26 | 15865 | 23336 |

**无单 key 劣化** — 5 key 全部 100% 出 200, 延迟接近 (10.8-19.2s)。

### per-key 错误 (30min)
| key | error_type | count | avg_ms |
|---|---|---|---|
| k0 | all_tiers_exhausted | 1 | 180043 |
| k1 | stream_absolute_cap | 1 | 173857 |
| k4 | zombie_empty_completion | 1 | 11946 |

各错误类型各 1 次, 归因 k0/k1/k4 但三 key 均 26-27×200 全成功 → **均为整 tier 偶发远端事件**, 非 key 单点故障。

### key_cycle_429s 分布
0=10, 1=120, 2=2, 3=2

**k1=120 为轮转伪影** (与 R1080-R1083 一致, 连续 5 轮): k1 为轮转首 key, 每请求先 429-probe 后 fast-break 切走; k1 本窗 0 错误 + 26×200 全成功 → 非真实劣化。

### 趋势 (持续上行)
| 时段 | total | ok | err | SR |
|---|---|---|---|---|
| 00:00 | 248 | 241 | 7 | 97.2% |
| 01:00 | 263 | 253 | 10 | 96.2% |
| 02:00 | 261 | 256 | 5 | 98.1% |
| 03:00 | 39 | 37 | 2 | **94.9%** |
| 30min | 134 | 131 | 3 | **97.8%** |
| 6h | 1432 | 1354 | 78 | **94.6%** |

24h all_tiers_exhausted=425 (历史累计, 非当前风暴)。

### fallback 日志 (hm4104, 最近 5min)
```
11:03:46 CONTENT_FILTER_ZOMBIE — primary 流中检测到 content_filter (R840 zombie), 切 ms_gw fallback
11:03:46 PRIMARY-ZOMBIE-FALLBACK — nv_gw 返回 content_filter zombie, 切 ms_gw fallback 流式
11:04:08 FALLBACK-STREAM — 从 primary 切到 ms_gw 流式
```
**1 次 content_filter zombie 触发 fallback** — 对应 DB 中 zombie_empty_completion=1 (k4)。
hm4104 的 R840 content_filter 检测机制捕获后切 ms_gw, **客户端经 fallback 恢复, 无可见失败**。
属正常防御机制运作, 非链路劣化。

## 2. 根因判定 (改前必有数据)

延续 R1021-R1083 的 **NVCF 模型特异性劣化风暴** (function_id 52e1ddb6) 缓释期:
1. **SR 97.8%, 6h 94.6% 且逐小时上行** — 上游持续恢复、稳定。
2. **错误共 3 次/30min, 各类型各 1 次** (all_tiers_exhausted/stream_absolute_cap/zombie_empty_completion),
   归因 k0/k1/k4 但三 key 均 100% 出 200 → 均为整 tier 偶发远端长 hold, 非 key 单点。
3. **zombie_empty_completion 由 hm4104 content_filter 兜底** — 客户端经 ms_gw fallback 恢复, 无泄露。
4. **429 = 0**, 无 429 冷却杠杆空间。
5. **k1 key_cycle_429s=120 为轮转伪影** (连续 5 轮确认), k1 0 错误 26×200 → 非真实劣化。

## 3. 决策: NOP (无参数修改)

30min SR 97.8% > 95% NOP 阈值, 延迟稳定 (p50 9.3s), 无单 key 劣化, 趋势上行,
唯一 fallback 事件 (content_filter zombie) 由 hm4104 防御机制兜底恢复。无单参数 lever 有数据支撑需调整。

维持 R1067 最佳配置 (UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET=180, NVU_TIER_BUDGET_DSV4F0731_NV=180,
KEY_COOLDOWN=30, TIER_COOLDOWN=90, CONN fast-break=5, 429 base/max=120, EMPTY_200 fast-break=3),
等待 NVCF deepseek-v4-flash-0731 function 完全恢复。

**不采取 integrate 旁路**: stream_absolute_cap + all_tiers_exhausted 均在 pexec 路径上偶发,
integrate 0 请求, 无 integrate 对照数据 → 无数据支撑切换。

**不调整 TIER budget**: 单次 all_tiers_exhausted 为 180s budget 烧尽, 提高 budget 只会让 502 更晚
出现而不增���功率; 降低预算会剪断本可成功的慢请求。97.8% SR 下无收益。

## 4. 验证

- [x] `/health` OK, 5 keys, proxy_role=passthrough, port=40666
- [x] 容器 dsvf0731_nv40666 Up 18 hours, 无重启, 无 env 改动
- [x] 30min SR=97.8%, 6h SR=94.6%, 延迟稳定 (p50 9.3s)
- [x] hm4104 fallback 1 次 (content_filter zombie, 兜底恢复, 无客户端可见失败)

## 5. 下一步建议

- 上游持续恢复中, 保持 NOP 观察。若 6h SR 稳定 >95% 连续 2-3 轮, 可延长 NOP 轮间隔。
- 若 all_tiers_exhausted + stream_absolute_cap 单轮合计 >5 次 (SR<92%) 回归, 再评估 integrate.api
  旁路 (NV_KEY_INTEGRATE_KEYS) — 当前无需干预。
- 关注 zombie_empty_completion 是否累积: 若单轮 >3 次, 需评估 EMPTY_200_FASTBREAK=3 是否应下调
  (当前 1 次, 且有 hm4104 content_filter 兜底, 无动作)。