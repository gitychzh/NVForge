# R1166: dsv4f0731_nv Self-Opt NOP Round

**日期**: 2026-08-08
**容器**: `dsvf0731_nv40666` (端口 40666, DeepSeek V4 Pro via NVCF pexec)
**模型**: dsv4f0731_nv
**采集**: 06:36 UTC
**结论**: NOP — 系统健康，无参数修改

## 数据 (30min 窗口)

| 指标 | 值 |
|---|---|
| 总量 / 成功 / 失败 | 140 / 140 / 0 |
| SR% | **100%** |
| Avg / P50 / P95 / Max | 12972ms / 9597ms / 33818ms / 48294ms |
| 错误分类 | (空 — 0 错误) |
| 429 计数 | 0 |
| fallback (hm4104) | 0（最近 5min 无 fallback 日志） |

## Per-key 分析

全部 5 个 key 零错误、负载均衡、延迟健康：

| key | 请求数 | avg(ms) | max(ms) | 错误 |
|---|---|---|---|---|
| k0 | 29 | 10799 | 24346 | 0 |
| k1 | 27 | 12106 | 26163 | 0 |
| k2 | 27 | 12392 | 37444 | 0 |
| k3 | 27 | 13937 | 31281 | 0 |
| k4 | 30 | 15504 | 44896 | 0 |

key 分布均匀（27–30 请求/key），延迟方差略大于上轮（k0 avg=10799 vs k4 avg=15504），但全部 0 错误，单 key max 均 <50s（UPSTREAM_TIMEOUT=50 内），属正常抽样波动，无单 key 劣化。k4 max=44896ms 为单点峰值，avg 15504ms 健康。

注: key_cycle_429s 计数 0|49 / 1|91（历史累积计数器，本窗口实际 429=0，无需关注）。

## Upstream type

- `nvcf_pexec`: 140/140 = 100% SR, avg 12972ms（无 integrate 分流，全走 pexec，与 R1165 一致）

## finish_reason

- tool_calls: 114 (81.4%)
- stop: 26 (18.6%)

正常（工具调用为主，符合 agent 使用模式，占比与 R1165 的 83.6% 基本持平）。

## 趋势

- 6h: 2025 记录, 2017 success = **99.6% SR** (8 失败)
- 3h 逐小时: 22:00 185/185=100%, 21:00 355/355=100%, 20:00 405/405=100%, 19:00 158/158=100%
- 24h all_tiers_exhausted: 73（历史累积，本时段 429=0，近期无聚集）

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

## 上次修改效果 (R1165 → R1166)

R1165 SR=100% (171/171)。本轮 SR=**100%** (140/140)，持平，仍为满格。
Avg 从 10784ms 微增至 12972ms（+2188ms），P50 8365→9597ms，属正常波动。
请求量 171→140 略降，属正常波动。零错误、零 429、零 fallback 延续。系统持续稳态。

## 结论

SR=100% 连续多轮稳定（R1153–R1166 满格），零错误、零 429、零 fallback，key 全部健康且近满负载分布，
延迟稳定（P95<34s，单 key max<50s 超时阈值内）。所有 NOP 判定标准（SR>95%、无异常错误、延迟稳定）均满足。
**不改任何参数。**（"改前必有数据"铁律 — 100% SR 下无任何可调项的数据支撑。）

## 下一步建议

- 保持观察。系统健康稳定，SR 连续多轮（R1153–R1166）100%。
- 预置对策（仅当信号出现才动作）:
  - 429 回升 → `KEY_COOLDOWN_S` 30→60s
  - RemoteDisconnected/超时聚集拉低 SR → `UPSTREAM_TIMEOUT` 50→35s
  - stream 死链重新聚集（≥3/30min 或单 key 集中）→ 源码级修复 `handlers.py`
  - IncompleteRead/SSLEOFError 聚集（≥30/h）→ 检查对应 key 的 SOCKS5 端口
- 继续监控 5 个 SOCKS5 端口与 key 级瞬时错误复发风险。