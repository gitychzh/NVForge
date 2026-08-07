# R1089: dsv4f0731_nv self-opt — NOP (SR 97.1% 健康, 错误仅 4 次偶发, 429=0, 无单 key 劣化)

日期: 2026-08-07 ~14:12 (BJT) = ~06:12 UTC

## 1. 数据 (30min 窗口 采集)

### 主指标
- **SR = 97.1% (133/137)**, avg=15394ms, p50=9726ms, **p95=42494ms**, max=179845ms
- 30min 错误: **all_tiers_exhausted=3** (avg 179862 ≈ 180s budget 烧尽), **NVStream_IncompleteRead=1** (avg 76324)
- **429 计数 = 0** (无 429 冷却杠杆)
- upstream_type: 100% nvcf_pexec (137/137), **integrate 0 请求**
- finish_reason: tool_calls=113, stop=20 (正常)
- tier_attempts: 窗口内无 attempt 行 (请求直接命中成功)

### per-key 200 延迟 (5 key 全部健康)
| key | total | ok | avg_ok_ms | max_ms |
|---|---|---|---|---|
| k0 | 26 | 26 | 9634 | 15753 |
| k1 | 28 | 28 | 13687 | 36813 |
| k2 | 24 | 24 | 7461 | 11205 |
| k3 | 29 | 29 | 14628 | 33718 |
| k4 | 26 | 26 | 9847 | 15828 |

**无单 key 劣化** — 5 key 全部 100% 出 200, 延迟接近 (7.5-14.6s)。

### per-key 错误 (30min)
| key | error_type | count | avg_ms |
|---|---|---|---|
| k0 | all_tiers_exhausted | 3 | 179862 |
| k0 | NVStream_IncompleteRead | 1 | 76324 |

归因 k0 但 k0 26×200 全成功 → 均为整 tier 偶发远端长 hold/流截断, 非 key 单点故障。

### key_cycle_429s 分布
0=10, 1=126, 2=1

**k1=126 为轮转伪影** (与 R1080-R1088 一致, 连续 10 轮): k1 为轮转首 key, 每请求先 429-probe
后 fast-break 切走; k1 本窗 0 错误 + 28×200 全成功 → 非真实劣化。

### 趋势 (持续稳定)
| 时段 | total | ok | err | SR |
|---|---|---|---|---|
| 03:00 | 234 | 230 | 4 | 98.3% |
| 04:00 | 285 | 279 | 6 | 97.9% |
| 05:00 | 249 | 243 | 6 | 97.6% |
| 06:00 | 55 | 53 | 2 | 96.4% |
| 30min | 137 | 133 | 4 | **97.1%** |
| 6h | 1646 | 1604 | 42 | **97.4%** |

24h all_tiers_exhausted=367 (与 R1088 的 368 持平, 累计趋缓)。

### fallback 日志 (hm4104, 最近 5min)
**1× fallback 触发**:
```
PRIMARY-FAIL-STREAM nv_gw 流式 server_5xx status=502 after 179459ms → 切 ms_gw
```
该 502 对应 30min 窗口的 all_tiers_exhausted=3 之一 (179459ms ≈ 180s TIER budget 烧尽),
单发偶发, 非模式性。R1088 本窗口 fallback=0, 本轮 1/137 (=0.7%) 略升但远低于干预阈值。

## 2. 根因判定 (改前必有数据)

延续 R1021-R1088 的 **NVCF deepseek-v4-flash-0731 特异性缓释期** (function_id 52e1ddb6):
1. **SR 97.1%, 6h 97.4% 且逐小时稳定** (98.3%→97.9%→97.6%→96.4%) — 上游持续稳定, 无回归。
2. **错误仅 4 次/30min** (all_tiers_exhausted=3 + NVStream_IncompleteRead=1), 归因 k0 但 k0 26×200 全成功 → 整 tier 偶发远端长 hold/流截断。
3. **429 = 0**, fast-break 先耗尽 key, 无 429 冷却杠杆空间。
4. **k1 key_cycle_429s=126 为轮转伪影** (连续 10 轮确认), k1 0 错误 28×200 → 非真实劣化。
5. **hm4104 fallback 仅 1× (0.7%)** — 单发 502 @180s budget 边界, 非模式性泄露。

## 3. 决策: NOP (无参数修改)

30min SR 97.1% > 95% NOP 阈值, 延迟稳定 (p50 9.7s), 无单 key 劣化, 趋势稳定无回归,
fallback 1× 为单发偶发 (0.7% < 干预阈值)。无单参数 lever 有数据支撑需调整。

维持 R1067 最佳配置 (UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET=180, NVU_TIER_BUDGET_DSV4F0731_NV=180,
KEY_COOLDOWN=30, TIER_COOLDOWN=90, CONN fast-break=5, 429 base/max=120, EMPTY_200 fast-break=3),
等待 NVCF deepseek-v4-flash-0731 function 完全恢复。

**不采取 integrate 旁路**: all_tiers_exhausted + NVStream_IncompleteRead 均在 pexec 路径上偶发,
integrate 0 请求, 无 integrate 对照数据 → 无数据支撑切换。

**不调整 TIER budget**: 单次 all_tiers_exhausted 为 180s budget 烧尽, 提高 budget 只会让 502 更晚
出现而不增成功率; 97.1% SR 下无收益。

## 4. 验证

- [x] `/health` OK, 5 keys, proxy_role=passthrough, port=40666
- [x] 容器 dsvf0731_nv40666 Up 21 hours, 无重启, 无 env 改动
- [x] 30min SR=97.1%, 6h SR=97.4%, 延迟稳定 (p50 9.7s)
- [x] hm4104 fallback=1 (单发 502 @180s budget 边界, 0.7%, 非模式性)

## 5. 下一步建议

- 上游持续稳定, 保持 NOP 观察。若 6h SR 稳定 >95% 连续多轮, 可延长 NOP 轮间隔。
- 关注 NVStream_IncompleteRead: 本窗口 1 次, 单发流截断, 偶发意义, 无动作。若单轮 >3 次
  需评估 UPSTREAM_TIMEOUT 是否不足 (当前 90s, 本 error avg 76s < 90s, 属远端主动截断非超时)。
- 若 dsv4f0731_nv 自身 all_tiers_exhausted 单轮 >10 次 (SR<92%) 回归, 或 hm4104 fallback 连���
  多轮 >2%, 再评估 integrate.api 旁路 (NV_KEY_INTEGRATE_KEYS) — 当前无需干预。