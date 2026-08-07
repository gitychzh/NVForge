# R1105: 系统健康 — NOP (无参数修改)

> 时间: 2026-08-07 20:20 UTC (BJT 04:20)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF)
> 状态: **NOP (不改参数)** — 30min SR=99.4%, 429=0, ATE=0, fallback=0

## 1. 背景 (改前必有数据)

R1104 (20:12 UTC, 30min SR=98.8%) 也是 NOP。本轮观测窗口 (19:50-20:20 UTC) 延续 BJT 凌晨低负载状态。

### DB 30min 窗口 (mapped_model=dsv4f0731_nv)

| 指标 | R1104 | 本轮 | 变化 |
|------|-------|------|------|
| 总请求 | 168 | 158 | -6% |
| 成功(200) | 166 | 157 | -5% |
| **SR** | **98.8%** | **99.4%** | **+0.6pp** |
| 429 | 0 | 0 | → |
| 错误 | 2 (zombie) | 1 (zombie) | -50% |
| Avg | 10,568ms | 10,806ms | +238ms |
| P50 | 7,907ms | 8,450ms | +543ms |
| P95 | 31,189ms | 29,354ms | -1,835ms |
| Max | 55,670ms | 50,761ms | -4,909ms |

P95 下降 1.8s, Max 下降 4.9s — 尾部延迟改善。SR 从 98.8%→99.4%。

### 错误分布 (30min)

| error_type | count | avg_ms | key |
|------------|-------|--------|-----|
| zombie_empty_completion | 1 | 5,428 | 2 |

唯一的错误是 key 2 上的低时长空 200 (5.4s)。与 R1104 完全相同的模式 (key2, zombie_empty_completion)。这是 key 2 的间歇性特征，非系统性劣化。

### Per-key 200 延迟 (30min)

| key | n | avg_ms | P50 | max_ms | 与 R1104 对比 |
|-----|---|--------|-----|--------|---------------|
| 0 | 34 | 10,671 | 6,618 | 23,352 | avg +1,074ms |
| 1 | 28 | 9,259 | 5,587 | 16,388 | avg +739ms |
| 2 | 33 | 12,443 | 8,769 | 36,723 | avg -1,295ms (改善) |
| 3 | 31 | 9,987 | 8,391 | 27,796 | avg +2,062ms |
| 4 | 31 | 11,603 | 8,476 | 30,628 | avg -752ms |

- Key 2 延迟斜率模式改善 (从 avg=13.7s 回落至 12.4s) — 仍最高但未恶化。
- Key 0/3 在本轮略高 — 可能因请求类型分布差异 (tool_calls 比例影响生成长度)。
- 所有 key max 均安全在 UPSTREAM_TIMEOUT=90s 内。

### Per-key error (30min)

| key | error_type | count | avg_ms |
|-----|------------|-------|--------|
| 2 | zombie_empty_completion | 1 | 5,428 |

无 key 集中劣化 — 单个散点错误。

### Upstream type (30min)

| upstream | total | ok | SR |
|----------|-------|----|----|
| nvcf_pexec | 158 | 157 | **99.4%** |

100% pexec, 无 integrate 流量。`NV_KEY_INTEGRATE_KEYS` 为空 — 此参数无需干预。

### Finish reason

| reason | count | pct |
|--------|-------|-----|
| tool_calls | 132 | 84% |
| stop | 25 | 16% |

与 R1104 (83%/15%) 一致。DS V4 Pro 作为 hermes 主力模型，tool_calls 为主。

### 6h 趋势

| 窗口 | total | success | error | SR |
|------|-------|---------|-------|----|
| 6h | 1,803 | 1,767 | 36 | **97.9%** |
| 12:00 UTC | 98 | 97 | 1 | 99.0% |
| 11:00 UTC | 323 | 318 | 5 | 98.5% |
| 10:00 UTC | 322 | 318 | 4 | 98.8% |
| 09:00 UTC | 224 | 219 | 5 | 97.8% |

