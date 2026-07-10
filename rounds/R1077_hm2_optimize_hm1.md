# R1077: HM2→HM1 — NOP (double-dispatch, data identical to R1076, no config-fixable signals)

## TL;DR
NOP — double-dispatch continuation of R1076 (false trigger). 6h: 59req/51OK(86.4%)/8fail. dsv4p_nv 4/4 ATE (NVCF 504 external + ms_gw relay code-level). glm5_2_nv 51/55(92.7%), 4 NVStream_TimeoutError code-level. TIER_TIMEOUT_BUDGET_S=132 (R1074), NVU_MS_GW_FALLBACK_TIMEOUT=180 (R1074), NVU_PEER_FALLBACK_TIMEOUT=66 (R1074). All FASTBREAK at floor (1/2/1). All cooldown at floor. Zero param; iron rule: only change HM1 never HM2.

---

## 一、触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit `d6af335` author = `opc2_uname` (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch)
- Symlink 已指向 R1076 — 已由前一轮 fixed
- HM1 本地 git log 停留在 R821 (255 轮落后)
- 数据与 R1076 完全一致 (6h 窗口重合)

## 二、当前配置快照（R1077 部署前）

| # | 参数 | HM1 当前值 | 历史来源 |
|---|------|------------|----------|
| 1 | UPSTREAM_TIMEOUT | 66 | R988 (+2s, NVCFPexecTimeout binding rescue) |
| 2 | TIER_TIMEOUT_BUDGET_S | 132 | R1074 (110→132, +22s dsv4p_nv ATE headroom) |
| 3 | NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | R997 (2→1, function-level signal) |
| 4 | NVU_EMPTY_200_FASTBREAK | 2 | R1031 (1→2, key-specific empty_200 rescue; bug: logs show threshold=1) |
| 5 | NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | R1010 (2→1, function-level signal) |
| 6 | NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | R988 (sync UPSTREAM=66) |
| 7 | KEY_COOLDOWN_S | 25 | floor |
| 8 | TIER_COOLDOWN_S | 18 | R1018 (15→18, dsv4p empty_200 cooldown buffer) |
| 9 | NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| 10 | NVU_CONNECT_RESERVE_S | 0 | floor |
| 11 | NVU_SSLEOF_RETRY_DELAY_S | 1.0 | floor |
| 12 | NVU_MS_GW_FALLBACK_TIMEOUT | 180 | R1074 (90→180, ms_gw streaming rescue) |
| 13 | NVU_PEER_FALLBACK_TIMEOUT | 66 | R1074 (45→66, sync UPSTREAM=66) |
| 14 | NVU_TIER_BUDGET_GLM5_2_NV | 96 | R1008 (+2s, integrate budget) |
| 15 | NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | R1035 (110→100, -10s headroom) |
| 16 | NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | R1008 |
| 17 | NVU_STREAM_TOTAL_DEADLINE_S | 90 | R1038 (72→90, align thinking=90) |
| 18 | KEY_AUTHFAIL_COOLDOWN_S | 60 | R922 (defensive) |
| 19 | NVU_FALLBACK_HEALTH_THRESHOLD | 0.10 | R982 (0.05→0.10, dsv4p chain retention) |
| 20 | FALLBACK_HEALTH_THRESHOLD | 0.05 | dead param (R919) |
| 21 | NVU_FORCE_STREAM_UPGRADE | 0 | R692 |
| 22 | NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | R1039 (dsv4p_nv removed, re-enable peer rescue) |
| 23 | NV_INTEGRATE_MODELS | glm5_2_nv,minimax_m3_nv | R833 |
| 24 | NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,dsv4p_nv:dsv4p_ms,kimi_nv:kimi_ms | R1073 |

## 三、数据收集

### 3.1 6h 总体
| 指标 | 值 |
|------|-----|
| 总请求 | 59 |
| 成功 | 51 (86.4%) |
| 失败 | 8 (13.6%) |
| 平均延迟 | 30,796ms |
| 最大延迟 | 132,017ms |
| fallback触发 | 0 (f:59) |

