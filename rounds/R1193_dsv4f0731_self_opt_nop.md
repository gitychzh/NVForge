# R1193: dsv4f0731_nv40666 NOP — 30min SR=97.3%, 仅 2 孤立 IncompleteRead (0 429, 0 fallback)

日期: 2026-08-08 13:26 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF 链路)

## 决策：NOP（不改任何参数）

SR=97.3% (>95% 阈值)、0 429、0 fallback、per-key 均衡无劣化 key、6h SR=99.3%。2 个错误均为**单次孤立事件**（各 count=1，分布在 key1/key2 不同 key），无 fast-break 聚集（NKU_PEXEC_TIMEOUT_FASTBREAK=3、NVU_EMPTY_200_FASTBREAK=3 均未触及），被 key 循环正常兜住——不足为调参凭据。守"改前必有数据"铁律，健康窗口不动作。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **97.3%** (73/75, 2 error) |
| 错误 / Fallback | 2 / 0 |
| Avg / P50 / P95 / Max | 24958 / 14786 / 92095 / 124522 ms |
| 429 | 0 |
| upstream_type | nvcf_pexec 75/75 (100%) — 全 pexec，无 integrate |
| finish_reason | tool_calls 59, stop 14 |

**错误分类**（各 1 次，孤立无聚集）:
```
NVStream_IncompleteRead|2   (key1 avg35655ms, key2 avg66546ms)
```

**Per-key 200 延迟**（全 5 key 负载均匀 10-17 req，延迟同量级 14.0-36.5s，k2 略高但仅 1 孤立错误）:
```
key0|17req|avg19906
key1|12req|avg29293
key2|17req|avg36475
key3|17req|avg18782
key4|10req|avg14037
```

**Per-key 错误**: key1 NVStream_IncompleteRead×1, key2 NVStream_IncompleteRead×1 — 无 key 劣化（各 key 单事件，不构成 fast-break 触发）。

**tier_attempts**: 空（30min 内无 key 切换失败）。
**key_cycle_429s**: 0|26, 1|49 — 30min 429=0，验明无 429/循环压力。

## 趋势

- **6h**: 1347/1337 → **SR=99.3%**，10 失败, 0 fallback
- **3h 逐小时**: 05:00 74(97.3%,2err), 04:00 145(97.9%,3err), 03:00 168(98.2%,3err), 02:00 124(99.2%,1err) — 高流量下 SR 稳定 ≥97.3%
- **24h all_tiers_exhausted**: 27（较 R1192 的 29 **下降 6.9%**，均被 fallback 兜住，非本 30min 窗口信号）

## 关键判断

- 30min SR=97.3%，2 个错误均为**孤立单事件**（NVStream_IncompleteRead 各 1 次），分布在 key1/key2 不同 key，无 fast-break 聚集（阈值均未触及）。按预置对策"同种 ≥3/30min 才动作"，单事件被 key 循环兜住，**不足为凭**。
- 429=0、0 fallback、per-key 负载均匀 (10-17/key)、延迟同量级 (14.0-36.5s)——无劣化 key、无 integrate、全 pexec。
- 6h SR=99.3% + 高流量时段（最高 168/h）逐小时 SR ≥97.3% → 整体链路健康稳态，P50 14.8s 在 pexec 正常量级。
- 24h all_tiers_exhausted 27 较上轮 29 **下降 6.9%**，链路进一步趋稳。

**无任何调参依据。** 守"改前必有数据"铁律——健康窗口不动作，避免为调而调。

## 上次修改效果 (R1192 → R1193)

R1192 SR=97.8% (91/93)、2 孤立单事件错误。本轮 SR=97.3% (73/75)、2 孤立 IncompleteRead，为正常噪声（窗口请求量 93→75 下降放大稀疏尾部）。延迟 P50 14.6s→14.8s，各 key 均在 pexec 正常量级。429=0、0 fallback、R1192-R1193 均无参数变更。6h SR 99.4%→99.3%，仍健康。**无需要修的参数。**

## 下一步建议

- 保持观察。本轮 2 孤立单事件不足为调参依据，下轮若错误聚集（同种 ≥3/30min）或 429 回升再动作。
- 预置对策（仅当信号出现才动作，沿用之前设定）:
  - **429 回升 ≥5/30min** → `KEY_COOLDOWN_S` 30→60s。
  - **NVCF 错误聚集**（同种 ≥3/30min） → 排查上游出口而非盲目调超时（单次事件已被 key 循环兜住，不足为凭）。
  - **NVStream_IncompleteRead 持续 2+ 轮聚集** → 检查对应 key 出口 IP / 代理质量，非直接改参。
- 容器 /health OK、全 5 key 正常、no integrate 激活 — 保持现有配置不变。