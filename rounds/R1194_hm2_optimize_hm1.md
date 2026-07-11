# R1194: HM2→HM1 — NOP (false trigger, 62nd chain of R1133, zombie-only, all params floor/optimal, NVCF content-filter not config-fixable)

## TL;DR
NOP — 62nd false-trigger continuation of R1133. 6h: 24req/12OK(50.0%)/12zombie. glm5_2_nv integrate, NVCF content-filter stop+12chars, input_chars 171K→174K growing. Gateway detection+error-chunk correct. dsv4p_nv 0 traffic 21h. ms_gw 0 traffic. 0 tier_attempts. Zero param. 铁律:只改HM1不改HM2

## 一、触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit `2e021f9` author = `opc2_uname` (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (62nd chain of R1133)
- Symlink 已指向 R1193 — 前一轮已 fixed
- HM1 本地 git log 停留在 R821 (373 轮落后)

## 二、当前配置快照（R1194 部署前）

| # | 参数 | HM1 当前值 | 历史来源 |
|---|------|------------|----------|
| 1 | UPSTREAM_TIMEOUT | 66 | R988 (+2s, NVCFPexecTimeout binding rescue) |
| 2 | TIER_TIMEOUT_BUDGET_S | 198 | R1118 (132→198, +66s ms_gw+peer fallback rescue window) |
| 3 | NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | R997 (2→1, function-level signal) |
| 4 | NVU_EMPTY_200_FASTBREAK | 2 | R1031 (1→2, key-specific empty_200 rescue; bug: logs show threshold=1) |
| 5 | NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | R1010 (2→1, function-level signal) |
| 6 | NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | R988 (sync UPSTREAM=66) |
| 7 | KEY_COOLDOWN_S | 25 | floor |
| 8 | TIER_COOLDOWN_S | 15 | R1103 (18→15, revert R1018, key-specific empty_200 proved excessive) |
| 9 | NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| 10 | NVU_CONNECT_RESERVE_S | 0 | floor |
| 11 | NVU_SSLEOF_RETRY_DELAY_S | 1.0 | floor |
| 12 | NVU_MS_GW_FALLBACK_TIMEOUT | 180 | R1074 (90→180, ms_gw streaming rescue) |
| 13 | NVU_PEER_FALLBACK_TIMEOUT | 66 | R1074 (45→66, sync UPSTREAM=66) |
| 14 | NVU_TIER_BUDGET_GLM5_2_NV | 96 | R1008 (+2s, integrate budget) |
| 15 | NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | R1035 (110→100, -10s headroom) |
| 16 | NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | R1008 |
| 17 | NVU_STREAM_TOTAL_DEADLINE_S | 42 | R1107 (90→42, minimize zombie stall window) |
| 18 | KEY_AUTHFAIL_COOLDOWN_S | 60 | R922 (defensive) |
| 19 | NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | R919 (dead param) |
| 20 | FALLBACK_HEALTH_THRESHOLD | 0.05 | dead param (R919) |
| 21 | NVU_FORCE_STREAM_UPGRADE | 0 | R692 |
| 22 | NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | R1039 (dsv4p_nv removed, re-enable peer rescue) |
| 23 | NV_INTEGRATE_MODELS | glm5_2_nv | R833 |
| 24 | NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,dsv4p_nv:dsv4p_ms,kimi_nv:kimi_ms | R1073 |
| 25 | NVU_TIER_BUDGET_DSV4P_NV | 72 | R1116 (66→72, +6s for k5 rescue) |

## 三、数据收集

### 3.1 6h 总体 (DB)
| 指标 | 值 |
|------|-----|
| 总请求 | 24 |
| 成功 | 12 (50.0%) |
| 失败 | 12 (50.0%) |
| 平均延迟 | 7,177ms |
| 最大延迟 | 38,540ms |
| fallback触发 | 0 (f:24) |

### 3.2 按模型分组 (6h)
| 模型 | 请求 | 成功 | 失败 | SR | avg_dur | max_dur |
|------|------|------|------|-----|---------|---------|
| glm5_2_nv | 24 | 12 | 12 | 50.0% | 7,177ms | 38,540ms |
| dsv4p_nv | 0 | 0 | 0 | N/A | — | — |

### 3.3 按上游路径分组 (6h)
| 路径 | 请求 | 成功 | SR | avg_dur | avg_ttfb |
|------|------|------|-----|---------|----------|
| nv_integrate | 24 | 12 | 50.0% | 7,177ms | 7,176ms |

### 3.4 错误类型 (6h)
| 错误类型 | 次数 | 分析 |
|----------|------|------|
| zombie_empty_completion | 12 | NVCF content-filter stop+12chars, input_chars 171K→174K growing, code-level |

### 3.5 nv_tier_attempts (6h)
- **0 rows** — 零 tier-level 错误

