# R1174: dsv4f0731_nv40666 NOP — 30min 全绿 (SR=100%, 0错误, 0 fallback, 0 429)

日期: 2026-08-08 07:32 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF 链路)

## 决策：NOP（不改任何参数）

## 30min 窗口数据

| 指标 | 值 |
|---|---|
| SR | **100%** (148/148) |
| 错误 / Fallback | **0 / 0** |
| Avg / P50 / P95 / P99 | 13499 / 9953 / 34810 / 57726 ms |
| 429 | 0 |
| upstream_type | nvcf_pexec 148/148 (100%) — 全 pexec，无 integrate |
| finish_reason | tool_calls 129, stop 19 |

**Per-key 200 延迟**（全 5 key 无错误，健康）:
```
key0|25req|mean10936
key1|32req|mean15832
key2|30req|mean11937
key3|29req|mean13420
key4|32req|mean14702
```
5 key 负载较均匀 (25-32 req/key)、延迟同量级 (10.9-15.8s avg)，无劣化 key。per-key 错误为空表——30min 内 **0 错误**。

**tier_attempts**: 空（全直接成功，无 key 间切换）。
**key_cycle_429s**: 0|52, 1|96 — 累计计数（容器 lifetime 值，对比 R1173 的 49/88 基本无变化），非本窗口信号。同时 30min 429=0、错误表空、tier_attempts 空，三证一致排除窗口内 429/循环压力。

## 趋势

- **6h**: 2013/2003 → **SR=99.5%**，10 失败，0 fallback
- **3h 逐小时**: 20:00 185(100%), 21:00 355(100%), 22:00 265/268(99%), 23:00 161(100%) — 高流量且逐小时 SR 全 ≥99%
- **24h all_tiers_exhausted**: 55（~2.3/h，均被 fallback 兜住，非本 30min 窗口信号）

## 关键判断

- 30min SR=100%、0 错误、0 fallback、0 429 —— **连续第五轮全绿**（R1170、R1171、R1172、R1173、R1174 均 100%，窗口请求量 134-148 与延迟高度稳定）。
- all pexec、无 key 劣化、无 key 间切换，per-key 分布均匀，avg 10.9-15.8s 稳定。
- 6h SR=99.5% + 逐小时高流量（最高 355/h）稳定 SR ≥99% → 整体链路完全健康稳态，无任何退化信号。

**无任何调参依据。** 守"改前必有数据"铁律——健康窗口不动作，避免为调而调。

## 上次修改效果 (R1173 → R1174)

R1173 SR=100% (137/137)。本轮 SR=**100%** (148/148)，0 错误，连续全绿再次验证 NOP 判断正确。Avg 14712→13499ms、P50 11236→9953ms、P95 40608→34810ms 均下降（更优），延迟稳定。**无需要修的参数。** R1173 预置的应对策略均未触发（429=0、ATE=0、无 stream/buffer 错误、无 IncompleteRead）。

## 下一步建议

- 保持观察。连续五轮全绿强 NOP 信号，下轮若仍无 429 回升 / 错误聚集，继续 NOP。
- 预置对策（仅当信号出现才动作，沿用之前设定）:
  - **429 回升 ≥5/30min** → `KEY_COOLDOWN_S` 30→60s。
  - **all_tiers_exhausted ≥3/30min 且单 key 聚集** → 检查该 key 出口 IP / 代理质量，非直接改参。
  - **stream_no_content_gap / buffer_exhausted 聚集**（≥2/30min 同种） → `NVU_BUFFER_TIMEOUT_STAIRS` 90→75 或检查 NVU_BUFFER_CALLERS 链路。
  - **NVStream_IncompleteRead 聚集 ≥30/h** → 查对应 key SOCKS5 端口与 UPSTREAM_TIMEOUT(50)。
- 全 pexec 架构已连续多轮 SR≈100%，确认当前为最优，无需切换 integrate。