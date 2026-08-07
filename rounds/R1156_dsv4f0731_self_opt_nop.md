# R1156: dsv4f0731_nv Self-Opt NOP Round

**日期**: 2026-08-08
**容器**: `dsvf0731_nv40666` (端口 40666, DeepSeek V4 Pro via NVCF pexec)
**结论**: NOP — 系统健康，无参数修改

## 数据 (30min 窗口)

| 指标 | 值 |
|---|---|
| 总量 / 成功 / 失败 | 167 / 167 / 0 |
| SR% | **100%** |
| Avg / P50 / P95 / Max | 10688ms / 8496ms / 26858ms / 39804ms |
| 错误分类 | (空 — 0 错误) |
| 429 计数 | 0 |
| fallback (hm4104) | 0（最近 5min 无 fallback 日志） |

## Per-key 分析

全部 5 个 key 负载均衡、延迟健康、零错误：

| key | 请求数 | avg(ms) | max(ms) | 错误 |
|---|---|---|---|---|
| k0 | 36 | 10373 | 31720 | 0 |
| k1 | 33 | 11628 | 23791 | 0 |
| k2 | 32 | 10571 | 24581 | 0 |
| k3 | 32 | 9575 | 21620 | 0 |
| k4 | 34 | 11268 | 28410 | 0 |

key 分布均匀（32–36 请求/key），延迟方差小（avg 9575–11628ms，偏差 ~±10%），无单 key 劣化。

## Upstream type

- `nvcf_pexec`: 167/167 = 100% SR, avg 10688ms（无 integrate 分流）

## finish_reason

- tool_calls: 143 (85.6%)
- stop: 24 (14.4%)

正常（工具调用为主，符合 agent 使用模式）。

## 趋势

- 6h: 1969/1961 记录, 1961 success = **99.6% SR** (8 失败)
- 3h 逐小时: 100%, 100%, 99.7%, 99.4%
- 24h all_tiers_exhausted: 95（历史累积，本时段 429=0，近期无聚集）

## 决策

依照决策原则：**数据正常（SR>95%, 无异常错误, 延迟稳定）→ NOP 轮，只报告状态不改参数。**

当前状态:
- 30min SR 100%，零错误，零 429，零 fallback
- 5 key 负载均衡、延迟紧致
- 6h/3h 趋势全部 ≥99.4%

**不做任何参数修改**，避免破坏健康稳定状态。与上一轮 R1155 状态完全一致，链路处于最佳状态。

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

- 继续观察。当前链路处于最佳状态（100% SR, 延迟 ~10s avg）。
- 若下一轮仍健康，继续 NOP。
- 关注点：是否出现 429 或 pexec timeout 聚集、某 key 延迟劣化、all_tiers_exhausted 上升。