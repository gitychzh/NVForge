# R1246: HM2→HM1 — NOP (false trigger, R1000 HM1 self-commit, 81.1% SR all code-level failures, post-restart 13min too early)

## TL;DR
NOP — false trigger (HM1 commit R1000, "这是我提交的, 不触发"). 6h: 132req/107OK(81.1%SR)/25fail. 18 zombie_empty_completion (NVCF content-filter, code-level) + 5 IntegrateTimeout (NVCF function-level) + 6 all_tiers_exhausted (fallback_actually_attempted=false, code-level). Post-restart: 13min, 2-4req, too early. All params at floor/optimal. Zero param; iron rule: only change HM1 never HM2.

---

## 一、触发分析
cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit `28c0bfe` author = `opc2_uname` (HM2) → 实际上是 HM1 提交的 R1000 被 push 到 GitHub
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (false trigger, double-dispatch of R1000)
- HM1 本地未提交任何新内容

## 二、当前配置快照（R1246 部署前）

| # | 参数 | HM1 当前值 | 历史来源 |
|---|------|------------|----------|
| 1 | UPSTREAM_TIMEOUT | 66 | R988 |
| 2 | TIER_TIMEOUT_BUDGET_S | 210 | R1071→R1245 (210 generous) |
| 3 | NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | R997 (floor) |
| 4 | NVU_EMPTY_200_FASTBREAK | 2 | R1031 (code-level no-op R1039) |
| 5 | NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | R1010 (floor) |
| 6 | NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | R988 (sync UPSTREAM=66) |
| 7 | KEY_COOLDOWN_S | 25 | floor |
| 8 | TIER_COOLDOWN_S | 15 | R1103 (18→15) |
| 9 | NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| 10 | NVU_CONNECT_RESERVE_S | 0 | floor |
| 11 | NVU_SSLEOF_RETRY_DELAY_S | 1.0 | floor |
| 12 | NVU_MS_GW_FALLBACK_TIMEOUT | 200 | R1245 (180→200) |
| 13 | NVU_PEER_FALLBACK_TIMEOUT | 66 | R1000 (45→66) |
| 14 | NVU_TIER_BUDGET_GLM5_2_NV | 96 | R1008 |
| 15 | NVU_TIER_BUDGET_DSV4P_NV | 72 | R1116 |
| 16 | NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | R1035 |
| 17 | NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | R1008 |
| 18 | NVU_STREAM_TOTAL_DEADLINE_S | 42 | R1000 (90→42, aggressive) |
| 19 | NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | R1000 (new) |
| 20 | KEY_AUTHFAIL_COOLDOWN_S | 60 | R922 |
| 21 | NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | R982 |
| 22 | FALLBACK_HEALTH_THRESHOLD | 0.05 | dead param (R919) |
| 23 | NVU_FORCE_STREAM_UPGRADE | 0 | R692 |
| 24 | NVU_PEER_FB_SKIP_MODELS | (empty) | R1000 (removed glm5_2_nv) |
| 25 | NV_INTEGRATE_MODELS | glm5_2_nv | R833→R1245 |
| 26 | NV_KEY_INTEGRATE_KEYS | minimax_m3_nv:5 | R1245 (removed dsv4p_nv) |
| 27 | NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms | R1033 |
| 28 | MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| 29 | NVU_PEER_FALLBACK_ENABLED | 1 | R1000 |

## 三、数据收集

### 3.1 容器状态
- `nv_gw`: Up 13 minutes (healthy), StartedAt 2026-07-13T14:33:57Z (R1000+R1245 部署)
- `ms_gw`: Up 5 hours (healthy)
- compose md5: `6e23559de1376d2d638f98f34a544139`

### 3.2 6h 总体
| 指标 | 值 |
|------|-----|
| 总请求 | 132 |
| 成功 | 107 (81.1%) |
| 失败 | 25 |
| 平均延迟 | 31,036ms |
| 最大延迟 | 186,862ms |
| 平均 TTFB | 26,460ms |

### 3.3 1h 总体
| 指标 | 值 |
|------|-----|
| 总请求 | 8 |
| 成功 | 6 (75.0%) |
| 失败 | 2 |

### 3.4 Post-Restart (容器启动后 13min)
| 指标 | 值 |
|------|-----|
| 总请求 | 2 (DB) / 4 (logs) |
| 成功 | 1 (DB) / 3 (logs) |
| 失败 | 1 (zombie) |
| 判断 | 13min 太短，无法判断 |

