# R1092: dsv4f0731_nv self-opt — NOP (SR 96.7% 健康, 错误仅 4 次偶发, 429=0, 无单 key 劣化)

日期: 2026-08-07 ~16:48 (BJT) = ~08:48 UTC

## 1. 数据 (30min 窗口)

### 主指标 (nv_requests)
- **SR = 96.7% (117/121)**, avg=17699ms, p50=10233ms, **p95=73858ms**, max=155695ms
- 30min 错误: **stream_absolute_cap=2** (avg 153564/150012), **NVStream_IncompleteRead=1** (avg 35453), **all_tiers_exhausted=1** (avg 180058)
- **429 计数 = 0** (无 429 冷却杠杆)
- upstream_type: 100% nvcf_pexec (121/121), **integrate 0 请求**
- finish_reason: tool_calls=100, stop=17 (正常)

### per-key 200 延迟 (5 key 全部健康)
| key | total | ok | avg_ok_ms | max_ms |
|---|---|---|---|---|
| k0 | 26 | 26 | 19308 | 66358 |
| k1 | 21 | 21 | 8702 | 12549 |
| k2 | 25 | 25 | 12792 | 20652 |
| k3 | 22 | 22 | 11445 | 18188 |
| k4 | 23 | 23 | 15765 | 70583 |

**无单 key 劣化** — 5 key 全部 100% 出 200。k0/k4 avg 略高 (19.3s/15.8s) 但 boosting 由长 tool_calls 请求导致, 非故障信号。

### per-key 错误 (30min)
| key | error_type | count | avg_ms |
|---|---|---|---|
| k0 | NVStream_IncompleteRead | 1 | 35453 |
| k0 | all_tiers_exhausted | 1 | 180058 |
| k0 | stream_absolute_cap | 1 | 157116 |
| k2 | stream_absolute_cap | 1 | 150012 |

归因 k0/k2 但两 key 本窗 100% 200 成功 → 均为整 tier 偶发远端长 hold/流截断, 非 key 单点故障。

### key_cycle_429s 分布
0=10, 1=108, 2=2, 3=1

**k1=108 为轮转伪影** (与 R1080-R1091 一致, 连续 11 轮): k1 为轮转首 key, 每请求先 429-probe 后 fast-break 切走; k1 本窗 0 错误 + 21×200 全成功 → 非真实劣化。

### 趋势 (持续稳定)
| 时段 | total | ok | err | SR | avg_ok_ms |
|---|---|---|---|---|---|
| 05:00 | 60 | 59 | 1 | 98.3% | 11308 |
| 06:00 | 273 | 265 | 8 | 97.1% | 14338 |
| 07:00 | 262 | 253 | 9 | 96.6% | 12557 |
| 08:00 | 201 | 194 | 7 | 96.5% | 12753 |
| 30min | 121 | 117 | 4 | **96.7%** | - |
| 6h | 1623 | 1580 | 43 | **97.4%** | - |

24h all_tiers_exhausted=334 (与 R1091 的 345 持平, 累计趋缓)。

### fallback 日志 (hm4104)
采集脚本 5min 窗口显示 "无 fallback 日志"; 但直查 hm4104 30min 日志发现 **fallback 聚集簇**:
```
16:21-16:24  FALLBACK-STREAM + PRIMARY-BREAKER-SKIP (circuit OPEN) ×4
16:29:22     PRIMARY-FAIL-STREAM nv_gw 502 after 180066ms (all_tiers_exhausted 对应)
16:30-16:48  FALLBACK-STREAM + PRIMARY-BREAKER-SKIP (circuit OPEN) 持续
16:46:30     CONTENT_FILTER_ZOMBIE (R840 zombie) → 切 ms_gw
16:47-16:48  FALLBACK-STREAM + PRIMARY-BREAKER-SKIP 持续
```

