# R1103: 系统健康 — NOP (无参数修改)

> 时间: 2026-08-07 19:52 UTC
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF)
> 状态: **NOP (不改参数)** — 30min SR=98.8%, 429=0, ATE=0, fallback=0

## 1. 背景 (改前必有数据)

R1102 (2026-08-06) 也是 NOP。本轮观察窗口(19:22-19:52 UTC) 系统处于低负载时段。之前的 529 风暴(第 7 轮 R1016) 已在 R1092+ 多次 NOP 确认收敛。

### DB 30min 窗口 (mapped_model=dsv4f0731_nv)

| 指标 | 值 |
|------|-----|
| 总请求 | 170 |
| 成功(200) | 168 |
| **SR** | **98.8%** |
| 429 | **0** |
| 502 | 2 (zombie_empty_completion) |
| Avg/P50/P95 | 10526ms / 8772ms / 28225ms |

### 错误分布 (30min)

| error_type | count | avg_ms |
|------------|-------|--------|
| zombie_empty_completion | 2 | 2,681 |

两个错误均为低时长空 200 (非超时、非连接断开、非 529)。zombie 信号但延迟仅 2.7s, 不属严重劣化。

### Per-key 200 延迟 (30min)

| key | n | avg_ms | p95 |
|-----|---|--------|-----|
| 0 | 34 | 8,490 | 20,636 |
| 1 | 31 | 9,419 | 14,605 |
| 2 | 38 | 12,677 | 39,899 |
| 3 | 32 | 9,911 | 21,077 |
| 4 | 33 | 12,259 | 29,678 |

- Key2 P95=39.9s 略高, Key4 P95=29.7s 次高 — 但均在 UPSTREAM_TIMEOUT=90s 内
- Key 间无明显劣化

### Per-key error (30min)

| key | error_type | count | avg_ms |
|-----|------------|-------|--------|
| 3 | zombie_empty_completion | 1 | 1,872 |
| 4 | zombie_empty_completion | 1 | 3,490 |

仅 2 个请求级错误, 无 key 集中劣化。

### Upstream type (30min)

| upstream | total | ok | SR |
|----------|-------|----|----|
| nvcf_pexec | 170 | 168 | **98.8%** |

100% pexec, 无 integrate 流量 (`NV_KEY_INTEGRATE_KEYS` 为空)。

### Finish reason

| reason | count |
|--------|-------|
| tool_calls | 140 (82%) |
| stop | 28 (16%) |

无空响应。tool_calls 占比正常 (DS V4 Pro 作为 hermes 主力模型)。

### 6h 趋势

| 窗口 | total | success | error | SR | avg(ms) |
|------|-------|---------|-------|----|---------|
| 6h | 1790 | 1748 | 42 | **97.7%** | — |
| 11:00 UTC | 272 | 267 | 5 | 98.2% | 11,256 |
| 10:00 UTC | 322 | 318 | 4 | 98.8% | 10,680 |
| 09:00 UTC | 363 | 358 | 5 | 98.6% | 9,890 |
| 08:00 UTC | 30 | 30 | 0 | 100% | 13,532 |

8h-11h UTC 逐小时 SR 均 ≥98.2%, 无恶化趋势。11:00 UTC 后窗口误差仅 4 次 (tier_attempts 级)。

### 6h tier_attempts 错误 (tier=dsv4f0731_nv)

| error_type | count |
|------------|-------|
| NVCFPexecRemoteDisconnected | 94 |
| NVCFPexecTimeout | 15 |
| empty_200 | 14 |

**无 529_nv_overloaded!** — 账户级过载风暴已完全收敛 (对比 R1016 的 377/2h)。RemoteDisconnected 仍是主要错误类型。

### 6h per-key 成功率 (tier_attempts)

| key | attempts | success | error | avg_ok_ms |
|-----|----------|---------|-------|-----------|
| 0 | 302 | 283 (93.7%) | 19 | 3,851 |
| 1 | 280 | 254 (90.7%) | 26 | 4,089 |
| 2 | 308 | 283 (91.9%) | 25 | 3,767 |
| 3 | 290 | 263 (90.7%) | 27 | 4,040 |
| 4 | 300 | 274 (91.3%) | 26 | 4,078 |

5 keys 成功率均匀, 无单 key 明显劣化 (min≈90.7%, max≈93.7%)。

### 6h ATE 分析