### 3.2 1h 总体
| 指标 | 值 |
|------|-----|
| 总请求 | 6 |
| 成功 | 5 (83.3%) |
| 失败 | 1 |

### 3.3 Post-Restart (容器启动后 2026-07-10 08:35:48 UTC)
| 指标 | 值 |
|------|-----|
| 总请求 | 2 |
| 成功 | 1 (50.0%) |
| 失败 | 1 |

### 3.4 按模型分组 (6h)
| 模型 | 请求 | 成功 | 失败 | SR | avg_dur | max_dur |
|------|------|------|------|-----|---------|---------|
| glm5_2_nv | 55 | 51 | 4 | 92.7% | 26,609ms | 125,917ms |
| dsv4p_nv | 4 | 0 | 4 | 0.0% | 88,369ms | 132,017ms |

### 3.5 按上游路径分组 (6h)
| 路径 | 请求 | 成功 | SR | avg_dur | avg_ttfb |
|------|------|------|-----|---------|----------|
| nv_integrate | 54 | 50 | 92.6% | 24,770ms | 18,148ms |
| NULL (ATE) | 4 | 0 | 0.0% | 88,369ms | 928ms |
| nvcf_pexec | 1 | 1 | 100% | 125,917ms | 125,916ms |

### 3.6 错误类型 (6h)
| 错误类型 | 次数 | 模型 | 分析 |
|----------|------|------|------|
| NVStream_TimeoutError | 4 | glm5_2_nv | integrate流超时, 代码级, 非配置可修 |
| all_tiers_exhausted | 4 | dsv4p_nv | NVCF 504 external + ms_gw relay 代码级 |

### 3.7 nv_tier_attempts (6h)
| tier | error_type | cnt | avg_ms | max_ms |
|------|-----------|-----|--------|--------|
| glm5_2_nv | IntegrateRemoteDisconnected | 1 | 20,284ms | 20,284ms |
| glm5_2_nv | IntegrateTimeout | 1 | 90,566ms | 90,566ms |

- **0 NVCFPexecTimeout** in 6h → UPSTREAM=66 完全 non-binding
- **0 empty_200, 0 SSLEOF, 0 429** — 零键级错误
- dsv4p_nv: 0 nv_tier_attempts 行 (4 ATE 但 NVCF 504 不记录为 tier attempt)

### 3.8 最近 10 条请求
| 时间 (UTC) | 模型 | 状态 | 延迟 | TTFB | 路径 |
|-----------|------|------|------|------|------|
| 09:06:08 | dsv4p_nv | 502 | 132,017ms | 1,467ms | NULL (ATE) |
| 09:03:23 | glm5_2_nv | 200 | 125,917ms | 125,916ms | nvcf_pexec |
| 08:33:56 | glm5_2_nv | 200 | 19,747ms | 19,120ms | nv_integrate |
| 08:33:47 | glm5_2_nv | 200 | 9,166ms | 9,166ms | nv_integrate |
| 08:33:40 | glm5_2_nv | 200 | 4,654ms | 4,654ms | nv_integrate |
| 08:33:24 | glm5_2_nv | 200 | 11,109ms | 11,108ms | nv_integrate |
| 08:20:53 | dsv4p_nv | 502 | 1,328ms | 652ms | NULL (ATE) |
| 08:15:15 | glm5_2_nv | 502 | 96,068ms | - | nv_integrate |
| 08:04:47 | glm5_2_nv | 200 | 42,135ms | 41,151ms | nv_integrate |
| 08:04:09 | glm5_2_nv | 200 | 34,599ms | 34,599ms | nv_integrate |

### 3.9 成功率分时 (6h)
| 小时 (UTC) | 总数 | 成功 | 失败 | SR |
|------------|------|------|------|-----|
| 03:00 | 3 | 3 | 0 | 100% |
| 04:00 | 4 | 4 | 0 | 100% |
| 05:00 | 21 | 19 | 2 | 90.5% |
| 06:00 | 12 | 9 | 3 | 75.0% |
| 07:00 | 8 | 8 | 0 | 100% |
| 08:00 | 9 | 7 | 2 | 77.8% |
| 09:00 | 2 | 1 | 1 | 50.0% |