### 3.5 按模型分组 (6h)
| 模型 | 请求 | 成功 | 失败 | SR | avg_dur | max_dur |
|------|------|------|------|-----|---------|---------|
| glm5_2_nv | 126 | 103 | 23 | 81.7% | 29,911ms | 186,862ms |
| dsv4p_nv | 6 | 4 | 2 | 66.7% | 54,654ms | 142,677ms |

### 3.6 按上游路径分组 (6h)
| 路径 | 请求 | 成功 | SR | avg_dur | max_dur |
|------|------|------|-----|---------|---------|
| nv_integrate | 114 | 96 | 84.2% | 24,906ms | 86,243ms |
| nvcf_pexec | 12 | 11 | 91.7% | 69,965ms | 147,581ms |
| NULL (ATE) | 6 | 0 | 0% | 69,650ms | 186,862ms |

### 3.7 错误分类 (6h)
| 错误类型 | 数量 | 可配置修复? |
|---------|------|-----------|
| zombie_empty_completion | 18 | ❌ NVCF content-filter, code-level |
| all_tiers_exhausted | 6 | ❌ fallback_actually_attempted=false, code-level |
| NVStream_IncompleteRead | 1 | ❌ code-level |

### 3.8 ATE 详情 (6h)
| 模型 | 错误类型 | 数量 | avg_dur | max_dur | fallback_attempted |
|------|---------|------|---------|---------|-------------------|
| glm5_2_nv | zombie_empty_completion | 18 | 22,298ms | 109,395ms | false |
| glm5_2_nv | all_tiers_exhausted | 4 | 50,802ms | 186,862ms | false |
| dsv4p_nv | all_tiers_exhausted | 2 | 107,346ms | 142,677ms | false |
| glm5_2_nv | NVStream_IncompleteRead | 1 | 50,718ms | 50,718ms | false |

**关键发现**: 全部 25 个失败 `fallback_actually_attempted=false` — fallback 从未被尝试。peer-fallback 已启用 (R1000) 但代码层面未触发 fallback 路径。

### 3.9 nv_tier_attempts (6h)
| tier | error_type | 数量 | avg_ms | 键分布 |
|------|-----------|------|--------|--------|
| glm5_2_nv | IntegrateTimeout | 5 | 90,892ms | k0=3, k2=1, k3=1 |

**分析**: 5 次 IntegrateTimeout 是关键错误。avg 90.9s，max 91.1s — NVCF 函数级超时，均匀分布在多个键上。FASTBREAK=1 正确工作（第 1 次超时后立即中止，不循环到所有键）。但 5 次 timeout 各消耗 90s → 在 tier 内耗尽给予 peer-fb 的时间。

### 3.10 成功率分时 (6h)
| 小时 (UTC) | 总数 | 成功 | 失败 | SR |
|------------|------|------|------|-----|
| 08:00 | 14 | 13 | 1 | 92.9% |
| 09:00 | 27 | 22 | 5 | 81.5% |
| 10:00 | 42 | 33 | 9 | 78.6% |
| 11:00 | 8 | 6 | 2 | 75.0% |
| 12:00 | 27 | 22 | 5 | 81.5% |
| 13:00 | 6 | 5 | 1 | 83.3% |
| 14:00 | 8 | 6 | 2 | 75.0% |

全时段 75-92.9% SR — 波动但无 catastrophic drop。

### 3.11 最近 10 条请求
| 时间 (UTC) | 模型 | 状态 | TTFB | 延迟 | 路径 | 输入字符 |
|-----------|------|------|------|------|------|---------|
| 14:34:12 | glm5_2_nv | 502 | 11,244ms | 11,244ms | integrate | 171,799 |
| 14:33:58 | glm5_2_nv | 200 | 13,469ms | 13,470ms | integrate | 170,894 |
| 14:33:38 | glm5_2_nv | 200 | 15,407ms | 15,408ms | integrate | 169,786 |
| 14:33:21 | glm5_2_nv | 200 | 16,080ms | 16,080ms | integrate | 168,906 |
| 14:14:32 | dsv4p_nv | 200 | 45,950ms | 45,950ms | pexec | 123 |
| 14:03:44 | glm5_2_nv | 502 | 7,209ms | 7,210ms | integrate | 171,095 |
| 14:03:36 | glm5_2_nv | 200 | 7,834ms | 7,835ms | integrate | 170,192 |
| 14:03:21 | glm5_2_nv | 200 | 13,902ms | 13,902ms | integrate | 168,906 |
| 13:33:49 | glm5_2_nv | 200 | 16,802ms | 19,268ms | integrate | 164,732 |
| 13:33:33 | glm5_2_nv | 200 | 16,440ms | 16,441ms | integrate | 163,019 |

