# R1164: dsv4f0731_nv Self-Opt NOP Round

**日期**: 2026-08-08
**容器**: `dsvf0731_nv40666` (端口 40666, DeepSeek V4 Pro via NVCF pexec)
**模型**: dsv4f0731_nv
**采集**: 06:18 UTC
**结论**: NOP — 系统健康，无参数修改

## 数据 (30min 窗口)

| 指标 | 值 |
|---|---|
| 总量 / 成功 / 失败 | 184 / 184 / 0 |
| SR% | **100%** |
| Avg / P50 / P95 | 10533ms / 8519ms / 25179ms |
| 错误分类 | (空 — 0 错误) |
| 429 计数 | 0 |
| fallback (hm4104) | 0（最近 5min 无 fallback 日志） |

## Per-key 分析

全部 5 个 key 负载均衡、延迟健康、零错误：

| key | 请求数 | avg(ms) | p95(ms) | 错误 |
|---|---|---|---|---|
| k0 | 36 | 9609 | 24107 | 0 |
| k1 | 39 | 11398 | 23503 | 0 |
| k2 | 36 | 9079 | 25575 | 0 |
| k3 | 36 | 11420 | 24974 | 0 |
| k4 | 37 | 11072 | 25151 | 0 |

key 分布均匀（36–39 请求/key），延迟方差小（avg 9079–11420ms），p95 全部 <26s，无单 key 劣化。

注: key_cycle_429s 计数 0|71 / 1|113（历史累积计数器，本窗口实际 429=0，无需关注）。

## Upstream type

- `nvcf_pexec`: 184/184 = 100% SR, avg 10533ms（无 integrate 分流，与 R1163 一致全走 pexec）

## finish_reason

- tool_calls: 156 (84.8%)
- stop: 28 (15.2%)

正常（工具调用为主，符合 agent 使用模式，占比与 R1163 的 84.6% 基本持平）。

## 趋势

- 6h: 2030 记录, 2022 success = **99.6% SR** (8 失败)
- 3h 逐小时: 22:00 106/106=100%, 21:00 355/355=100%, 20:00 405/405=100%, 19:00 255/255=100%
- 24h all_tiers_exhausted: 87（历史累积，本时段 429=0，近期无聚集）

## 参数状态 (unchanged)

```
UPSTREAM_TIMEOUT=50
TIER_TIMEOUT_BUDGET_S=180
NVU_TIER_BUDGET_DSV4F_NV=180
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

## 上次修改效果 (R1163 → R1164)

R1163 SR=100% (182/182)。本轮 SR=**100%** (184/184)，持平，仍为满格。
Avg 从 10388ms 微增至 10533ms（+145ms，抽样噪声内，P50 8613→8519ms 略降）。
请求量 182→184 微增，属正常波动。零错误、零 429、零 fallback 延续。系统持续稳态。

## 结论

SR=100% 连续多轮稳定，零错误、零 429、零 fallback，key 全部健康且近满负载分布，
延迟稳定。所有 NOP 判定标准（SR>95%、无异常错误、延迟稳定）均满足。
**不改任何参数。**（"改前必有数据"铁律 — 100% SR 下无任何可调项的数据支撑。）

## 下一步建议

- 保持观察。系统健康稳定，SR 连续多轮（R1153–R1164）100%。
- 预置对策（仅当信号出现才动作）:
  - 429 回升 → `KEY_COOLDOWN_S` 30→60s
  - RemoteDisconnected/超时聚集拉低 SR → `UPSTREAM_TIMEOUT` 50→35s
  - stream 死链重新聚集（≥3/30min 或单 key 集中）→ 源码级修复 `handlers.py`
  - IncompleteRead/SSLEOFError 聚集（≥30/h）→ 检查对应 key 的 SOCKS5 端口
- 继续监控 5 个 SOCKS5 端口与 key 级瞬时错误复发风险。