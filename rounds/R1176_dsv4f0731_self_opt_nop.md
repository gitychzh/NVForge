# R1176: dsv4f0731_nv40666 NOP — 30min 全绿 (SR=100%, 0错误, 0 fallback, 0 429)

日期: 2026-08-08 07:40 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF 链路)

## 决策：NOP（不改任何参数）

## 30min 窗口数据

| 指标 | 值 |
|---|---|
| SR | **100%** (174/174) |
| 错误 / Fallback | **0 / 0** |
| Avg / P50 / P95 | 11932 / 9388 / 29542 ms (P95 百分位最高 43795) |
| 429 | 0 |
| upstream_type | nvcf_pexec 174/174 (100%) — 全 pexec，无 integrate |
| finish_reason | tool_calls 153, stop 21 |

**Per-key 200 延迟**（全 5 key 无错误，健康）:
```
key0|33req|mean11017
key1|36req|mean13928
key2|36req|mean11029
key3|34req|mean11358
key4|35req|mean12229
```
5 key 负载均匀 (33-36 req/key)、延迟同量级 (11.0-13.9s avg)，无劣化 key。per-key 错误为空表——30min 内 **0 错误**。

**tier_attempts**: 仅 2 条瞬时故障且均已被 key 循环恢复为 200：
- key0: 1× NVCFPexecTimeout (51421ms, 慢但最终成功)
- key3: 1× NVCFPexecRemoteDisconnected (31663ms)
非聚集信号，无调参依据。

**key_cycle_429s**: 0|66, 1|108 — 累计计数（容器 lifetime 值，对比 R1175 的 0|57,1|102 仅小幅自然滚动），非本窗口信号。30min 429=0、错误表空、tier_attempts 仅 2 瞬时错误，多证一致排除窗口内 429/循环压力。

## 趋势

- **6h**: 2006/1996 → **SR=99.5%**，10 失败，0 fallback
- **3h 逐小时**: 23:00 205(100%), 22:00 265/268(98.9%), 21:00 355(100%), 20:00 125(100%) — 高流量且逐小时 SR 全 ≥98.9%
- **24h all_tiers_exhausted**: 54（~2.3/h，均被 fallback 兜住，非本 30min 窗口信号）

## 关键判断

- 30min SR=100%、0 错误、0 fallback、0 429 —— **连续第七轮全绿**（R1170~R1176 均 100%，窗口请求量 134-174 与延迟高度稳定）。
- all pexec、无 key 劣化、无 key 间切换（tier_attempts 仅 2 瞬时错误），per-key 分布均匀，avg 11.0-13.9s 稳定。
- 6h SR=99.5% + 逐小时高流量（最高 355/h）稳定 SR ≥98.9% → 整体链路完全健康稳态，无任何退化信号。

**无任何调参依据。** 守"改前必有数据"铁律——健康窗口不动作，避免为调而调。

## 上次修改效果 (R1175 → R1176)

R1175 SR=100% (159/159)。本轮 SR=**100%** (174/174)，0 错误，连续全绿再次验证 NOP 判断正确。Avg 13305→11932ms、P50 9923→9388ms、P95 36192→29542ms（P95 回落到近日低位，前轮 R1175 提出的"P95 微升观察项"未延续，本轮无走高信号）。**无需要修的参数。** R1175 预置的应对策略均未触发（429=0、ATE 无窗口内增长、无 stream/buffer 错误聚集、无 IncompleteRead）。

## 下一步建议

- 保持观察。连续七轮全绿强 NOP 信号，下轮若仍无 429 回升 / 错误聚集，继续 NOP。
- 预置对策（仅当信号出现才动作，沿用之前设定）:
  - **429 回升 ≥5/30min** → `KEY_COOLDOWN_S` 30→60s。
  - **all_tiers_exhausted ≥3/30min 且单 key 聚集** → 检查该 key 出口 IP / 代理质量，非直接改参。
  - **stream_no_content_gap / buffer_exhausted 聚集**（≥2/30min 同种） → `NVU_BUFFER_TIMEOUT_STAIRS` 90→75 或检查 NVU_BUFFER_CALLERS 链路。
  - **NVStream_IncompleteRead 聚集 ≥30/h** → 查对应 key SOCKS5 端口与 UPSTREAM_TIMEOUT(50)。
- 本轮 30min 仅 2 条瞬时 NVCF 错误（timeout/disconnected 各 1），均恢复为 200，无聚集否则不动 UPSTREAM_TIMEOUT。
- 全 pexec 架构已连续多轮 SR≈100%，确认当前为最优，无需切换 integrate。