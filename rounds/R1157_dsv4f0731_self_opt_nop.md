# R1157: dsv4f0731_nv Self-Opt NOP Round

**日期**: 2026-08-08
**容器**: `dsvf0731_nv40666` (端口 40666, DeepSeek V4 Pro via NVCF pexec)
**结论**: NOP — 系统健康，无参数修改

## 数据 (30min 窗口)

| 指标 | 值 |
|---|---|
| 总量 / 成功 / 失败 | 170 / 170 / 0 |
| SR% | **100%** |
| Avg / P50 / P95 / Max | 10806ms / 8508ms / 25972ms / 39560ms |
| 错误分类 | (空 — 0 错误) |
| 429 计数 | 0 |
| fallback (hm4104) | 0（最近 5min 无 fallback 日志） |

## Per-key 分析

全部 5 个 key 负载均衡、延迟健康、零错误：

| key | 请求数 | avg(ms) | p95(ms) | 错误 |
|---|---|---|---|---|
| k0 | 36 | 10739 | 28438 | 0 |
| k1 | 34 | 11015 | 24199 | 0 |
| k2 | 33 | 11594 | 25179 | 0 |
| k3 | 32 | 8854 | 20542 | 0 |
| k4 | 35 | 11712 | 29890 | 0 |

key 分布均匀（32–36 请求/key），延迟方差小（avg 8854–11712ms），无单 key 劣化。

注: key_cycle_429s 计数为 0|66 / 1|104（历史累积计数器，本窗口实际 429=0，无需关注）。

## Upstream type

- `nvcf_pexec`: 170/170 = 100% SR, avg 10806ms（无 integrate 分流）

## finish_reason

- tool_calls: 148 (87.1%)
- stop: 22 (12.9%)

正常（工具调用为主，符合 agent 使用模式）。

## 趋势

- 6h: 1987 记录, 1979 success = **99.6% SR** (8 失败)
- 3h 逐小时: 21:00 256/256=100%, 20:00 405/405=100%, 19:00 349/348=99.7%, 18:00 81/80=98.8%
- 24h all_tiers_exhausted: 94（历史累积，本时段 429=0，近期无聚集）

## 决策

依照决策原则：**数据正常（SR>95%, 无异常错误, 延迟稳定）→ NOP 轮，只报告状态不改参数。**

当前状态:
- 30min SR 100%，零错误，零 429，零 fallback
- 5 key 负载均衡、延迟紧致
- 6h/3h 趋势全部 ≥98.8%

**不做任何参数修改**，避免破坏健康稳定状态。与上一轮 R1156 状态基本一致，链路处于最佳状态。

## 当前参数 (未变)

```
KEY_COOLDOWN_S=30, MIN_OUTBOUND_INTERVAL_S=5
TIER_COOLDOWN_S=90, TIER_TIMEOUT_BUDGET_S=180
NVU_TIER_BUDGET_DSV4F0731_NV=180, NVU_TIER_BUDGET_DSV4F_NV=180
UPSTREAM_TIMEOUT=50
NVU_KEYMGR_429_BASE_COOLDOWN=120, NVU_KEYMGR_429_MAX_COOLDOWN=120
NVU_KEYMGR_CONN_BASE_COOLDOWN=30, NVU_KEYMGR_CONN_FAIL_THRESHOLD=3
NVU_KEYMGR_CONN_LONG_COOLDOWN=120, NVU_KEYMGR_CONN_MAX_COOLDOWN=60
NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3
NVU_PROBE_TIMEOUT=10
NVU_PEER_FALLBACK_ENABLED=0
```

## 下一步建议

- 继续观察。当前链路处于最佳状态（100% SR, 延迟 ~10.8s avg）。
- 若下一轮仍健康，继续 NOP。
- 关注点：是否出现 429 或 pexec timeout 聚集、某 key 延迟劣化、all_tiers_exhausted 上升。