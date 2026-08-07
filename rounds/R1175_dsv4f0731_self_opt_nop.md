# R1175: dsv4f0731_nv40666 NOP — 30min 全绿 (SR=100%, 0错误, 0 fallback, 0 429)

日期: 2026-08-08 07:34 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF 链路)

## 决策：NOP（不改任何参数）

## 30min 窗口数据

| 指标 | 值 |
|---|---|
| SR | **100%** (159/159) |
| 错误 / Fallback | **0 / 0** |
| Avg / P50 / P95 / P99 | 13305 / 9923 / 36192 / 57409 ms |
| 429 | 0 |
| upstream_type | nvcf_pexec 159/159 (100%) — 全 pexec，无 integrate |
| finish_reason | tool_calls 141, stop 18 |

**Per-key 200 延迟**（全 5 key 无错误，健康）:
```
key0|28req|mean10956
key1|34req|mean16219
key2|34req|mean12205
key3|30req|mean12495
key4|33req|mean14167
```
5 key 负载较均匀 (28-34 req/key)、延迟同量级 (10.9-16.2s avg)，无劣化 key。per-key 错误为空表——30min 内 **0 错误**。

**tier_attempts**: 空（全直接成功，无 key 间切换）。
**key_cycle_429s**: 0|57, 1|102 — 累计计数（容器 lifetime 值，对比 R1174 的 52/96 基本无变化），非本窗口信号。同时 30min 429=0、错误表空、tier_attempts 空，三证一致排除窗口内 429/循环压力。

## 趋势

- **6h**: 2007/1997 → **SR=99.5%**，10 失败，0 fallback
- **3h 逐小时**: 23:00 175(100%), 22:00 265/268(98.9%), 21:00 355(100%), 20:00 168(100%) — 高流量且逐小时 SR 全 ≥99%
- **24h all_tiers_exhausted**: 55（~2.3/h，均被 fallback 兜住，非本 30min 窗口信号）

## 关键判断

- 30min SR=100%、0 错误、0 fallback、0 429 —— **连续第六轮全绿**（R1170、R1171、R1172、R1173、R1174、R1175 均 100%，窗口请求量 134-159 与延迟高度稳定）。
- all pexec、无 key 劣化、无 key 间切换，per-key 分布均匀，avg 10.9-16.2s 稳定。
- 6h SR=99.5% + 逐小时高流量（最高 355/h）稳定 SR ≥99% → 整体链路完全健康稳态，无任何退化信号。

**无任何调参依据。** 守"改前必有数据"铁律——健康窗口不动作，避免为调而调。

## 上次修改效果 (R1174 → R1175)

R1174 SR=100% (148/148)。本轮 SR=**100%** (159/159)，0 错误，连续全绿再次验证 NOP 判断正确。Avg 13499→13305ms、P50 9953→9923ms、P95 34810→36192ms（P95 微升 4%，仍在稳态区间）。**无需要修的参数。** R1174 预置的应对策略均未触发（429=0、ATE=0、无 stream/buffer 错误、无 IncompleteRead）。

## 下一步建议

- 保持观察。连续六轮全绿强 NOP 信号，下轮若仍无 429 回升 / 错误聚集，继续 NOP。
- 预置对策（仅当信号出现才动作，沿用之前设定）:
  - **429 回升 ≥5/30min** → `KEY_COOLDOWN_S` 30→60s。
  - **all_tiers_exhausted ≥3/30min 且单 key 聚集** → 检查该 key 出口 IP / 代理质量，非直接改参。
  - **stream_no_content_gap / buffer_exhausted 聚集**（≥2/30min 同种） → `NVU_BUFFER_TIMEOUT_STAIRS` 90→75 或检查 NVU_BUFFER_CALLERS 链路。
  - **NVStream_IncompleteRead 聚集 ≥30/h** → 查对应 key SOCKS5 端口与 UPSTREAM_TIMEOUT(50)。
- **P95 微升观察项**（本轮 36192 vs 上轮 34810，+4%）: 若未来连续多轮 P95 持续走高且伴随错误出现，才考虑 UPSTREAM_TIMEOUT/TIER_TIMEOUT_BUDGET 微调；单轮波动不动作。
- 全 pexec 架构已连续多轮 SR≈100%，确认当前为最优，无需切换 integrate。