### 3.12 ms_gw 信号
- ms_requests (6h): 12 total, **0 OK** — ms_gw BrokenPipeError 模式持续
- ms_gw 日志: MS-OK-STREAM / MS-STREAM-DONE 正常处理 (glm5.2 via ZHIPUAI)

### 3.13 nv_gw 日志 (最近 100 行)
- 4 个请求: 3× NV-INTEGRATE-SUCCESS + 1× NV-ZOMBIE-EMPTY
- tier_chain=['glm5_2_nv'] (no fallback, 3model) — 单 tier 链
- 全部 first-attempt integrate 成功
- 零 NV-TIER-FAIL, NV-EMPTY-FASTBREAK, NV-MS-FB, NV-ALL-TIERS
- 零 peer-fallback 触发

## 四、分析

### 4.1 误触发确认
- 最新 commit `28c0bfe` (R1000): HM2→HM1, author = `opc2_uname`
- 脚本输出 "这是我提交的, 不触发"
- HM1 未提交任何新内容
- cron 被派遣 — 应为误触发

### 4.2 失败根因分析

| 失败数 | 错误类型 | 根因 | 可配置修复? |
|--------|---------|------|-----------|
| 18 | zombie_empty_completion | NVCF glm5_2 content-filter: finish_reason=stop but content_chars=12 < 50, input_chars≥5000, no tool_calls. Gateway sends content_filter error SSE chunk → openclaw fallback. | ❌ code-level detection, correct behavior |
| 5 | IntegrateTimeout | NVCF function-level integrate timeout at ~90.9s. FASTBREAK=1 working (1st attempt aborts). Uniform across k0/k2/k3. NVCF internal queuing, not key-specific. | ❌ NVCF function-level, not config-fixable |
| 6 | all_tiers_exhausted (ATE) | 4 glm5_2_nv + 2 dsv4p_nv. fallback_actually_attempted=false for ALL — code-level block. Despite peer-fallback enabled (R1000), peer-fb never triggered. ms_gw 0/12 OK — BrokenPipeError. | ❌ code-level (fallback not attempted), not config-fixable |

### 4.3 参数优化空间
- **0 NVCFPexecTimeout** — FASTBREAK=1 at floor
- **0 empty_200, 0 SSLEOF, 0 429** — 零键级错误
- 所有 FASTBREAK at floor (1/2/1)
- 所有 cooldown at floor/optimal (KEY=25, TIER=15, INTEGRATE=0)
- BUDGET=210 >>> UPSTREAM=66 (144s margin) — 巨大余量
- **无参数可优化** — 所有错误为 code-level 或 NVCF function-level

### 4.4 R1000 变更效果
R1000 变更: peer-fb skip 移除, peer-fb timeout 45→66, NVU_STREAM_TOTAL_DEADLINE_S 90→42
- 容器重启后仅 13min / 2-4 请求
- 3/4 first-attempt integrate 成功 (8.7-16s)
- 1/4 zombie (content-filter, 11.2s)
- 零 peer-fb 触发 — 太早无法判断 R1000 效果
- 零 ATE post-restart — 早期信号积极但样本太小

### 4.5 与 R1245 对比
- R1245: dsv4p_nv 移出 NV_KEY_INTEGRATE_KEYS → 直接 pexec, 100% SR (3/3 OK, avg 22.4s)
- R1246: dsv4p_nv 6h 仅 6 请求 (4 OK, 2 ATE), low traffic
- glm5_2_nv: 81.7% SR, 主要失败模式 zombie (content-filter) — 自 R1133 持续

## 五、决策: NOP (零变更)

所有参数在 floor/optimal。6h 81.1% SR 中全部 25 个失败为 code-level（18 zombie + 5 timeout + 6 ATE/fallback-not-attempted + 1 NVStream_IncompleteRead）。Post-restart 仅 13min，数据不足。零参数可优化。零变更。

**铁律**: 只改 HM1 不改 HM2 ✓

---

## ⏳ 轮到HM1优化HM2
