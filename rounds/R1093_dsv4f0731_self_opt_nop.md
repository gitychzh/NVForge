# R1093: dsv4f0731_nv self-opt — NOP (SR 97.6%, FID 281478d0 100% pexec success, 无待调参数)

日期: 2026-08-07 ~17:00 UTC (~01:00 BJT 08-08)

## 1. 数据 (30min 窗口 ~16:30-17:00 UTC)

### 主指标 (nv_requests)
- **SR = 97.6% (124/127)**, avg=17253ms, p50=9847ms, **p95=73538ms**
- 30min 错误: **NVStream_IncompleteRead=1** (avg 35453), **all_tiers_exhausted=1** (avg 180074), **stream_absolute_cap=1** (avg 150012), **zombie_empty_completion=1** (avg 7050)
- **429 计数 = 0**
- upstream_type: 100% nvcf_pexec (123/123), integrate 0 请求
- finish_reason: tool_calls=102, stop=17

### per-key 200 延迟 (5 key 全部 100% 成功)
| key | 200 | avg_ok_ms | max_ms |
|---|---|---|---|
| k0 | 27 | 22135 | 121063 |
| k1 | 20 | 9959 | 13154 |
| k2 | 26 | 12425 | 33816 |
| k3 | 22 | 11990 | 17464 |
| k4 | 24 | 15243 | 67687 |

k0/k4 avg/ms max 偏高但 100% 200 成功 → tool_calls 长流正常。

### per-key 错误 (30min)
| key | error_type | count | avg_ms |
|---|---|---|---|
| k0 | NVStream_IncompleteRead | 1 | 35453 |
| k0 | all_tiers_exhausted | 1 | 180074 |
| k0 | zombie_empty_completion | 1 | 7050 |
| k2 | stream_absolute_cap | 1 | 150012 |

k0 集中 3 错误但 27×200 成功 → 轮转偶发, 非 k0 单点持续劣化。

### FID 路由分析 (关键发现, 首次 30min 粒度)
| function_id | upstream_type | total | ok | avg_ok_ms |
|---|---|---|---|---|
| 281478d0 (0731 新 FID) | nvcf_pexec | 106 | 106 | 4353 |
| 52e1ddb6 (旧 dsv4f FID) | nvcf_pexec | 13 | 0 | — |

**核心洞察**: 281478d0 106/106 = **100% pexec 成功率**, avg 4.4s。但 ~12.3% (13/119) 的 attempt 错误路由到 52e1ddb6, 全部失败 (13 RemoteDisconnected + 1 timeout + 1 empty_200, avg ~35s/次)。**若解决路由泄漏, Request 级 SR 可达 100%。**

### key_cycle_429s 分布
0=11, 1=109, 2=1, 3=2

k1=109 为轮转伪影 (连续 12 轮确认): k1 0 错误 + 20×200 成功。

### 趋势 (持续稳定 6h)
| 时段 | total | ok | err | SR | avg_ok_ms |
|---|---|---|---|---|---|
| 04:00 UTC | 284 | 278 | 6 | 97.9% | 12495 |
| 05:00 UTC | 249 | 243 | 6 | 97.6% | 12557 |
| 06:00 UTC | 272 | 264 | 8 | 97.1% | 14308 |
| 07:00 UTC | 262 | 253 | 9 | 96.6% | 12557 |
| 08:00 UTC | 261 | 252 | 9 | 96.6% | 12753 |
| 09:00 UTC | 51 | 51 | 0 | 100.0% | 8454 |
| 30min | 127 | 124 | 3 | **97.6%** | — |
| **6h** | **1625** | **1580** | **45** | **97.2%** | — |
| **24h** | — | — | — | **~97%** | — |

**SR 随 42h 持续稳定, 无退化趋势**: 凌晨 09:00 UTC (17:00 BJT) 窗口 51/51=100%。

### 24h all_tiers_exhausted = 328 (较 R1092 的 334 略降)

