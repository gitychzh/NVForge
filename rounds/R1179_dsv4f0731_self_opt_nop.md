# R1179: dsv4f0731_nv40666 NOP — 30min 全绿 (SR=100%, 0错误, 0 fallback, 0 429)

日期: 2026-08-08 08:00 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF 链路)

## 决策：NOP（不改任何参数）

## 30min 窗口数据

| 指标 | 值 |
|---|---|
| SR | **100%** (171/171) |
| 错误 / Fallback | **0 / 0** |
| Avg | 10965 ms |
| 429 | 0 |
| upstream_type | nvcf_pexec 171/171 (100%) — 全 pexec，无 integrate |
| finish_reason | tool_calls 146, stop 25 |

**Per-key 200 延迟**（全 5 key 无错误，健康）:
```
key0|33req|mean12029|p95 24224
key1|34req|mean10895|p95 25045
key2|34req|mean9905|p95 22551
key3|35req|mean12446|p95 29511
key4|35req|mean9578|p95 31978
```
5 key 负载均匀 (33-35 req/key)、延迟同量级 (9.6-12.4s avg)，无劣化 key，p95 26-32s 同量级。per-key 错误为空表——30min 内 **0 错误**。

**tier_attempts**: 空表——30min 内无 key 间切换、无任何瞬时故障。

**key_cycle_429s**: 0|68, 1|103 — 累计计数（与 R1178 完全一致 0|68,1|103，无新增）。30min 429=0、错误表空、tier_attempts 空，多证一致排除窗口内 429/循环压力。

## 趋势

- **6h**: 2028/2022 → **SR=99.7%**，6 失败，0 fallback
- **3h 逐小时**: 23:00 306(100%), 22:00 262/265(98.9%), 21:00 355(100%), 20:00 7(100%) — 高流量且逐小时 SR 全 ≥98.9%
- **24h all_tiers_exhausted**: 52（~2.2/h，均被 fallback 兜住，非本 30min 窗口信号）

## 关键判断

- 30min SR=100%、0 错误、0 fallback、0 429 —— **连续第十轮全绿**（R1170~R1179 均 100%，窗口请求量 101-306、延迟 avg 稳定在 10-11s 带）。
- all pexec、无 key 劣化、tier_attempts 完全为空（无 key 间切换），per-key 分布均匀，avg 9.6-12.4s 稳定。
- 6h SR=99.7% + 逐小时高流量（最高 355/h）稳定 SR ≥98.9% → 整体链路完全健康稳态，无任何退化信号。

**无任何调参依据。** 守"改前必有数据"铁律——健康窗口不动作，避免为调而调。

## 上次修改效果 (R1178 → R1179)

R1178 SR=100% (173/173)。本轮 SR=**100%** (171/171)，0 错误，连续全绿再次验证 NOP 判断正确。Avg 10983→10965ms（持平）、per-key 延迟带 9.4-13.5s → 9.6-12.4s（同量级稳定）。tier_attempts 连续三轮为空表（0 瞬时错误），链路干净；key_cycle_429s 与 R1178 完全一致 0|68,1|103（无新增循环），更证窗口零压力。**无需要修的参数。** R1178 预置的应对策略均未触发（429=0、ATE 无窗口内增长、无 stream/buffer 错误聚集、无 IncompleteRead）。

## 下一步建议

- 保持观察。连续十轮全绿强 NOP 信号，下轮若仍无 429 回升 / 错误聚集，继续 NOP。
- 预置对策（仅当信号出现才动作，沿用之前设定）:
  - **429 回升 ≥5/30min** → `KEY_COOLDOWN_S` 30→60s。
  - **all_tiers_exhausted ≥3/30min 且单 key 聚集** → 检查该 key 出口 IP / 代理质量，非直接改参。
  - **stream_no_content_gap / buffer_exhausted 聚集**（≥2/30min 同种） → `NVU_BUFFER_TIMEOUT_STAIRS` 90→75 或检查 NVU_BUFFER_CALLERS 链路。
  - **NVStream_IncompleteRead 聚集 ≥30/h** → 查对应 key SOCKS5 端口与 UPSTREAM_TIMEOUT(50)。
- 本轮 30min tier_attempts 空表（0 瞬时错误），无任何 upstream 调整依据。
- 全 pexec 架构已连续多轮 SR≈100%，确认当前为最优，无需切换 integrate。