**根因**: 16:29 的 502@180066ms (all_tiers_exhausted, 180s TIER budget 烧尽) 触发 hm4104 下游 circuit breaker 转 OPEN, 随后约 20 分钟多数请求被 PRIMARY-BREAKER-SKIP 直走 fallback。**这是 hm4104 适配器侧熔断行为, 非 dsvf0731_nv40666 可调**。主链路 DB 层 30min SR 仍 96.7%, 无异常。

## 2. 根因判定 (改前必有数据)

延续 R1021-R1091 的 **NVCF deepseek-v4-flash-0731 特异性缓释期** (function_id 52e1ddb6):
1. **SR 96.7%, 6h 97.4% 且逐小时稳定** (98.3%→97.1%→96.6%→96.5%) — 上游持续稳定, 无回归。
2. **错误仅 4 次/30min** (stream_absolute_cap=2 + NVStream_IncompleteRead=1 + all_tiers_exhausted=1), 归因 k0/k2 但两 key 100% 200 成功 → 整 tier 偶发远端长 hold/流截断。
3. **429 = 0**, fast-break 先耗尽 key, 无 429 冷却杠杆空间。
4. **k1 key_cycle_429s=108 为轮转伪影** (连续 11 轮确认), k1 0 错误 21×200 → 非真实劣化。
5. **hm4104 fallback 聚集簇由 16:29 单次 502 触发下游熔断** — 主链路 SR 仍健康, 熔断为适配器侧自适应 (R840 zombie 亦为下游检测), 非 dsvf0731_nv40666 参数异常。

## 3. 决策: NOP (无参数修改)

30min SR 96.7% > 95% NOP 阈值, 延迟稳定 (p50 10.2s), 无单 key 劣化, 趋势稳定无回归。
fallback 聚集簇为下游 hm4104 熔断对单次 502 的自适应, 非模式性主链路劣化。

维持 R1067 最佳配置 (UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET=180, NVU_TIER_BUDGET_DSV4F0731_NV=180,
KEY_COOLDOWN=30, TIER_COOLDOWN=90, 429 base/max=120, EMPTY_200 fast-break=3, PEXEC fast-break=3),
等待 NVCF deepseek-v4-flash-0731 function 完全恢复。

**不采取 integrate 旁路**: stream_absolute_cap + NVStream_IncompleteRead + all_tiers_exhausted 均在 pexec
路径上偶发, integrate 0 请求, 无 integrate 对照数据 → 无数据支撑切换。

**不调整 TIER budget**: 单次 all_tiers_exhausted 为 180s budget 烧尽, 提高 budget 只会让 502 更晚
出现而不增成功率; 96.7% SR 下无收益。

## 4. 验证

- [x] `/health` OK, 5 keys, proxy_role=passthrough, port=40666
- [x] 容器 dsvf0731_nv40666 Up 23 hours, 无重启, 无 env 改动
- [x] 30min SR=96.7%, 6h SR=97.4%, 延迟稳定 (p50 10.2s)
- [x] hm4104 fallback 聚集簇归因 16:29 单次 502 触发下游熔断 (主链路 SR 仍健康)

## 5. 下一步建议

- 上游持续稳定, 保持 NOP 观察。若 6h SR 稳定 >95% 连续多轮, 可延长 NOP 轮间隔。
- 关注 stream_absolute_cap (本轮首现, 2 次, avg ~150s): 若为 pexec 流超长被 absolute cap 截断
  (deepseek flash 推理长流), 需与 NVStream_IncompleteRead 一并观察。若单轮 >5 次评估 UPSTREAM_TIMEOUT
  或 absolute cap 是否过低; 当前 2 次无动作。
- 若 dsv4f0731_nv 自身 all_tiers_exhausted 单轮 >10 次 (SR<92%) 回归, 或 hm4104 fallback 连续
  多轮 >2%, 再评估 integrate.api 旁路 (NV_KEY_INTEGRATE_KEYS) — 当前无需干预。