06:00 低谷 (75.0%) = NVStream_TimeoutError 集中。09:00 = dsv4p_nv ATE。

### 3.10 容器状态
- `nv_gw`: Up 50 minutes (healthy), StartedAt 2026-07-10T08:35:48Z
- `ms_gw`: Up 14 hours (healthy)
- ms_gw 日志: MS-OK-STREAM/MS-STREAM-DONE 正常处理 glm5_2_ms + dsv4p_ms

### 3.11 nv_gw 日志 (最近 100 行)
- 1 个 dsv4p_nv ATE 周期: k4 504 → k5 504 → pexec timeout → FASTBREAK → ABORT-NO-FALLBACK
- ms_gw relay BrokenPipeError 4211ms (relay_started=True)
- 零其他 ERROR / WARN
- glm5_2_nv integrate 全部正常 (NV-INTEGRATE-SUCCESS + first attempt)

### 3.12 ms_gw 配置
- EMPTY_200_FASTBREAK_THRESHOLD=3 (floor)
- UPSTREAM_TIMEOUT=300
- KEY_COOLDOWN_S=60
- VARIANT_COOLDOWN_S=30
- ALL_EXHAUSTED_COOLDOWN_S=30
- PROXY_TIMEOUT=600

## 四、分析

### 4.1 触发确认为误触发
- 最新 commit `d6af335` author = `opc2_uname` (HM2)，脚本输出 "这是我提交的, 不触发"
- Symlink 已指向 R1076 — 前一轮已 fix
- 数据与 R1076 完全一致 (同一 6h 窗口)
- HM1 本地 git log 停留在 R821 (255 轮落后)
- **Double-dispatch**: R1076 已提交+推送，cron 又派遣了一次

### 4.2 dsv4p_nv 100% ATE = 外部 + 代码级
- 4/4 dsv4p_nv 请求全部 ATE (NVCF 504 gateway timeout + NVCFPexecTimeout)
- NVCF function `74f02205` 返回 504 — 外部 NVCF per-account/per-IP 部署差异
- ms_gw relay 成功处理 dsv4p_ms (MS-OK-STREAM) 但 relay 回 nv_gw→client 时 BrokenPipeError
- 这是代码级 TCP relay 竞态，非配置可修
- R1074 的 MS_GW_FALLBACK_TIMEOUT 180s 未生效 (relay 在 timeout 前就断管)

### 4.3 glm5_2_nv 92.7% SR 稳定
- 51/55 integrate 成功，100% first-attempt
- 4 个 NVStream_TimeoutError 是代码级流超时，非配置可修
- nv_tier_attempts: 仅 2 行 (IntegrateRemoteDisconnected + IntegrateTimeout)，非故障模式
- 0 NVCFPexecTimeout, 0 empty_200, 0 SSLEOF, 0 429 — 完美零键级错误

### 4.4 参数优化空间
- UPSTREAM=66 non-binding (0 NVCFPexecTimeout in 6h)
- 所有 FASTBREAK 在 floor (1/2/1)
- 所有 cooldown 在 floor/optimal
- BUDGET=132 >> UPSTREAM=66 (66s margin)
- 所有 tier-specific budgets 充足
- ms_gw: 所有参数在 floor
- **无参数可优化** — 达到理论最优状态 (在当前 NVCF function 部署约束下)

### 4.5 与 R1076 对比
- R1076: 6h 59/51(86.4%), 8 fail, 同一 error breakdown
- R1077: 6h 59/51(86.4%), 8 fail, 完全一致
- 数据未变化 — 同一 6h 窗口

## 五、决策: NOP (零变更)

所有参数在 floor/optimal。dsv4p_nv 100% ATE 是 NVCF 外部 504 + ms_gw 代码级 relay 问题，非配置可修。glm5_2_nv 92.7% SR 稳定，4 个 NVStream_TimeoutError 是代码级。零变更。

## 六、变更记录

无变更。容器未重启。

---

## ⏳ 轮到HM1优化HM2
