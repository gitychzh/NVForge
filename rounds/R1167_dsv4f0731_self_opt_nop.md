# R1167: dsv4f0731_nv Self-Opt NOP Round

**日期**: 2026-08-08
**容器**: `dsvf0731_nv40666` (端口 40666, DeepSeek V4 Pro via NVCF pexec)
**模型**: dsv4f0731_nv
**采集**: 07:00 UTC
**结论**: NOP — 系统健康，无参数修改

## 数据 (30min 窗口)

| 指标 | 值 |
|---|---|
| 总量 / 成功 / 失败 | 107 / 104 / 3 |
| SR% | **97.2%** |
| Avg / P50 / P95 | 20245ms / 12984ms / 71679ms |
| 错误分类 | all_tiers_exhausted: 1, buffer_exhausted: 1, stream_no_content_gap: 1 |
| 429 计数 | 0 |
| fallback (hm4104) | 0（最近 5min 无 fallback 日志） |

## Per-key 分析

| key | 200数 | avg(ms) | 错误 |
|---|---|---|---|
| k0 | 23 | 18638 | all_tiers_exhausted: 1 |
| k1 | 16 | 15502 | stream_no_content_gap: 1 |
| k2 | 25 | 17461 | 0 |
| k3 | 16 | 13252 | 0 |
| k4 | 24 | 23994 | buffer_exhausted: 1 |

3 个错误分布于 **3 个不同 key**（k0/k1/k4）且为 **3 种不同类型**，无单 key 聚集、无成对复发，属瞬态噪声。per-key 延迟健康（avg 13.2–24.0s），负载分布均匀（成功数 16–25/key）。key_cycle_429s 为历史累积计数器（0|34 / 1|73），本窗口实际 429=0。

## Upstream type

- `nvcf_pexec`: 107/104 = **97.2% SR**, avg 20132ms（无 integrate 分流，全走 pexec，与 R1165/R1166 一致）

## finish_reason

- tool_calls: 90 (86.5%)
- stop: 14 (13.5%)

正常（工具调用为主，占比较上轮 81.4% 略升，仍在 agent 使用模式正常范围）。

## 趋势

- **6h: 1995 记录, 1984 success = 99.4% SR** (11 失败)
- 3h 逐小时（低流量 23:00 仅有 1–6 条，剔除）:
  - 22:00 | 265 req | 262 ok | avg 14267ms | p95 43008ms
  - 21:00 | 355 req | 355 ok | avg 10325ms | p95 24967ms
  - 20:00 | 397 req | 397 ok | avg 9456ms  | p95 21352ms
- 6h 逐小时 SR 全为 99–100%，p95 稳定在 21–43s，**无系统劣化**。
- 24h all_tiers_exhausted: 65（历史累积，本时段实际 ATE=1，非聚集）

## 参数状态 (unchanged)

```
UPSTREAM_TIMEOUT=50
TIER_TIMEOUT_BUDGET_S=180 / NVU_TIER_BUDGET_DSV4F_NV=180
KEY_COOLDOWN_S=30
TIER_COOLDOWN_S=90
NVU_PEXEC_TIMEOUT_FASTBREAK=3 / NVU_EMPTY_200_FASTBREAK=3
NVU_BUFFER_TIMEOUT_STAIRS=90×5 / NVU_BUFFER_TOTAL_DEADLINE_S=450 / NVU_BUFFER_MAX_RETRIES=5
NVU_PEER_FALLBACK_ENABLED=0
NVU_KEYMGR_429_BASE/MAX_COOLDOWN=120/120
NVU_KEYMGR_CONN_BASE_COOLDOWN=30 / FAIL_THRESHOLD=3 / MAX=60 / LONG=120
NVU_PROBE_ENABLED=1 / PROBE_INTERVAL=15 / PROBE_TIMEOUT=10
PROXY_TIMEOUT=300 / PROXY_ROLE=passthrough
```

无 integrate keys（全走 nvcf_pexec）。本窗口 429=0，无调 budget/cooling 的数据需求。

## 上次修改效果 (R1166 → R1167)

R1166 SR=**100%** (140/140)。本轮 SR=**97.2%** (104/107)，回落 2.8 个百分点。回落全部由 3 个单点瞬态错误贡献（ate/buffer/gap 各 1，均 <1% 命中率），非系统性退化。Avg 从 12972ms 升至 20245ms（+7273ms）—— 部分由 3 个慢错误消耗 tier budget（最慢 138085ms）拉高，6h 逐小时 avg 稳定（9.5–15s）证明常态延迟未变。**无参数失效，属抽样噪声。**

## 结论

SR=97.2% > 95% NOP 阈值；0 429、0 fallback；3 个错误为 3 种不同类型、分散于 3 个独立 key 的**单点瞬态**（各自命中率 <1%）；6h SR=99.4% 表明整体链路稳定；逐小时 p95 未持续超阈值（仅 30min 小样本被慢错误拉高到 71.7s，常态 p95 ≤43s）。所有 NOP 判定标准满足。**不改任何参数。**（"改前必有数据"铁律 — 单点噪声不足以支撑任何调参。）

## 下一步建议

- 保持观察。单点瞬态错误（ate/buffer/gap）如无复发，下轮仍 NOP。
- 预置对策（仅当信号出现才动作）:
  - **若 30min 再出现 ≥3 个 all_tiers_exhausted 且单 key 聚集** → 提示 budget 分配问题，考虑检查该 key 出口 IP / 代理质量，而非直接改参数。
  - 429 回升（≥5/30min） → `KEY_COOLDOWN_S` 30→60s（当前 429=0，无此需求）。
  - stream_no_content_gap / buffer_exhausted 聚集（≥2/30min 同种） → buffer 死链信号，考虑 `NVU_BUFFER_TIMEOUT_STAIRS` 90→75 或检查 NVU_BUFFER_CALLERS 链路。
  - NVStream_IncompleteRead 聚集（≥30/h） → 检查对应 key 的 SOCKS5 端口与 UPSTREAM_TIMEOUT。
- 关注 30min p95 是否为小样本误导（本轮常态 p95 应 ≤43s，71.7s 为 3 慢错误所致）。