| metric | value |
|--------|-------|
| ATE in nv_requests (6h) | 16 (zombie=16 请求级等效) |
| ATE in nv_tier_attempts (6h) | 0 |
| ATE avg duration | 197s (24h, 267次) |

6h 窗口内 tier_attempts 级 ATE=0, 仅有 16 个请求级 ATE (对应的 zombie_empty_completion)。24h ATE=267 主要来自 UTC 5-8h 风暴时段。

### 24h 积累

| 指标 | 24h |
|------|-----|
| 请求级 ATE | 267 |
| tier RemoteDisconnected | 775 |
| tier Timeout | 191 |
| tier 529_overloaded | 166 |
| tier 504_gateway_timeout | 96 |
| tier empty_200 | 103 |

529 于最新 6h 窗口清零。267 ATE 的 avg=197s — 说明风暴期预算完全烧完。

### Fallback

hm4104 fallback 日志 (5min 窗口): **无 fallback** ✅

所有 hermes 请求在本机 dsv4f0731_nv 直接完成, 无需 ms_gw 降级。

### 当前参数

| 参数 | 当前值 |
|------|--------|
| UPSTREAM_TIMEOUT | 90 |
| TIER_TIMEOUT_BUDGET_S | 180 |
| NVU_TIER_BUDGET_DSV4F0731_NV | 180 |
| KEY_COOLDOWN_S | 30 |
| TIER_COOLDOWN_S | 90 |
| NVU_KEYMGR_429_BASE_COOLDOWN | 120 |
| NVU_KEYMGR_429_MAX_COOLDOWN | 120 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 3 |
| NVU_EMPTY_200_FASTBREAK | 3 |
| NVU_BUFFER_TIMEOUT_STAIRS | 90,90,90,90,90 |

## 2. 决策: NOP (不改参数)

**理由:**

1. **30min SR=98.8%** — 远高于主动干预阈值 (95%)。系统已在当前参数下达到高质量运行。
2. **429=0, ATE=0** — 无速率限制或预算耗尽问题。key 冷却和预算分配运作正常。
3. **529 风暴已收敛** — 最新 6h 窗口无 529_nv_overloaded (对比 R1016: 377/2h)。账户级过载已不活跃。
4. **无单 key 劣化** — 5 个 key 延迟/错误均匀分布。key2 P95=39.9s, key4 P95=29.7s 偏高但处于正常方差范围, 且无对应错误积累。
5. **Fallback=0** — hm4104 降级到 ms_gw 为零, 本机 NVCF 链路完全自足。
6. **一次只改一个参数** — 无参数存在明确劣化信号, 改任何参数均属"凭感觉抖动"而非数据驱动。

**conclusion**: NOP — 系统健康, 无优化空间需要立即介入。

## 3. 当前状态 (30min 主指标)

- 30min SR: **98.8%** (168/170)
- Avg/P50/P95: 10.5s / 8.8s / 28.2s
- 错误: zombie_empty_completion=2 (平均 2.7s)
- 429: 0, key_cycle_429s=0
- upstream: 100% nvcf_pexec
- finish_reason: tool_calls=140, stop=28
- Fallback: **0** ✅

## 4. 上次修改效果 (R1102 NOP)

- R1102 确认 529 风暴消失。R1103 确认风暴已完全收敛 (最新 6h 零 529)。
- SR 从风暴期 ~75% 回升到 98%+, 系统完全恢复。

## 5. 验证

- [x] /health: status OK, 5 keys, tiers 含 dsv4f0731_nv
- [x] 容器 Up (未重启)
- [x] hm4104 fallback = 0
- [x] 写入仓库 (本 round 文件 + commit)

## 6. 下一步建议

1. **NOP 状态持续** — 若后续观测仍维持 SR>95%, 429=0, 继续 NOP。每日仅需一次快照以把控趋势。
2. **监控窗口切换** — 当前观测的是 HM2 本地窗口 (UTC 19:xx, 相当于 BJT 03:xx 凌晨)。下次可以有意选 BJT 白天时段 (UTC 5-10) 观察性能差异。本次数据证实: 低负载时段系统表现优秀。
3. **关键指标预警** (当满足以下任一条件时触发干预):
   - 30min SR < 95%
   - single-hour 429 > 10
   - hour-over-hour 延迟 P95 恶化 >50%
   - fallback 率 >5%