# R1118 — dsv4f0731_nv40666 NOP (持续稳定)

## 结论
**不修改参数。** 系统保持稳定运行，30min SR=99.3%，无有效优化方向。

## 当前状态 (30min 窗口 23:04~23:34 UTC+8)

| 指标 | 值 |
|------|------|
| 请求数 | 146 |
| 成功数 | 145 |
| SR | 99.32% |
| Avg/P50/P95/Max | 12,354ms / 9,754ms / 34,350ms / 60,586ms |
| 错误 | 1 zombie_empty_completion (k1, 2001ms) |
| 429 | 0 |
| fallback (hm4104, 5min) | 0 |
| upstream | 100% nvcf_pexec |
| finish_reason: tool_calls | 119 (81.5%) |
| finish_reason: stop | 26 (17.8%) |
| key_cycle_429s | 0 on all keys |

## 6h/24h 趋势

| 时段 | Total | Success | Failed | Fallback | Avg Latency |
|------|-------|---------|--------|----------|-------------|
| 30min | 146 | 145 | 1 | 0 | 12,354ms |
| 3h 15:00 | 165 | 164 | 1 | 0 | 12,503ms |
| 3h 14:00 | 294 | 293 | 1 | 0 | 11,974ms |
| 3h 13:00 | 282 | 279 | 3 | 0 | 11,388ms |
| 3h 12:00 | 107 | 105 | 2 | 0 | 11,853ms |
| 6h total | 1,839 | 1,819 | 20 | 0 | — |
| **6h SR** | | **98.9%** | | | |

### 24h all_tiers_exhausted: 148

## Per-Key 性能 (30min)

| Key | Success | avg_ms | max_ms | Errors |
|-----|---------|--------|--------|--------|
| k0 | 31 | 12,793 | 35,479 | 0 |
| k1 | 25 | 10,823 | 21,524 | 1 zombie_empty_completion |
| k2 | 32 | 14,559 | 41,368 | 0 |
| k3 | 28 | 9,935 | 22,829 | 0 |
| k4 | 29 | 13,465 | 32,573 | 0 |

Per-key 分布均衡，k2 延迟略高但无错误，k1 唯一错误是 2001ms 的 zombie empty，非严重问题。

## 当前参数 (未改动)

| 参数 | 值 |
|------|------|
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
| NVU_PROBE_TIMEOUT | 10 |
| NV_KEY_INTEGRATE_KEYS | (空 — 未启用 integrate) |

## NOP 原因

1. **30min SR=99.3%** — 高于 95% 阈值，无需修改
2. **6h SR=98.9%** — 持续稳定，无退化趋势
3. **0 次 429** — 无 rate limit 问题
4. **0 fallback** — hm4104 无 fallback 触发
5. **错误极低** — 仅 1 zombie_empty_completion（NVCF 空响应，非可优化参数）
6. **Per-key 均衡** — 各 key 延迟分布在 9,935~14,559ms 之间，方差正常
7. **全部 pexec** — integrate 未启用，pexec 链路质量好
8. **24h all_tiers_exhausted=148** — 考虑到 24h 总量约 5,909 请求（基于 6h 1,839 推算），ATE 率约 2.5%，在可接受范围内

## 上次修改效果 (R1100 → R1118)

R1100 报告 30min SR=99.35%，当前 30min SR=99.32% — 持续稳定在同一水平。当前 6h SR=98.9% 也接近 R1100 时期的水平。未发生退化。

## 下一步建议

- 保持观察。如果出现以下情况再调整参数：
  - 429 率回升 → 增加 KEY_COOLDOWN_S 到 60 或 120
  - RemoteDisconnected/overloaded 频发（30+/h）→ 降低 UPSTREAM_TIMEOUT 到 60s 加速 key 循环
  - Max 延迟持续 >60s → 检查是否有长时间僵尸连接
- 当前不启用 integrate.api，pexec 链路表现良好，无切换必要