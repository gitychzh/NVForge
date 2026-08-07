# R1162: dsv4f0731_nv Self-Opt NOP Round

**日期**: 2026-08-08
**容器**: `dsvf0731_nv40666` (端口 40666, DeepSeek V4 Pro via NVCF pexec)
**模型**: dsv4f0731_nv
**采集**: 06:10:45 UTC
**结论**: NOP — 系统健康，无参数修改

## 数据 (30min 窗口)

| 指标 | 值 |
|---|---|
| 总量 / 成功 / 失败 | 189 / 189 / 0 |
| SR% | **100%** |
| Avg / P50 / P95 | 10119ms / 8588ms / 24181ms |
| 错误分类 | (空 — 0 错误) |
| 429 计数 | 0 |
| fallback (hm4104) | 0（最近 5min 无 fallback 日志） |

## Per-key 分析

全部 5 个 key 负载均衡、延迟健康、零错误：

| key | 请求数 | avg(ms) | p95(ms) | 错误 |
|---|---|---|---|---|
| k0 | 36 | 10191 | 21807 | 0 |
| k1 | 38 | 10779 | 23234 | 0 |
| k2 | 38 | 8499 | 24394 | 0 |
| k3 | 39 | 11721 | 25676 | 0 |
| k4 | 38 | 9368 | 22004 | 0 |

key 分布均匀（36–39 请求/key），延迟方差小（avg 8499–11721ms），p95 全部 <26s，无单 key 劣化。

注: key_cycle_429s 计数 0|72 / 1|117（历史累积计数器，本窗口实际 429=0，无需关注）。

## Upstream type

- `nvcf_pexec`: 189/189 = 100% SR, avg 10119ms（无 integrate 分流，与 R1161 一致全走 pexec）

## finish_reason

- tool_calls: 162 (85.7%)
- stop: 27 (14.3%)

正常（工具调用为主，符合 agent 使用模式，占比与 R1161 的 85.8% 基本持平）。

## 趋势

- 6h: 2022 记录, 2014 success = **99.6% SR** (8 失败)
- 3h 逐小时: 22:00 61/61=100%, 21:00 355/355=100%, 20:00 405/405=100%, 19:00 300/299=99.7%
- 24h all_tiers_exhausted: 89（历史累积，本时段 429=0，近期无聚集）

## 参数状态 (unchanged)

```
UPSTREAM_TIMEOUT=50
TIER_TIMEOUT_BUDGET_S=180
NVU_TIER_BUDGET_DSV4F0731_NV=180
KEY_COOLDOWN_S=30
TIER_COOLDOWN_S=90
NVU_PEXEC_TIMEOUT_FASTBREAK=3
NVU_EMPTY_200_FASTBREAK=3
NVU_BUFFER_TIMEOUT_STAIRS=90×5
NVU_PEER_FALLBACK_ENABLED=0
NVU_KEYMGR_429_BASE/MAX_COOLDOWN=120/120
NVU_KEYMGR_CONN_BASE_COOLDOWN=30 / FAIL_THRESHOLD=3 / MAX=60 / LONG=120
```

无 integrate keys（全走 nvcf_pexec）。本窗口 ATE=0，无调 budget 的数据需求。

## 上次修改效果 (R1161 → R1162)

R1161 SR=100% (190/190)。本轮 SR=**100%** (189/189)，持平，仍为满格。
Avg 从 9903ms 微增至 10119ms（+216ms，抽样噪声内，P50 8516→8588ms 微升）。
请求量 190→189 基本持平。零错误、零 429、零 fallback 延续。系统持续稳态。

## 结论

SR=100% 连续多轮稳定，零错误、零 429、零 fallback，key 全部健康且近满负载分布，
延迟稳定。所有 NOP 判定标准（SR>95%、无异常错误、延迟稳定）均满足。
**不改任何参数。**（"改前必有数据"铁律 — 100% SR 下无任何可调项的数据支撑。）

## 下一步建议

- 保持观察。系统健康稳定，SR 连续多轮 100%。
- 预置对策（仅当信号出现才动作）:
  - 429 回升 → `KEY_COOLDOWN_S` 30→60s
  - RemoteDisconnected/超时聚集拉低 SR → `UPSTREAM_TIMEOUT` 50→35s
  - stream 死链重新聚集（≥3/30min 或单 key 集中）→ 源码级修复 `handlers.py`
  - IncompleteRead/SSLEOFError 聚集（≥30/h）→ 检查对应 key 的 SOCKS5 端口
- 继续监控 5 个 SOCKS5 端口与 key 级瞬时错误复发风险。