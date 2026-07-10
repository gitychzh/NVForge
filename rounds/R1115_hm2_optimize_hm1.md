# HM2 Optimize HM1 — Round R1115

**日期**: 2026-07-11 02:40 UTC
**触发**: false trigger (double-dispatch of R1114, 自提交 "这是我提交的, 不触发")
**作者**: opc2_uname (HM2)
**结论**: NOP — 所有参数在最优值, 所有失败为代码级

## 1. 触发分析

- cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit: `ebe861a` (R1114, opc2_uname), 自提交
- 本轮 = R1114 的 double-dispatch
- 本次为 R1115

## 2. HM1 nv_gw 容器状态

- 容器: nv_gw, Up ~1h, StartedAt 2026-07-10T17:21:04Z
- tier_chain: `['glm5_2_nv', 'dsv4p_nv', 'kimi_nv', 'minimax_m3_nv']` (no fallback, 3model)
- 所有参数在 floor/optimal

## 3. 6h 数据 (DB 查询)

| 指标 | 值 |
|------|-----|
| 总请求 | 136 |
| 成功 | 122 |
| 失败 | 14 |
| SR | 89.7% |

### 按模型

| 模型 | 请求 | 成功 | 失败 | SR | avg_dur |
|------|------|------|------|-----|---------|
| glm5_2_nv | 95 | 84 | 11 | 88.4% | 19,253ms |
| dsv4p_nv | 25 | 22 | 3 | 88.0% | 20,881ms |
| minimax_m3_nv | 9 | 9 | 0 | 100% | 14,483ms |
| kimi_nv | 7 | 7 | 0 | 100% | 3,605ms |

### 错误分类

| 错误类型 | 数量 | 分析 |
|----------|------|------|
| zombie_empty_completion | 9 | 代码级僵尸检测, 3-15s fast abort (优于96s hang) |
| all_tiers_exhausted | 3 | ms_gw BrokenPipeError, 代码级流同步缺陷 |
| NVStream_TimeoutError | 2 | 代码级流超时 |

### 按路径

| 路径 | 请求 | 成功 | 失败 | SR |
|------|------|------|------|-----|
| nv_integrate | 102 | 91 | 11 | 89.2% |
| nvcf_pexec | 31 | 31 | 0 | 100% |
| (ATE) | 3 | 0 | 3 | 0% |

### 其他

- nv_tier_attempts: 0 行 (无 key 级失败)
- fallback_occurred: 0/136 (全部 false)
- ms_gw: 0% SR (6 total, 0 OK), 全部 BrokenPipeError
- 容器日志中观察到 1 次 dsv4p_nv ATE: k4 empty_200 → TIER_BUDGET=66 耗尽 → ms_gw BrokenPipeError 4376ms

## 4. 当前参数 (HM1 nv_gw)

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | floor |
| TIER_TIMEOUT_BUDGET_S | 198 | optimal |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | optimal |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal |
| TIER_COOLDOWN_S | 15 | floor |
| KEY_COOLDOWN_S | 25 | floor |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | standard |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | optimal |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | optimal |
| NVU_EMPTY_200_FASTBREAK | 2 | set (known bug: not honored in pexec) |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | floor |
| NVU_FORCE_STREAM_UPGRADE | 0 | disabled |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | aligned |
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 | generous |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | standard |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | floor |

## 5. ms_gw 状态

- 容器 ms_gw 正常, 处理 dsv4p_ms 和 glm5_2_ms 请求
- EMPTY_200_FASTBREAK_THRESHOLD=3, KEY_COOLDOWN_S=60, UPSTREAM_TIMEOUT=300
- 全部失败为代码级 BrokenPipeError (nv_gw 在 ms_gw 完成 relay 前断开)
- 观测: 1 次 dsv4p_ms 的 MS-STREAM-DONE 后 BrokenPipeError (nv_gw 提前断开)

## 6. 决策: NOP

**所有 14 个失败全部为代码级, 无可配置参数优化空间:**

| 失败类型 | 数量 | 代码级原因 | 配置可变? |
|---------|------|-----------|----------|
| zombie_empty_completion | 9 | 代码级僵尸检测, 3-15s fast abort | 否 |
| all_tiers_exhausted | 3 | ms_gw BrokenPipeError 流同步缺陷 | 否 |
| NVStream_TimeoutError | 2 | 代码级流超时 | 否 |

**所有参数在 floor/optimal 值, 无调整空间:**
- nvcf_pexec: 100% SR (31/31) — 完美
- nv_tier_attempts: 0 行 — 无 key 级失败
- UPSTREAM=66, TIER_COOLDOWN=15, KEY_COOLDOWN=25 均为 floor
- FASTBREAK 参数全部最优
- TIER_BUDGET 198 充裕, 各模型 per-tier budget 合理

**铁律: 只改 HM1 不改 HM2。本轮不改任何参数。**

## 7. 验证

- ✅ 容器正常运行 (Up ~1h)
- ✅ 所有参数在预期值
- ✅ 无配置漂移
- ✅ 0 容错空间 (全部失败为代码级)

## ⏳ 轮到HM1优化HM2
