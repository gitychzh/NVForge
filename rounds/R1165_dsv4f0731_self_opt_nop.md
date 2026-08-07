# R1165: dsv4f0731_nv Self-Opt NOP Round

**日期**: 2026-08-08
**容器**: `dsvf0731_nv40666` (端口 40666, DeepSeek V4 Pro via NVCF pexec)
**模型**: dsv4f0731_nv
**采集**: 06:22 UTC
**结论**: NOP — 系统健康，无参数修改

## 数据 (30min 窗口)

| 指标 | 值 |
|---|---|
| 总量 / 成功 / 失败 | 171 / 171 / 0 |
| SR% | **100%** |
| Avg / P50 / P95 | 10784ms / 8365ms / 26601ms |
| 错误分类 | (空 — 0 错误) |
| 429 计数 | 0 |
| fallback (hm4104) | 0（最近 5min 无 fallback 日志） |

## Per-key 分析

全部 5 个 key 负载均衡、延迟健康、零错误：

| key | 请求数 | avg(ms) | max(ms) | 错误 |
|---|---|---|---|---|
| k0 | 33 | 9640 | 24209 | 0 |
| k1 | 35 | 11844 | 26209 | 0 |
| k2 | 34 | 8791 | 25693 | 0 |
| k3 | 34 | 11629 | 25631 | 0 |
| k4 | 35 | 11919 | 30287 | 0 |

key 分布均匀（33–35 请求/key），延迟方差小（avg 8791–11919ms），p95 全部 <27s，无单 key 劣化。（k4 max 30287ms 为单点峰值，不影响整体，avg 11919ms 健康。）

注: key_cycle_429s 计数 0|65 / 1|106（历史累积计数器，本窗口实际 429=0，无需关注）。

## Upstream type

- `nvcf_pexec`: 171/171 = 100% SR, avg 10784ms（无 integrate 分流，与 R1164 一致全走 pexec）

## finish_reason

- tool_calls: 143 (83.6%)
- stop: 28 (16.4%)

正常（工具调用为主，符合 agent 使用模式，占比与 R1164 的 84.8% 基本持平）。

## 趋势

- 6h: 2024 记录, 2016 success = **99.6% SR** (8 失败)
- 3h 逐小时: 22:00 121/121=100%, 21:00 355/355=100%, 20:00 405/405=100%, 19:00 229/229=100%
- 24h all_tiers_exhausted: 84（历史累积，本时段 429=0，近期无聚集）

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

## 上次修改效果 (R1164 → R1165)

R1164 SR=100% (184/184)。本轮 SR=**100%** (171/171)，持平，仍为满格。
Avg 从 10533ms 微增至 10784ms（+251ms，抽样噪声内，P50 8519→8365ms 略降）。
请求量 184→171 略降，属正常波动。零错误、零 429、零 fallback 延续。系统持续稳态。

## 结论

SR=100% 连续多轮稳定（R1153–R1165 满格），零错误、零 429、零 fallback，key 全部健康且近满负载分布，
延迟稳定。所有 NOP 判定标准（SR>95%、无异常错误、延迟稳定）均满足。
**不改任何参数。**（"改前必有数据"铁律 — 100% SR 下无任何可调项的数据支撑。）

## 下一步建议

- 保持观察。系统健康稳定，SR 连续多轮（R1153–R1165）100%。
- 预置对策（仅当信号出现才动作）:
  - 429 回升 → `KEY_COOLDOWN_S` 30→60s
  - RemoteDisconnected/超时聚集拉低 SR → `UPSTREAM_TIMEOUT` 50→35s
  - stream 死链重新聚集（≥3/30min 或单 key 集中）→ 源码级修复 `handlers.py`
  - IncompleteRead/SSLEOFError 聚集（≥30/h）→ 检查对应 key 的 SOCKS5 端口
- 继续监控 5 个 SOCKS5 端口与 key 级瞬时错误复发风险。