# R1181: dsv4f0731_nv40666 NOP — 30min 全绿 (SR=100%, 0错误, 0 fallback, 0 429)

日期: 2026-08-08 08:06 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF 链路)

## 决策：NOP（不改任何参数）

连续第十二轮全绿（R1170~R1181 均 SR=100%），健康稳态，守"改前必有数据"铁律不动作。

## 30min 窗口数据

| 指标 | 值 |
|---|---|
| SR | **100%** (165/165) |
| 错误 / Fallback | **0 / 0** |
| Avg / P50 / P95 / Max | 10928 / 8697 / 25913 / 52513 ms |
| 429 | 0 |
| upstream_type | nvcf_pexec 165/165 (100%) — 全 pexec，无 integrate |
| finish_reason | tool_calls 140, stop 25 |

**Per-key 200 延迟**（全 5 key 无错误，健康）:
```
key0|33req|mean10951|p95 24306
key1|34req|mean10288|p95 21023
key2|32req|mean10099|p95 20744
key3|32req|mean11568|p95 29765
key4|34req|mean11725|p95 32147
```
5 key 负载均匀 (32-34 req/key)、延迟同量级 (10.1-11.7s avg)，无劣化 key。per-key 错误为空表——30min 内 **0 错误**。

**tier_attempts**: 空表——30min 内无 key 间切换、无任何瞬时故障。

**key_cycle_429s**: 0|68, 1|97 — 与 R1180 (0|68, 1|97) 完全一致，无新增循环。30min 429=0、错误表空、tier_attempts 空，多证一致排除窗口内 429/循环压力。

## 趋势

- **6h**: 2048/2053 → **SR=99.76%**，5 失败，0 fallback
- **3h 逐小时**: 00:00 36(100%), 23:00 316(100%), 22:00 262/265(98.9%), 21:00 314(100%) — 高流量且逐小时 SR 全 ≥98.9%
- **24h all_tiers_exhausted**: 50（~2.1/h，均被 fallback 兜住，非本 30min 窗口信号）

## 关键判断

- 30min SR=100%、0 错误、0 fallback、0 429 —— **连续第十二轮全绿**（R1170~R1181 均 100%，窗口请求量 101-306、延迟 avg 稳定在 10-11.5s 带）。
- 全部 pexec、无 key 劣化、tier_attempts 完全为空（无 key 间切换），per-key 分布均匀，avg 10.1-11.7s 稳定。
- 6h SR=99.76% + 逐小时高流量（最高 316/h）稳定 SR ≥98.9% → 整体链路完全健康稳态，无任何退化信号。
- Max=52.5s 仅源自单次冷态/慢客户端的 p95 尾部稀疏值，非系统性（SR 仍 100%）。

**无任何调参依据。** 守"改前必有数据"铁律——健康窗口不动作，避免为调而调。

## 上次修改效果 (R1180 → R1181)

R1180 SR=100% (163/163)。本轮 SR=**100%** (165/165)，0 错误，连续全绿再次验证 NOP 判断正确。Avg 11032→10928ms（基本持平，-104ms 噪声内）、per-key 延迟带 10.2-11.6s → 10.1-11.7s（同量级稳定）。tier_attempts 连续五轮为空表（0 瞬时错误），链路干净；key_cycle_429s 与 R1180 完全一致（无新增循环）。**无需要修的参数。** R1180 预置的应对策略均未触发（429=0、ATE 无窗口内增长、无 stream/buffer 错误聚集、无 IncompleteRead）。

## 下一步建议

- 保持观察。连续十二轮全绿强 NOP 信号，下轮若仍无 429 回升 / 错误聚集，继续 NOP。
- 预置对策（仅当信号出现才动作，沿用之前设定）:
  - **429 回升 ≥5/30min** → `KEY_COOLDOWN_S` 30→60s。
  - **all_tiers_exhausted ≥3/30min 且单 key 聚集** → 检查该 key 出口 IP / 代理质量，非直接改参。
  - **stream_no_content_gap / buffer_exhausted 聚集**（≥2/30min 同种） → `NVU_BUFFER_TIMEOUT_STAIRS` 90→75 或检查 NVU_BUFFER_CALLERS 链路。
  - **NVStream_IncompleteRead 聚集 ≥30/h** → 查对应 key SOCKS5 端口与 UPSTREAM_TIMEOUT(50)。
- 本轮 30min tier_attempts 空表（0 瞬时错误），无任何 upstream 调整依据。
- 全 pexec 架构已连续多轮 SR≈100%，确认当前为最优，无需切换 integrate。