### 3.6 最近 10 条请求
| 时间 (UTC) | 模型 | 状态 | 延迟 | 路径 |
|-----------|------|------|------|------|
| 08:33:39 | glm5_2_nv | 502 | 10,434ms | nv_integrate |
| 08:33:24 | glm5_2_nv | 200 | 9,256ms | nv_integrate |
| 08:03:40 | glm5_2_nv | 502 | 4,432ms | nv_integrate |
| 08:03:24 | glm5_2_nv | 200 | 10,323ms | nv_integrate |
| 07:34:09 | glm5_2_nv | 502 | 4,576ms | nv_integrate |
| 07:33:24 | glm5_2_nv | 200 | 38,540ms | nv_integrate |
| 07:03:35 | glm5_2_nv | 502 | 5,642ms | nv_integrate |
| 07:03:24 | glm5_2_nv | 200 | 4,604ms | nv_integrate |
| 06:33:38 | glm5_2_nv | 502 | 6,659ms | nv_integrate |
| 06:33:24 | glm5_2_nv | 200 | 7,961ms | nv_integrate |

### 3.7 容器状态
- `nv_gw`: Up 14 hours (healthy), StartedAt 2026-07-11 03:03:24 CST
- `ms_gw`: Up 37 hours (healthy), StartedAt 2026-07-09 00:01:24 CST

### 3.8 nv_gw 日志 (最近 100 行)
- 纯 zombie 模式: 每 30min 一轮 integrate 请求对 (2 req/rnd)
- 第一 req: NV-INTEGRATE-SUCCESS, first attempt, ~2-3s TTFB
- 第二 req: NV-INTEGRATE-SUCCESS, first attempt, ~2-3s TTFB, 然后 NV-ZOMBIE-EMPTY (content_chars=12 < 50, input_chars 171K→174K growing)
- NV-ZOMBIE-ERROR-CHUNK: finish_reason=content_filter SSE chunk → trigger openclaw fallback
- Gateway detection+error-chunk 正确工作
- 零 ERROR, 零 WARN, 零 ATE, 零 FASTBREAK, 零 NV-TIER-FAIL
- dsv4p_nv: 0 traffic 21h+ (since restart 2026-07-10 19:03Z)

### 3.9 ms_gw 日志 (最近 30 行)
- 正常处理 glm5_2_ms + dsv4p_ms 请求
- MS-OK-STREAM → MS-STREAM-DONE 标准流程
- 1× MS-STREAM-CLIENT-EOF (BrokenPipeError, 客户端断开)
- 1× stream_no_data_lines → FASTBREAK=3 → variant exhausted → 下一 variant OK
- 0 ERROR, 0 异常

## 四、分析

### 4.1 触发确认为误触发
- 最新 commit `2e021f9` author = `opc2_uname` (HM2)，脚本输出 "这是我提交的, 不触发"
- Symlink 已指向 R1193 — 前一轮已 fix
- 数据与 R1193 完全一致: 同一 6h 窗口，24req/12OK(50.0%)/12zombie
- HM1 本地 git log 停留在 R821 (373 轮落后)
- **62nd chain of R1133**: R1133 触发于 2026-07-10 22:03 UTC，至今无 HM1 实际变更

### 4.2 zombie_empty_completion 持续
- 12/12 失败为 zombie_empty_completion (NVCF content-filter stop+12chars)
- input_chars 增长趋势: 171K→174K (每轮 +~500 chars)
- Gateway 检测正确: NV-ZOMBIE-EMPTY → NV-ZOMBIE-ERROR-CHUNK → openclaw fallback
- 这是 NVCF 内容过滤行为，非配置可修

### 4.3 dsv4p_nv 零流量
- dsv4p_nv: 0 traffic 21h (since HM1 last restart at 2026-07-10 19:03Z)
- 但 dsv4p_nv pexec 历史上 100% SR (since restart)
- ms_gw dsv4p_ms 正常处理请求 (MS-OK-STREAM)

### 4.4 参数优化空间
- UPSTREAM=66 non-binding (0 NVCFPexecTimeout in 6h)
- 所有 FASTBREAK 在 floor/optimal (1/2/1)
- 所有 cooldown 在 floor/optimal
- BUDGET=198 >> UPSTREAM=66 (132s margin)
- 所有 tier-specific budgets 充足
- ms_gw: 所有参数在 floor
- **无参数可优化** — 达到理论最优状态

### 4.5 与 R1193 对比
- R1193: 6h 24/12(50.0%), 12 zombie, 0 tier_attempts
- R1194: 6h 24/12(50.0%), 12 zombie, 0 tier_attempts
- 数据完全一致 — 同一 6h 窗口

## 五、决策: NOP (零变更)

所有参数在 floor/optimal。12/12 失败为 zombie_empty_completion（NVCF content-filter 行为，代码级检测+error-chunk 正确）。dsv4p_nv 0 traffic 21h。ms_gw 正常。零变更。

## 六、变更记录

无变更。容器未重启。

---

## ⏳ 轮到HM1优化HM2
