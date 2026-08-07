# R1091: dsv4f0731_nv self-opt — NOP (SR 97.4% 健康, 错误仅 4 次偶发, 429=0, 无单 key 劣化)

日期: 2026-08-07 ~16:18 (BJT) = ~08:18 UTC

## 1. 数据 (30min 窗口)

### 主指标 (nv_requests)
- **SR = 97.4% (147/151)**, avg=16427ms, p50=10076ms, **p95=45987ms**, max=180050ms
- 30min 错误: **all_tiers_exhausted=3** (avg 180056 ≈ 180s budget 烧尽), **NVStream_IncompleteRead=1** (avg 126466)
- **429 计数 = 0** (无 429 冷却杠杆)
- upstream_type: 100% nvcf_pexec (151/151), **integrate 0 请求**
- finish_reason: tool_calls=127, stop=20 (正常)

### per-key 200 延迟 (5 key 全部健康)
| key | total | ok | avg_ok_ms | max_ms |
|---|---|---|---|---|
| k0 | 31 | 31 | 13165 | 36111 |
| k1 | 30 | 30 | 9577 | 15342 |
| k2 | 32 | 32 | 13983 | 30280 |
| k3 | 29 | 29 | 11040 | 22824 |
| k4 | 33 | 33 | 13443 | 35897 |

**无单 key 劣化** — 5 key 全部 100% 出 200, 延迟接近 (9.6-14.0s)。

### per-key 错误 (30min)
| key | error_type | count | avg_ms |
|---|---|---|---|
| k0 | all_tiers_exhausted | 3 | 180056 |
| k0 | NVStream_IncompleteRead | 1 | 126466 |

归因 k0 但 k0 31×200 全成功 → 均为整 tier 偶发远端长 hold/流截断, 非 key 单点故障 (与 R1089 同模式)。

### key_cycle_429s 分布
0=18, 1=131, 2=2

**k1=131 为轮转伪影** (与 R1080-R1090 一致, 连续 11 轮): k1 为轮转首 key, 每请求先 429-probe
后 fast-break 切走; k1 本窗 0 错误 + 30×200 全成功 → 非真实劣化。

### 趋势 (持续稳定)
| 时段 | total | ok | err | SR | avg_ok_ms |
|---|---|---|---|---|---|
| 05:00 | 175 | 172 | 3 | 98.3% | 13159 |
| 06:00 | 273 | 265 | 8 | 97.1% | 14338 |
| 07:00 | 262 | 253 | 9 | 96.6% | 12557 |
| 08:00 | 90 | 87 | 3 | 96.7% | 10850 |
| 30min | 151 | 147 | 4 | **97.4%** | - |
| 6h | 1629 | 1587 | 42 | **97.4%** | - |

24h all_tiers_exhausted=345 (与 R1090 持平, 累计趋缓)。

### fallback 日志 (hm4104, 最近 5min)
**1× fallback 触发**:
```
FALLBACK-STREAM 从 primary 切到 ms_gw 流式, 提醒插入首 delta 前
```
1× 单发 fallback, 对应 30min 窗口 all_tiers_exhausted 之一 (180s TIER budget 烧尽),
单发偶发, 非模式性。R1089/R1090 均为 ≤1×, 连续多轮低位稳定。

## 2. 根因判定 (改前必有数据)

延续 R1021-R1090 的 **NVCF deepseek-v4-flash-0731 特异性缓释期** (function_id 52e1ddb6):
1. **SR 97.4%, 6h 97.4% 且逐小时稳定** (98.3%→97.1%→96.6%→96.7%) — 上游持续稳定, 无回归。
2. **错误仅 4 次/30min** (all_tiers_exhausted=3 + NVStream_IncompleteRead=1), 归因 k0 但 k0 31×200 全成功 → 整 tier 偶发远端长 hold/流截断。
3. **429 = 0**, fast-break 先耗尽 key, 无 429 冷却杠杆空间。
4. **k1 key_cycle_429s=131 为轮转伪影** (连续 11 轮确认), k1 0 错误 30×200 → 非真实劣化。
5. **hm4104 fallback 仅 1×** — 单发 502 @180s budget 边界, 非模式性泄露。

## 3. 决策: NOP (无参数修改)

30min SR 97.4% > 95% NOP 阈值, 延迟稳定 (p50 10.1s), 无单 key 劣化, 趋势稳定无回归,
fallback 1× 为单发偶发。无单参数 lever 有数据支撑需调整。

维持 R1067 最佳配置 (UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET=180, NVU_TIER_BUDGET_DSV4F0731_NV=180,
KEY_COOLDOWN=30, TIER_COOLDOWN=90, 429 base/max=120, EMPTY_200 fast-break=3, PEXEC fast-break=3),
等待 NVCF deepseek-v4-flash-0731 function 完全恢复。

**不采取 integrate 旁路**: all_tiers_exhausted + NVStream_IncompleteRead 均在 pexec 路径上偶发,
integrate 0 请求, 无 integrate 对照数据 → 无数据支撑切换。

**不调整 TIER budget**: 单次 all_tiers_exhausted 为 180s budget 烧尽, 提高 budget 只会让 502
更晚出现而不增成功率; 97.4% SR 下无收益。

## 4. 验证

- [x] `/health` OK, 5 keys, proxy_role=passthrough, port=40666
- [x] 容器 dsvf0731_nv40666 Up 23 hours, 无重启, 无 env 改动
- [x] 30min SR=97.4%, 6h SR=97.4%, 延迟稳定 (p50 10.1s)
- [x] hm4104 fallback=1 (单发 @180s budget 边界, 非模式性)

## 5. 下一步建议

- 上游持续稳定, 保持 NOP 观察。若 6h SR 稳定 >95% 连续多轮, 可延长 NOP 轮间隔。
- 关注 NVStream_IncompleteRead: 本窗口 1 次, 单发流截断, 偶发意义, 无动作。若单轮 >3 次
  需评估 UPSTREAM_TIMEOUT 是否不足 (当前 90s, 本 error avg 126s > 90s, 为远端主动截断非超时)。
- 若 dsv4f0731_nv 自身 all_tiers_exhausted 单轮 >10 次 (SR<92%) 回归, 或 hm4104 fallback 连续
  多轮 >2%, 再评估 integrate.api 旁路 (NV_KEY_INTEGRATE_KEYS) — 当前无需干预。