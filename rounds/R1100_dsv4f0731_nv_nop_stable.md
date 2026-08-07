# R1100 — dsv4f0731_nv40666 NOP (稳定运行)

## 结论
**不修改参数。** 当前系统运行稳定，无有效优化方向。

## 当前状态 (30min 窗口)

| 指标 | 值 |
|------|------|
| 请求数 | 155 |
| 成功数 | 154 |
| SR | 99.35% |
| Avg/P50/P95/Max | 11,536ms / 8,916ms / 33,878ms / 62,748ms |
| 错误 | 1 zombie_empty_completion (k1, 2001ms) |
| 429 | 0 |
| fallback (hm4104, 5min) | 0 |
| upstream | 100% nvcf_pexec |

## 6h Tier Attempts 分析

| 错误类型 | 计数 | 平均耗时 |
|----------|------|---------|
| pexec_success | 1,280 | 4,365ms |
| NVCFPexecRemoteDisconnected | 18 | 38,611ms |
| empty_200 | 3 | — |

**24h 历史趋势 (逐小时):**

从 UTC 09:00 起，dsv4f0731_nv 的错误率从 ~30-60/小时下降到 1-7/小时（~90% 下降）。

| 时段 (UTC) | RemoteDisconnected | Timeout | overloaded | empty_200 | total_errors |
|------------|-------------------|---------|------------|-----------|-------------|
| 06-08 15:00~08-07 08:00 | 15-37/h | 2-10/h | 0-14/h | 1-8/h | 31-58/h |
| **08-07 09:00~15:00** | **1-6/h** | **0** | **0** | **0-1/h** | **1-7/h** |

Overloaded(529) 从 UTC 03:00 起消失。Timeout 从 UTC 09:00 起消失。

## 24h 完整错误汇总
| 错误类型 | 计数 | 平均耗时 |
|----------|------|---------|
| NVCFPexecRemoteDisconnected | 528 | 40,570ms |
| NVCFPexecTimeout | 108 | 30,081ms |
| 529_nv_overloaded | 85 | — |
| empty_200 | 71 | — |
| 504_nv_gateway_timeout | 13 | — |
| budget_exhausted_after_connect | 2 | 1,142ms |

**144 requests 非200 in 24h** — 全部 502 或 499。

## Per-Key 延迟 (6h)

| Key | Success | avg_ms | Failures | avg_fail_ms |
|-----|---------|--------|----------|-------------|
| k0 | 266 | 4,197 | 3 RD | 34,915 |
| k1 | 234 | 4,321 | 5 RD | 36,049 |
| k2 | 264 | 4,267 | 3 RD | 38,934 |
| k3 | 258 | 4,361 | 6 RD+2 empty | 40,440 |
| k4 | 258 | 4,680 | 1 RD+1 empty | 50,573 |

Per-key 延迟方差小（4,197~4,680ms），keys 间均衡。

## 当前参数

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
| NV_KEY_INTEGRATE_KEYS | (空 — 未启用 integrate) |

## NOP 原因

1. **30min SR=99.35%** — 高于 95% 阈值，无修改必要
2. **6h 内 0 次 429** — key 循环冷却策略正常工作
3. **0 fallback** — hm4104 无 fallback 日志
4. **错误类型均为 NVCF 端** — RemoteDisconnected/overloaded 是 NVCF 基础设施层问题，非可调参数可修复
5. **当前错误率极低** — 1-7/h，历史最优水平
6. **Per-key 均衡** — 各 key 延迟/成功率无显著差异
7. **99% 请求 tool_calls** — dsv4f0731_nv 模型正常产生工具调用

## 后续建议

- 继续保持观察。如果有 NVCF 出现批量 429 时再考虑调整 KEY_COOLDOWN_S
- 当前启用 integrate.api 没有明显收益（pexec SR=99.35%），不优先考虑
- 当 RemoteDisconnected 率恢复到 30+/h 时，考虑降低 UPSTREAM_TIMEOUT 到 60s 以更快完成 key 循环