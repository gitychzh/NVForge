# R1163: dsv4f0731_nv Self-Opt NOP Round

**日期**: 2026-08-08
**容器**: `dsvf0731_nv40666` (端口 40666, DeepSeek V4 Pro via NVCF pexec)
**模型**: dsv4f0731_nv
**采集**: 06:14:45 UTC
**结论**: NOP — 系统健康，无参数修改

## 数据 (30min 窗口)

| 指标 | 值 |
|---|---|
| 总量 / 成功 / 失败 | 182 / 182 / 0 |
| SR% | **100%** |
| Avg / P50 / P95 | 10388ms / 8613ms / 25943ms |
| 错误分类 | (空 — 0 错误) |
| 429 计数 | 0 |
| fallback (hm4104) | 0（最近 5min 无 fallback 日志） |

## Per-key 分析

全部 5 个 key 负载均衡、延迟健康、零错误：

| key | 请求数 | avg(ms) | p95(ms) | 错误 |
|---|---|---|---|---|
| k0 | 36 | 9965 | 20420 | 0 |
| k1 | 37 | 11096 | 26542 | 0 |
| k2 | 36 | 8720 | 26223 | 0 |
| k3 | 36 | 11725 | 26381 | 0 |
| k4 | 37 | 10415 | 22959 | 0 |

key 分布均匀（36–37 请求/key），延迟方差小（avg 8720–11725ms），p95 全部 <27s，无单 key 劣化。

注: key_cycle_429s 计数 0|70 / 1|112（历史累积计数器，本窗口实际 429=0，无需关注）。

## Upstream type

- `nvcf_pexec`: 182/182 = 100% SR, avg 10388ms（无 integrate 分流，与 R1162 一致全走 pexec）

## finish_reason

- tool_calls: 154 (84.6%)
- stop: 28 (15.4%)

正常（工具调用为主，符合 agent 使用模式，占比与 R1162 的 85.7% 基本持平）。

## 趋势

- 6h: 2030 记录, 2022 success = **99.6% SR** (8 失败)
- 3h 逐小时: 22:00 83/83=100%, 21:00 355/355=100%, 20:00 405/405=100%, 19:00 273/272=99.6%
- 24h all_tiers_exhausted: 88（历史累积，本时段 429=0，近期无聚集）

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
PROXY_TIMEOUT=300 / PROXY_ROLE=passthrough
```

无 integrate keys（全走 nvcf_pexec）。本窗口 ATE=0，无调 budget 的数据需求。

## 上次修改效果 (R1162 → R1163)

R1162 SR=100% (189/189)。本轮 SR=**100%** (182/182)，持平，仍为满格。
Avg 从 10119ms 微增至 10388ms（+269ms，抽样噪声内，P50 8588→8613ms 基本持平）。
请求量 189→182 略降，属正常波动。零错误、零 429、零 fallback 延续。系统持续稳态。

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