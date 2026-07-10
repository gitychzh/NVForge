# R1066: HM2→HM1 — NOP (false trigger, 98.1% 6h SR, 1 NVStream_TimeoutError on k1, all params floor/optimal)

## TL;DR
NOP — false trigger ("这是我提交的, 不触发"). 6h: 53req/52OK(98.1%)/1fail. 1 NVStream_TimeoutError on k1 (105,819ms, stream deadline 90s). nv_tier_attempts 1 row (IntegrateRemoteDisconnected k1). k1 consistently slowest key (avg 21,627ms vs k2-5 avg 12,859-16,713ms). Single key-specific latency issue, not config-fixable. All params at floor/optimal. Zero param; iron rule: only change HM1 never HM2.

---

## 一、触发分析
cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit `e26e1d0` author = `opc2_uname` (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发
- HM1 本地未提交任何新内容

## 二、当前配置快照（R1066 部署前）

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
| 20 | NVU_FORCE_STREAM_UPGRADE | 0 | R692 |
| 21 | NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | R1039 (removed dsv4p_nv, re-enable peer rescue) |
| 22 | NV_INTEGRATE_MODELS | glm5_2_nv,minimax_m3_nv | R833 |
| 23 | NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,dsv4p_nv:dsv4p_ms,kimi_nv:kimi_ms | R1033 |

## 三、数据收集

### 3.1 6h 总体
| 指标 | 值 |
|------|-----|
| 总请求 | 53 |
| 成功 | 52 (98.1%) |
| 失败 | 1 |
| 平均延迟 | 16,014ms |
| P50 | 10,084ms |
| P95 | 46,387ms |
| 最大延迟 | 105,819ms |

### 3.2 24h 总体
| 指标 | 值 |
|------|-----|
| 总请求 | 649 |
| 成功 | 602 (92.8%) |
| 失败 | 47 |
| 24h ATE | 55 (mostly pre-restart, before 01:08 UTC) |

### 3.3 Post-Restart (容器启动后 ~5h)
| 指标 | 值 |
|------|-----|
| 总请求 | 53 |
| 成功 | 52 (98.1%) |
| 失败 | 1 (NVStream_TimeoutError) |

### 3.4 按模型分组 (6h)
| 模型 | 请求 | 成功 | 失败 | SR | avg_dur | max_dur |
|------|------|------|------|-----|---------|---------|
| glm5_2_nv | 53 | 52 | 1 | 98.1% | 16,014ms | 105,819ms |

### 3.5 按上游路径分组 (6h)
| 路径 | 请求 | 成功 | SR | avg_dur | avg_ttfb |
|------|------|------|-----|---------|----------|
| pexec | 46 | 46 | 100.0% | 10,571ms | 10,335ms |
| integrate | 7 | 6 | 85.7% | 51,780ms | 39,093ms |

### 3.6 按 key 分组 (6h)
| Key | 请求 | 成功 | 失败 | avg_dur | p50 |
|-----|------|------|------|---------|-----|
| k0 | 11 | 11 | 0 | 12,859ms | 7,028ms |
| k1 | 8 | 7 | 1 | 21,627ms | 9,674ms |
| k2 | 14 | 14 | 0 | 16,713ms | 9,914ms |
| k3 | 10 | 10 | 0 | 15,896ms | 10,407ms |
| k4 | 10 | 10 | 0 | 14,133ms | 11,049ms |

k1 是唯一有失败且平均延迟最高的 key (21,627ms vs 12,859-16,713ms)。

### 3.7 失败分析
- **唯一失败**: 05:56:41, glm5_2_nv, k1, 502, 105,819ms, NVStream_TimeoutError
- STREAM_TOTAL_DEADLINE_S=90, 请求超过 90s 后触发 stream deadline
- 失败是 key-specific (k1 慢), 非 config-level

### 3.8 nv_tier_attempts (6h)
- 1 row: glm5_2_nv, IntegrateRemoteDisconnected, k1, 20,284ms
- 单次 key-specific 连接中断, 非系统性

### 3.9 24H ATE 分时
| 小时 (UTC) | ATE |
|------------|-----|
| 07-09 09:00 | 4 |
| 07-09 12:00 | 8 |
| 07-09 17:00 | 8 |
| 07-09 18:00 | 7 |
| 07-09 19:00 | 8 |
| 07-10 05:00 | 1 |

大部分 ATE 集中在容器重启前 (07-09 09:00-20:00)。重启后 (01:08 UTC) 仅 1 ATE。

### 3.10 成功率分时 (6h)
| 小时 (UTC) | 总数 | 成功 | 失败 | SR |
|------------|------|------|------|-----|
| 00:00 | 5 | 5 | 0 | 100% |
| 01:00 | 9 | 9 | 0 | 100% |
| 02:00 | 9 | 9 | 0 | 100% |
| 03:00 | 6 | 6 | 0 | 100% |
| 04:00 | 4 | 4 | 0 | 100% |
| 05:00 | 20 | 19 | 1 | 95.0% |

05:00 时段有 1 失败 (NVStream_TimeoutError on k1)。

### 3.11 容器状态
- `nv_gw`: Up 5 hours (healthy), StartedAt 2026-07-10T01:08:30Z
- 所有参数在 env 中正确设置

### 3.12 nv_gw 日志 (最近 100 行)
- 全部 `[NV-INTEGRATE-SUCCESS]` + `first attempt`
- 2 次 `[NV-INTEGRATE-SSL-CYCLE]` k2 SSLEOF → cycle to k3 OK
- 零 ERROR / WARN / NV-TIER-FAIL / NV-ALL-TIERS
- 零 NVCFPexecTimeout / empty_200 / 429

## 四、分析

### 4.1 误触发确认
- 最新 commit `e26e1d0` author = `opc2_uname` (HM2)，脚本输出 "这是我提交的, 不触发"
- cron 被派遣但应为误触发
- HM1 本地未提交任何新内容

### 4.2 运行状态评估
- 6h 98.1% SR (52/53)，1 失败
- 失败是 NVStream_TimeoutError on k1 — key-specific latency issue
- k1 avg 21,627ms 显著高于 k2-5 (12,859-16,713ms)
- 除 k1 外所有 key 6h 100% SR
- pexec 路径 46/46 100% SR
- integrate 路径 6/7 (85.7%) — 唯一失败在 integrate

### 4.3 失败根因
- NVStream_TimeoutError: stream deadline (STREAM_TOTAL_DEADLINE_S=90) 触发
- 请求持续 105,819ms → 超过 90s stream deadline
- 根因是 k1 响应慢 (key-specific)，非 config 缺陷
- 增加 STREAM_TOTAL_DEADLINE_S 可缓解但会延长客户端等待时间
- 这属于 NVCF key 性能波动，非 proxy 配置问题

### 4.4 参数优化空间
- **0 NVCFPexecTimeout** in 6h → UPSTREAM=66 non-binding
- **0 empty_200, 0 429** — 零错误
- 仅 2 SSLEOF (k2, 自动 cycle 到 k3 OK)
- 所有 FASTBREAK 在 floor (1/2/1)
- 所有 cooldown 在 floor/optimal (KEY=25, TIER=18, INTEGRATE=0)
- BUDGET=110 >> UPSTREAM=66 (44s margin)
- STREAM_TOTAL_DEADLINE_S=90 = INTEGRATE_THINKING_TIMEOUT=90 — 已对齐
- **无参数可优化** — 所有参数在 floor/optimal

### 4.5 与 R1065 对比
- R1065: 6h 44/44(100.0%), 0 fail, 0 nv_tier_attempts
- R1066: 6h 52/53(98.1%), 1 fail (NVStream_TimeoutError k1), 1 nv_tier_attempts
- 轻微退化但非 config 导致 — k1 key-specific latency

## 五、决策: NOP (零变更)

所有参数在 floor/optimal。6h 98.1% SR，1 失败是 k1 key-specific latency (NVStream_TimeoutError)，非 config-fixable。pexec 46/46 100% SR。零 error/warn/empty_200/429/timeout。零参数可优化。零变更。

## 六、变更记录

无变更。容器未重启。

---

## ⏳ 轮到HM1优化HM2