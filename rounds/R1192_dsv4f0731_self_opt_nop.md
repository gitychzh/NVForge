# R1192: dsv4f0731_nv40666 NOP — 30min SR=97.8%, 仅 2 孤立单事件错误 (0 429, 0 fallback)

日期: 2026-08-08 12:14 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF 链路)

## 决策：NOP（不改任何参数）

SR=97.8% (>95% 阈值)、0 429、0 fallback、per-key 均衡无劣化 key、6h SR=99.4%。2 个错误均为**单次孤立事件**（各 count=1）、无 fast-break 聚集，被 key 循环正常兜住——不足为调参凭据。守"改前必有数据"铁律，健康窗口不动作。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **97.8%** (91/93, 2 error) |
| 错误 / Fallback | 2 / 0 |
| Avg / P50 / P95 / Max | 21716 / 14576 / 65271 / 99147 ms |
| 429 | 0 |
| upstream_type | nvcf_pexec 93/93 (100%) — 全 pexec，无 integrate |
| finish_reason | tool_calls 75, stop 16 |

**错误分类**（各 1 次，孤立无聚集）:
```
NVStream_IncompleteRead|1   (key1, avg35318ms)
zombie_empty_completion|1   (key3, avg44067ms)
```

**Per-key 200 延迟**（全 5 key 负载均匀 15-23 req，延迟同量级 15.7-23.2s）:
```
key0|23req|avg27704|P9593570
key1|16req|avg17818|P9537851
key2|19req|avg15718|P9551445
key3|15req|avg20060|P9548492
key4|18req|avg23245|P9562076
```

**Per-key 错误**: key1 NVStream_IncompleteRead×1, key3 zombie_empty_completion×1 — 无 key 劣化（各 key 单事件，不构成 fast-break 触发）。

**tier_attempts**: 空（30min 内无 key 切换失败）。
**key_cycle_429s**: 0|22, 1|71 — 30min 429=0，验明无 429/循环压力。

## 趋势

- **6h**: 1478/1469 → **SR=99.4%**，9 失败, 0 fallback
- **3h 逐小时**: 04:00 44(97.7%,1err), 03:00 168(98.2%,3err), 02:00 225(99.6%,1err), 01:00 180(99.4%,1err) — 高流量下 SR 稳定 ≥97.7%
- **24h all_tiers_exhausted**: 29（~1.2/h，较 R1191 的 40 下降，均被 fallback 兜住，非本 30min 窗口信号）

## 关键判断

- 30min SR=97.8%（较上轮 100% 降 2.2pp），2 个错误均为**孤立单事件**（NVStream_IncompleteRead、zombie_empty_completion 各 1 次），分布在 key1/key3 不同 key，无 fast-break 聚集（阈值 NVU_EMPTY_200_FASTBREAK=3、NVU_PEXEC_TIMEOUT_FASTBREAK=3 均未触及）。按 R1191 预置对策"同种 ≥3/30min 才动作"，单事件被 key 循环兜住，**不足为凭**。
- 429=0、0 fallback、per-key 负载均匀 (15-23/key)、延迟同量级 (15.7-23.2s)——无劣化 key、无 integrate、全 pexec。
- 6h SR=99.4% + 高流量时段（最高 225/h）逐小时 SR ≥97.7% → 整体链路健康稳态，P50 14.6s 略升但无错误聚集佐证为正常稀疏尾部带。
- 24h all_tiers_exhausted 29 较上轮 40 **下降 27.5%**，链路进一步趋稳。

**无任何调参依据。** 守"改前必有数据"铁律——健康窗口不动作，避免为调而调。

## 上次修改效果 (R1191 → R1192)

R1191 SR=100% (109/109)、0 错误。本轮 SR=97.8% (91/93)、2 孤立单事件错误，为正常噪声（窗口请求量 109→93 下降放大稀疏尾部）。延迟 P50 12.2s→14.6s，各 key 均在 pexec 正常量级。429=0、0 fallback、R1191-R1192 均无参数变更。6h SR 99.84%→99.4%，仍健康。**无需要修的参数。**

## 下一步建议

- 保持观察。本轮 2 孤立单事件不足为调参依据，下轮若错误聚集（同种 ≥3/30min）或 429 回升再动作。
- 预置对策（仅当信号出现才动作，沿用之前设定）:
  - **429 回升 ≥5/30min** → `KEY_COOLDOWN_S` 30→60s。
  - **NVCF 错误聚集**（同种 ≥3/30min） → 排查上游出口而非盲目调超时（单次事件已被 key 循环兜住，不足为凭）。
  - **zombie_empty_completion / NVStream_IncompleteRead 持续 2+ 轮聚集** → 检查对应 key 出口 IP / 代理质量，非直接改参。
- 容器 /health OK、全 5 key 正常、no integrate 激活 — 保持现有配置不变。