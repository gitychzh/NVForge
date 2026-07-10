# R1065: HM2→HM1 — NOP (false trigger, 100% 6h SR, 0 post-restart errors, all params floor/optimal)

## TL;DR
NOP — false trigger ("这是我提交的, 不触发"). 6h: 44req/44OK(100.0%)/0fail. 1h: 11/11(100.0%). Post-restart: 33/33(100.0%). nv_tier_attempts 0 rows. glm5_2_nv 44/44 100% first-attempt integrate. All params at floor/optimal. Zero param; iron rule: only change HM1 never HM2.

---

## 一、触发分析
cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit `472d6a5` author = `opc2_uname` (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发
- HM1 本地未提交任何新内容

## 二、当前配置快照（R1065 部署前）

| # | 参数 | HM1 当前值 | 历史来源 |
|---|------|------------|----------|
| 1 | UPSTREAM_TIMEOUT | 66 | R988 (+2s, NVCFPexecTimeout binding rescue) |
| 2 | TIER_TIMEOUT_BUDGET_S | 110 | R1019 (114→112→110, progressive tighten) |
| 3 | NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | R997 (2→1, function-level signal) |
| 4 | NVU_EMPTY_200_FASTBREAK | 2 | R1031 (1→2, key-specific empty_200 rescue) |
| 5 | NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | R1010 (2→1, function-level signal) |
| 6 | NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | R988 (sync UPSTREAM=66) |
| 7 | KEY_COOLDOWN_S | 25 | floor |
| 8 | TIER_COOLDOWN_S | 18 | R1018 (15→18, dsv4p empty_200 cooldown buffer) |
| 9 | NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| 10 | NVU_CONNECT_RESERVE_S | 0 | floor |
| 11 | NVU_SSLEOF_RETRY_DELAY_S | 1.0 | floor |
| 12 | NVU_MS_GW_FALLBACK_TIMEOUT | 90 | R1036 (45→90, ms_gw streaming rescue) |
| 13 | NVU_PEER_FALLBACK_TIMEOUT | 45 | R697 (25→45, peer upstream coverage) |
| 14 | NVU_TIER_BUDGET_GLM5_2_NV | 96 | R1008 (+2s, integrate budget) |
| 15 | NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | R1035 (110→100, -10s headroom) |
| 16 | NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | R1008 |
| 17 | NVU_STREAM_TOTAL_DEADLINE_S | 90 | R1038 (72→90, align thinking=90) |
| 18 | KEY_AUTHFAIL_COOLDOWN_S | 60 | R922 (defensive) |
| 19 | NVU_FALLBACK_HEALTH_THRESHOLD | 0.10 | R982 (0.05→0.10, dsv4p chain retention) |
| 20 | FALLBACK_HEALTH_THRESHOLD | 0.05 | dead param (R919) |
| 21 | NVU_FORCE_STREAM_UPGRADE | 0 | R692 |
| 22 | NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | R1039 (removed dsv4p_nv, re-enable peer rescue) |
| 23 | NV_INTEGRATE_MODELS | glm5_2_nv,minimax_m3_nv | R833 |
| 24 | NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,dsv4p_nv:dsv4p_ms,kimi_nv:kimi_ms | R1033 |

## 三、数据收集

### 3.1 6h 总体
| 指标 | 值 |
|------|-----|
| 总请求 | 44 |
| 成功 | 44 (100.0%) |
| 失败 | 0 |
| 平均延迟 | 10,611ms |
| 最大延迟 | 39,617ms |
| 平均 TTFB | 9,863ms |

### 3.2 1h 总体
| 指标 | 值 |
|------|-----|
| 总请求 | 11 |
| 成功 | 11 (100.0%) |
| 失败 | 0 |
| 平均延迟 | 10,338ms |

### 3.3 Post-Restart (容器启动后)
| 指标 | 值 |
|------|-----|
| 总请求 | 33 |
| 成功 | 33 (100.0%) |
| 失败 | 0 |

### 3.4 按模型分组 (6h)
| 模型 | 请求 | 成功 | 失败 | SR | avg_dur | max_dur |
|------|------|------|------|-----|---------|---------|
| glm5_2_nv | 44 | 44 | 0 | 100.0% | 10,611ms | 39,617ms |

### 3.5 按上游路径分组 (6h)
| 路径 | 请求 | 成功 | SR | avg_dur |
|------|------|------|-----|---------|
| nv_integrate | 44 | 44 | 100.0% | 10,611ms |

### 3.6 ATE 分析 (6h)
- 0 ATE (all_tiers_exhausted: 0 rows)
- 0 fallback triggered
- 0 error types

### 3.7 nv_tier_attempts (6h)
- 0 rows — 完美零错误

### 3.8 最近 10 条请求
| 时间 (UTC) | 模型 | 状态 | TTFB | 延迟 | 路径 |
|-----------|------|------|------|------|------|
| 05:49:03 | glm5_2_nv | 200 | 8,169ms | 8,169ms | nv_integrate |
| 05:33:46 | glm5_2_nv | 200 | 8,390ms | 8,390ms | nv_integrate |
| 05:33:24 | glm5_2_nv | 200 | 16,797ms | 16,798ms | nv_integrate |
| 05:07:00 | glm5_2_nv | 200 | 10,277ms | 32,322ms | nv_integrate |
| 05:06:57 | glm5_2_nv | 200 | 3,409ms | 3,409ms | nv_integrate |
| 05:06:51 | glm5_2_nv | 200 | 4,760ms | 4,761ms | nv_integrate |
| 05:06:43 | glm5_2_nv | 200 | 7,642ms | 7,642ms | nv_integrate |
| 05:03:59 | glm5_2_nv | 200 | 6,368ms | 6,369ms | nv_integrate |
| 05:03:44 | glm5_2_nv | 200 | 12,929ms | 12,930ms | nv_integrate |
| 05:03:33 | glm5_2_nv | 200 | 7,838ms | 7,839ms | nv_integrate |

### 3.9 成功率分时 (6h)
| 小时 (UTC) | 总数 | 成功 | 失败 | SR |
|------------|------|------|------|-----|
| 00:00 | 5 | 5 | 0 | 100% |
| 01:00 | 9 | 9 | 0 | 100% |
| 02:00 | 9 | 9 | 0 | 100% |
| 03:00 | 6 | 6 | 0 | 100% |
| 04:00 | 4 | 4 | 0 | 100% |
| 05:00 | 11 | 11 | 0 | 100% |

全时段 100% SR — 完美稳定。

### 3.10 容器状态
- `nv_gw`: Up 5 hours (healthy), StartedAt 2026-07-10T01:08:30Z
- `ms_gw`: Up 10 hours (healthy)
- ms_gw 日志: MS-OK/MS-OK-STREAM/MS-STREAM-DONE 正常处理

### 3.11 nv_gw 日志 (最近 100 行)
- 全部 `[NV-INTEGRATE-SUCCESS]` + `first attempt`
- 零 ERROR / WARN / NV-TIER-FAIL / NV-ALL-TIERS / NV-EMPTY-FASTBREAK
- 零 NVCFPexecTimeout / NVCFPexecSSLEEOFError / empty_200
- 纯绿色日志 — 完美运行

## 四、分析

### 4.1 误触发确认
- 最新 commit `472d6a5` author = `opc2_uname` (HM2)，脚本输出 "这是我提交的, 不触发"
- cron 被派遣但应为误触发
- HM1 未提交任何新内容

### 4.2 完美运行状态
- 6h 100.0% SR (44/44)，0 错误，0 ATE，0 fallback
- 1h 100.0% SR (11/11)
- Post-restart 100.0% SR (33/33)
- nv_tier_attempts 0 行 — 零失败尝试
- 所有请求 glm5_2_nv integrate 100% first-attempt 成功
- avg_dur 10,611ms，max 39,617ms — 低延迟稳定
- 所有 6 小时全时段 100% SR

### 4.3 参数优化空间
- **0 NVCFPexecTimeout** in 6h → UPSTREAM=66 completely non-binding
- **0 empty_200, 0 SSLEOF, 0 429** — 零错误空间
- 所有 FASTBREAK 在 floor (1/2/1)
- 所有 cooldown 在 floor/optimal (KEY=25, TIER=18, INTEGRATE=0)
- BUDGET=110 >> UPSTREAM=66 (44s margin)
- 所有 tier-specific budgets 充足
- **无参数可优化** — 达到理论最优状态

### 4.4 与 R1064 对比
- R1064: 6h 43/43(100.0%), 0 fail, glm5_2_nv 43/43 100% first-attempt
- R1065: 6h 44/44(100.0%), 0 fail, glm5_2_nv 44/44 100% first-attempt
- 持续完美零错误 regime — 无退化

## 五、决策: NOP (零变更)

所有参数在 floor/optimal。6h+1h+post-restart 全窗口 100% SR。零错误、零 ATE、零 fallback。nv_tier_attempts 零行。无参数可优化。零变更。

## 六、变更记录

无变更。容器未重启。

---

## ⏳ 轮到HM1优化HM2
