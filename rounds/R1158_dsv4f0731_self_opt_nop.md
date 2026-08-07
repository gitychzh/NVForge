# R1158: dsv4f0731_nv Self-Opt NOP Round

**日期**: 2026-08-08
**容器**: `dsvf0731_nv40666` (端口 40666, DeepSeek V4 Pro via NVCF pexec)
**结论**: NOP — 系统健康，无参数修改

## 数据 (30min 窗口, 采集 05:50:44)

| 指标 | 值 |
|---|---|
| 总量 / 成功 / 失败 | 165 / 165 / 0 |
| SR% | **100%** |
| Avg / P50 / P95 / Max | 10541ms / 8586ms / 25132ms / 32067ms |
| 错误分类 | (空 — 0 错误) |
| 429 计数 | 0 |
| fallback (hm4104) | 0（最近 5min 无 fallback 日志） |

## Per-key 分析

全部 5 个 key 负载均衡、延迟健康、零错误：

| key | 请求数 | avg(ms) | p95(ms) | 错误 |
|---|---|---|---|---|
| k0 | 34 | 10292 | 21947 | 0 |
| k1 | 34 | 10601 | 28555 | 0 |
| k2 | 33 | 10681 | 24841 | 0 |
| k3 | 32 | 9379 | 23517 | 0 |
| k4 | 32 | 11761 | 25226 | 0 |

key 分布均匀（32–34 请求/key），延迟方差小（avg 9379–11761ms），p95 全部 <29s，无单 key 劣化。

注: key_cycle_429s 计数 0|63 / 1|102（历史累积计数器，本窗口实际 429=0，无需关注）。

## Upstream type

- `nvcf_pexec`: 165/165 = 100% SR, avg 10541ms（无 integrate 分流）

## finish_reason

- tool_calls: 143 (86.7%)
- stop: 22 (13.3%)

正常（工具调用为主，符合 agent 使用模式）。

## 趋势

- 6h: 1987 记录, 1979 success = **99.6% SR** (8 失败)
- 3h 逐小时: 21:00 288/288=100%, 20:00 405/405=100%, 19:00 349/348=99.7%, 18:00 48/47=97.9%
- 24h all_tiers_exhausted: 93（历史累积，本时段 429=0，近期无聚集）

## 参数状态 (unchanged)

```
KEY_COOLDOWN_S=30
TIER_COOLDOWN_S=90
TIER_TIMEOUT_BUDGET_S=180
NVU_TIER_BUDGET_DSV4F0731_NV=180
UPSTREAM_TIMEOUT=50
NVU_PEXEC_TIMEOUT_FASTBREAK=3
NVU_EMPTY_200_FASTBREAK=3
```

无 integrate 使用（全走 nvcf_pexec）。

## 结论

SR=100% 连续稳定，零错误、零 429、零 fallback，key 健康，延迟稳定。所有 NOP 判定标准（SR>95%、无异常错误、延迟稳定）均满足。**不改任何参数。**