# R1169: dsv4f0731_nv Self-Opt NOP Round

**日期**: 2026-08-08
**容器**: `dsvf0731_nv40666` (端口 40666, DeepSeek V4 Pro via NVCF pexec)
**模型**: dsv4f0731_nv
**采集**: 07:10 UTC
**结论**: NOP — 系统健康，无参数修改

## 数据 (30min 窗口)

| 指标 | 值 |
|---|---|
| 总量 / 成功 / 失败 | 92 / 89 / 3 |
| SR% | **96.7%** |
| Avg / P50 / P95 | 22884ms / 15231ms / 94630ms |
| 错误分类 | all_tiers_exhausted: 1, buffer_exhausted: 1, stream_no_content_gap: 1 |
| 429 计数 | 0 |
| key_cycle_429s | 0|30, 1|62（历史累积计数，本窗口 429=0） |
| fallback (hm4104) | 0（最近 5min 无 fallback 日志） |

## Per-key 分析

| key | 200数 | avg(ms) | 错误 |
|---|---|---|---|
| k0 | 16 | 21596 | all_tiers_exhausted: 1 |
| k1 | 15 | 19953 | stream_no_content_gap: 1 |
| k2 | 20 | 23371 | 0 |
| k3 | 16 | 12825 | 0 |
| k4 | 22 | 24310 | buffer_exhausted: 1 |

3 个错误分布于 **3 个不同 key**（k0/k1/k4）且为 **3 种不同类型**（ate/gap/buffer），无单 key 聚集、无成对复发，属瞬态噪声。per-key 延迟健康（avg 12.8–24.3s），负载均匀（ok 15–22/key）。

## Upstream type

- `nvcf_pexec`: 92/89 = **96.7% SR**, avg 22884ms（无 integrate 分流，全走 pexec，与 R1165–R1168 一致）

## finish_reason

- tool_calls: 74 (83%)
- stop: 15 (17%)

正常（工具调用为主，agent 使用模式稳定）。

## 趋势

- **6h: 1987 记录, 1977 success = 99.5% SR** (10 失败)
- 3h 逐小时:
  - 23:00 | 30 req | 30 ok | avg 20804ms（低流量时段）
  - 22:00 | 265 req | 262 ok | avg 14267ms
  - 21:00 | 355 req | 355 ok | avg 10325ms
  - 20:00 | 334 req | 334 ok | avg 9473ms
- 6h 逐小时 SR 全为 99–100%，avg 稳定（9.4–20.8s），**无系统劣化**。
- 24h all_tiers_exhausted: 63（历史累积，本时段实际 ATE=1，非聚集）

## 参数状态 (unchanged)

```
UPSTREAM_TIMEOUT=50
TIER_TIMEOUT_BUDGET_S=180 / NVU_TIER_BUDGET_DSV4F0731_NV=180 / NVU_TIER_BUDGET_DSV4F_NV=180
KEY_COOLDOWN_S=30
TIER_COOLDOWN_S=90
NVU_PEXEC_TIMEOUT_FASTBREAK=3 / NVU_EMPTY_200_FASTBREAK=3
NVU_BUFFER_TIMEOUT_STAIRS=90×5
NVU_PEER_FALLBACK_ENABLED=0
NVU_KEYMGR_429_BASE/MAX_COOLDOWN=120/120
NVU_KEYMGR_CONN_BASE_COOLDOWN=30 / FAIL_THRESHOLD=3 / MAX=60 / LONG=120
PROXY_TIMEOUT=300 / PROXY_ROLE=passthrough
```

live env 已核实与 R1168 完全一致，无漂移。无 integrate keys（全走 nvcf_pexec）。本窗口 429=0，无调 budget/cooling 的数据需求。

## 上次修改效果 (R1168 → R1169)

R1168 SR=**97.1%** (100/103)。本轮 SR=**96.7%** (89/92)，持平。3 个错误类型与前两轮完全一致（all_tiers_exhausted / buffer_exhausted / stream_no_content_gap 各 1），且同样分散于 3 个不同 key —— 确认这三类单点瞬态错误是 **dsv4f0731 链路的常态底层噪声**（每类 ~1/100 量级），非系统退化。Avg 22884ms 略高于常态（由 138s 的 stream gap + 80s buffer 两个慢错误拉高），6h 逐小时 avg 9.4–20.8s 反映真实常态。**无参数失效，属抽样噪声。**

## 结论

SR=96.7% > 95% NOP 阈值；0 429、0 fallback；3 个错误为 3 种不同类型、分散于 3 个独立 key 的**单点瞬态**（各自命中率 ~1%，且连续三轮错误类型/分布模式一致，确认为链路常态噪声而非新问题）；6h SR=99.5% 表明整体链路稳定；逐小时 p95 未持续超阈值。所有 NOP 判定标准满足。**不改任何参数。**（"改前必有数据"铁律 — 单点噪声不足以支撑任何调参。）

## 下一步建议

- 保持观察。单点瞬态错误（ate/buffer/gap）已连续三轮以相同且独立分布出现，如持续不聚集，下轮仍 NOP。
- 预置对策（仅当信号出现才动作）:
  - **若 30min 再出现 ≥3 个 all_tiers_exhausted 且单 key 聚集** → 提示 budget 分配/出口 IP 问题，检查该 key 代理质量，而非直接改参数。
  - 429 回升（≥5/30min） → `KEY_COOLDOWN_S` 30→60s（当前 429=0，无此需求）。
  - stream_no_content_gap / buffer_exhausted 聚集（≥2/30min 同种，或连续多轮同 key） → buffer 死链信号，考虑 `NVU_BUFFER_TIMEOUT_STAIRS` 90→75 或检查 NVU_BUFFER_CALLERS 链路。
  - NVStream_IncompleteRead 聚集（≥30/h） → 检查对应 key 的 SOCKS5 端口与 UPSTREAM_TIMEOUT。
- 关注 30min p95 是否为小样本误导（常态 p95 应 ≤43s，94.6s 为缓慢错误拉高，与 R1167/R1168 同因）。