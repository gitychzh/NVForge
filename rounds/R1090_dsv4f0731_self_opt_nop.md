# R1090: dsv4f0731_nv self-opt — NOP (SR 98.5% 健康, 错误仅 4 次 budget 烧尽, 429=0, 无单 key 劣化)

日期: 2026-08-07 ~15:55 (BJT) = ~07:55 UTC

## 1. 数据 (30min 窗口)

### 主指标 (nv_requests)
- **SR = 98.5% (128/130)**, avg=16218ms, p50=9442ms, p95=37740ms, max=180082ms
- 30min 错误: **all_tiers_exhausted=3** (avg 178613 ≈ 180s budget 烧尽), **zombie_empty_completion=1** (114485)
- **429 计数 = 0** (无 429 冷却杠杆)
- upstream_type: 100% nvcf_pexec (133/133), **integrate 0 请求**
- finish_reason: tool_calls=113, stop=17 (正常)
- key_cycle_429s: 0=11, 1=121, 2=1 (k1=121 为轮转伪影, 连续多轮确认)

### tier_attempts (30min, error 分类)
| error_type | count | avg_ms | min_ms | max_ms |
|---|---|---|---|---|
| pexec_success | 118 | 3783 | 1064 | 8739 |
| NVCFPexecRemoteDisconnected | 13 | 42431 | 30500 | 76274 |
| NVCFPexecTimeout | 3 | 32492 | 28259 | 39824 |
| empty_200 | 2 | - | - | - |

**18 次失败 attempt 均被 fast-break 消化** → 仅 4 请求烧尽 180s budget 报 502。错误皆为 NVCF 远端瞬态 (RemoteDisconnected/Timeout/empty), 非 key 单点故障。

### 趋势 (6h 持续稳定)
| hour | total | ok | err | SR | avg_ok_ms |
|---|---|---|---|---|---|
| 02:00 | 261 | 256 | 5 | 98.1% | 15241 |
| 03:00 | 295 | 288 | 7 | 97.6% | 13498 |
| 04:00 | 285 | 279 | 6 | 97.9% | 14907 |
| 05:00 | 249 | 243 | 6 | 97.6% | 13479 |
| 06:00 | 273 | 265 | 8 | 97.1% | 14338 |
| 07:00 | 259 | 250 | 9 | 96.5% | 12225 |
| **6h** | **1624** | **1583** | **41** | **97.5%** | - |

6h SR=97.5%, 逐小时稳定 96.5-98.1%, 无回归。

### fallback 日志 (hm4104, 最近 5min)
**1× fallback 触发**:
```
PRIMARY-FAIL-STREAM nv_gw 流式 server_5xx status=502 after 180063ms → 切 ms_gw
FALLBACK-FAIL-STREAM ms_gw 流式 timeout status=0 after 250132ms (ms_gw 自身超时, 非 dsv4f0731 问题)
```
该 502 @180063ms ≈ 180s TIER budget 烧尽, 对应 all_tiers_exhausted 之一。1/130 (=0.8%) 单发偶发, 远低于干预阈值。

## 2. 根因判定 (改前必有数据)

延续 R1021-R1089 的 **NVCF deepseek-v4-flash-0731 特异性缓释期** (function_id 52e1ddb6):
1. **SR 98.5%, 6h 97.5% 且逐小时稳定** — 上游持续稳定, 无回归。
2. **错误仅 4 次/30min** (all_tiers_exhausted=3 + zombie_empty_completion=1), 均 ≈180s budget 边界烧尽。
3. **18 次失败 attempt 被 fast-break 消化** (RemoteDisconnected=13, Timeout=3, empty_200=2), 仅 4 请求烧尽 budget → fast-break 机制有效。
4. **429 = 0**, 无 429 冷却杠杆空间。
5. **无单 key 劣化** (tier_attempts per-key 全部 pexec_success 为主, 无故障集中)。
6. **hm4104 fallback=1 (0.8%)** — 单发 502 @budget 边界, 非模式性泄露。

## 3. 决策: NOP (无参数修改)

30min SR 98.5% > 95% NOP 阈值, 延迟稳定 (p50 9.4s), 无单 key 劣化, 趋势稳定无回归,
fallback 1× 为单发偶发 (0.8% < 干预阈值)。无单参数 lever 有数据支撑需调整。

维持 R1067 最佳配置 (UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET=180, NVU_TIER_BUDGET_DSV4F0731_NV=180,
KEY_COOLDOWN=30, TIER_COOLDOWN=90, 429 base/max=120, EMPTY_200 fast-break=3),
等待 NVCF deepseek-v4-flash-0731 function 完全恢复。

**不采取 integrate 旁路**: all_tiers_exhausted + RemoteDisconnected 均在 pexec 路径上瞬态,
integrate 0 请求, 无 integrate 对照数据 → 无数据支撑切换。

**不调整 TIER budget**: 单次 all_tiers_exhausted 为 180s budget 烧尽, 提高 budget 只会让 502
更晚出现而不增成功率; 98.5% SR 下无收益。

## 4. 验证

- [x] `/health` OK, 5 keys, proxy_role=passthrough, port=40666
- [x] 容器 dsvf0731_nv40666 Up 22 hours, 无重启, 无 env 改动
- [x] 30min SR=98.5%, 6h SR=97.5%, 延迟稳定 (p50 9.4s)
- [x] hm4104 fallback=1 (单发 502 @180s budget 边界, 0.8%, 非模式性)

## 5. 下一步建议

- 上游持续稳定, 保持 NOP 观察。若 6h SR 稳定 >95% 连续多轮, 可延长 NOP 轮间隔。
- 关注 NVCFPexecRemoteDisconnected (本窗 13 次): 为最大瞬态错误源, 但全被 fast-break 消化,
  无请求级影响。若单轮 RemoteDisconnected >30 或用尽 budget 请求 >10 (SR<92%), 需评估
  upstream/egress 稳定性。
- 若 dsv4f0731_nv 自身 all_tiers_exhausted 单轮 >10 次 (SR<92%) 回归, 或 hm4104 fallback 连续
  多轮 >2%, 再评估 integrate.api 旁路 (NV_KEY_INTEGRATE_KEYS) — 当前无需干预。