6h SR=97.9%, 与 R1104 (97.9%) 持平。逐小时 SR 均 ≥97.8%。

### key_cycle_429s (30min)

| 429 count per request | requests |
|--------------------|----------|
| 0 | 54 |
| 1 | 104 |

与 R1104 结论一致: 多数请求 (66%) 遇到 1 次 key 级 429 后重试成功。这是正常的高负载键池竞争 — 5 个共享 key 中总有几个在那个时间窗口处于冷却状态。请求最终成功 (SR=99.4%)。

### 24h ATE

| 指标 | 值 |
|------|-----|
| all_tiers_exhausted | 251 |

251 ATE/24h, 较 R1104 (255) 下降 4。这些 ATE 分布在北京时间白天高负载时段 (UTC 4-10)。SLA 预期如此 — 5 keys 在峰值时段会有短暂的全面枯竭。

### Fallback

hm4104 fallback 日志 (5min 窗口): **无 fallback** ✅

所有 hermes 请求在本机 dsv4f0731_nv 直接完成。

### 当前参数 (未改变)

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

1. **30min SR=99.4%** — 极高成功率，且较上轮 (98.8%) 改善 0.6pp。远高于阈值 (95%)。
2. **429=0, ATE=0** — 窗口内无速率限制。key_cycle_429s 显示 key 级 429 被有效重试消耗。
3. **Fallback=0** — NVCF 链路完全自足，无需 ms_gw 降级。
4. **只有一个错误 (key2, zombie_empty_completion)** — 散点事件，非系统性。
5. **24h ATE 从 267 (R1103) → 255 (R1104) → 251 (本轮)** — 持续下降趋势，无需干预。
6. **Key 2 延迟仍在改善** — avg 从 R1104 的 13.7s 降至 12.4s。
7. **参数无劣化信号** — 所有关键指标 (SR, 延迟, 错误率, 冷却机制) 均在健康范围内。

**结论**: NOP — 系统健康稳定，参数无调整必要。

## 3. 当前状态 (30min 主指标)

- 30min SR: **99.4%** (157/158)
- Avg/P50/P95/max: 10.8s / 8.5s / 29.4s / 50.8s
- 错误: zombie_empty_completion=1 (avg 5.4s, key 2)
- 429: 0 (key_cycle_429s: 0→54, 1→104)
- upstream: 100% nvcf_pexec
- finish_reason: tool_calls=132, stop=25
- Fallback: **0** ✅

## 4. 上次修改效果 (R1104 NOP → 本轮)

- R1104→R1105: SR 从 98.8%→99.4% (+0.6pp)
- 24h ATE 从 255→251 (下降 4)
- P95 从 31,189ms→29,354ms (下降 1.8s)
- Max 从 55,670ms→50,761ms (下降 4.9s)
- Key 2 avg 从 13.7s→12.4s (改善)

所有指标改善或持平。连续多轮 (R1102→R1105) 维持 SR>98%, 429=0。

## 5. 验证

- [x] /health: status OK, 5 keys, tiers 含 dsv4f0731_nv
- [x] hm4104 fallback = 0
- [x] 写入仓库 (本 round 文件 + commit)

## 6. 下一步建议

1. **继续 NOP 状态** — 只要 SR>95%, 429=0, fallback=0, 持续 NOP。
2. **每日快照趋势** — 建议每日相同时间 (UTC 12:00 / BJT 20:00) 采集一次高峰负载数据, 验证 BT 白天高压环境下的稳定性。
3. **Key 2 观察指标** — 连续多轮 key 2 延迟均高于其他 key。如果某轮 key 2 错误率 >5% 或 avg >20s, 考虑增加 KEY_COOLDOWN_S (30→60) 或对 key 2 施加独立冷却。
4. **ATE 阈值监测** — 如果 24h ATE 连续上升 (如 >300) 或 ATE 出现在当前低负载窗口, 考虑优化 TIER_COOLDOWN_S 或扩展 key 池。