### NVCFPexecRemoteDisconnected 24h 趋势
| 时段 | disc_pct | 备注 |
|---|---|---|
| 09-14 UTC (昨日峰值) | 34.7-59.4% | **旧 FID (52e1ddb6) 时代** |
| 01-08 UTC (今日) | 9.6-13.1% | 换 FID 后改善 75% |
| 09 UTC (最新) | 0.0% | 完美 |

### fallback 日志 (hm4104, 最近 5min)
3 次 PRIMARY-BREAKER-SKIP + 1 次 PRIMARY-FAIL-STREAM (502@180082ms) + 1 FALLBACK-STREAM:
```
16:55:23 PRIMARY-FAIL-STREAM nv_gw 502 after 180082ms
16:55:41 FALLBACK-STREAM 提醒插入首 delta 前
16:56:08 PRIMARY-BREAKER-SKIP (circuit OPEN), 直走 fallback
16:56:11 FALLBACK-STREAM
```
单次 502 触发下游熔断, 短暂自愈。

## 2. 根因分析

1. **SR 97.6%, 6h 97.2%, 最新小时 100%** — 稳定无退化。
2. **新 FID 281478d0 完美**: 106/106=100% pexec success, avg 4.4s vs 52e1ddb6 旧 FID 0%.
3. **~12% 路由泄漏到 52e1ddb6 浪费 budget**: 13 次/30min, 每次 ~35s = ~455s 浪费。但 request 级仍通过剩余的 pexec 成功 =97.6% SR。
4. **429 = 0**, fast-break 耗尽 key 先于 429。
5. **错误 4 次/30min (全部 pexec)**: 不在 integrate 路径 (integrate 0 请求)。
6. **hm4104 fallback 由单次 502 触发下游熔断**, 非本容器异常。

## 3. 决策: NOP (无参数修改)

30min SR 97.6% > 95% NOP 阈值, 6h 97.2%, 趋势稳定, 无待调参数。

**不尝试解决 52e1ddb6 路由泄漏**: 这是 upstream.py 的 `_try_tier_keys` 中 func_health 选择 function_id 的代码逻辑问题 (select_healthy_function 只接收 ["281478d0"], 但实际 observation 出现 52e1ddb6 — 可能是线程安全/内存泄漏/func_health 全局跨 model 泄漏, 或者 `execute_request` 中 R-channel 分支并行运行 dsv4f_nv 的 channel 逻辑共享了 function_id 变量)。这**不是参数可以解决的问题**, 需要代码修改。在当前 SR 97.6% 下收益不迫切。

维持 R1067 最佳配置不变:
- UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET=180, NVU_TIER_BUDGET_DSV4F0731_NV=180
- KEY_COOLDOWN=30, TIER_COOLDOWN=90
- NVU_KEYMGR_429_BASE_COOLDOWN=120, NVU_KEYMGR_429_MAX_COOLDOWN=300
- NVU_EMPTY_200_FASTBREAK=3, NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_CONN_ERR_FAST_BREAK=2
- NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90

## 4. 验证
- [x] `/health` OK, 5 keys, proxy_role=passthrough, port=40666
- [x] 容器 dsvf0731_nv40666 Up 23h, 无重启, 无 env 改动
- [x] 30min SR=97.6%, 6h SR=97.2%, 延迟稳定 (p50 9.8s)
- [x] hm4104 fallback 仅单次 502 触发下游熔断

## 5. 下一步建议
- 持续 NOP 观察。SR 连续 >95% 4+ 轮可考虑延长轮次间隔至 1h。
- **代码级问题**: ~12% attempt 路由到错误 FID 52e1ddb6。排查 `func_health.select_healthy_function` 是否跨 model 泄漏候选列表, 或 `_try_tier_keys` 中 function_id 变量在多线程下被其他 tier 的 channel 逻辑覆盖。修复后预期 SR 可提升至 ~100%。
- 若 bark/用户反馈 dsv4f0731_nv 有退化, 优先查 FID 路由统计而非调超时参数。