# R1177: dsv4f0731_nv40666 NOP — 30min 全绿 (SR=100%, 0错误, 0 fallback, 0 429)

日期: 2026-08-08 07:44 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF 链路)

## 决策：NOP（不改任何参数）

## 30min 窗口数据

| 指标 | 值 |
|---|---|
| SR | **100%** (182/182) |
| 错误 / Fallback | **0 / 0** |
| Avg / P50 / P95 | 11075 / 8880 / 25784 ms (P95 百分位最高 39952) |
| 429 | 0 |
| upstream_type | nvcf_pexec 182/182 (100%) — 全 pexec，无 integrate |
| finish_reason | tool_calls 159, stop 23 |

**Per-key 200 延迟**（全 5 key 无错误，健康）:
```
key0|35req|mean10385
key1|36req|mean12423
key2|38req|mean10179
key3|36req|mean10872
key4|37req|mean11536
```
5 key 负载均匀 (35-38 req/key)、延迟同量级 (10.2-12.4s avg)，无劣化 key。per-key 错误为空表——30min 内 **0 错误**。

**tier_attempts**: 空表——30min 内无 key 间切换、无任何瞬时故障，比上轮（仅 2 条瞬时错误）更干净。

**key_cycle_429s**: 0|70, 1|112 — 累计计数（容器 lifetime 值，对比 R1176 的 0|66,1|108 仅自然滚动 +4/+4），非本窗口信号。30min 429=0、错误表空、tier_attempts 空，多证一致排除窗口内 429/循环压力。

## 趋势

- **6h**: 2014/2004 → **SR=99.5%**，10 失败，0 fallback
- **3h 逐小时**: 23:00 232(100%), 22:00 265/268(98.9%), 21:00 355(100%), 20:00 101(100%) — 高流量且逐小时 SR 全 ≥98.9%
- **24h all_tiers_exhausted**: 54（~2.3/h，均被 fallback 兜住，非本 30min 窗口信号）

## 关键判断

- 30min SR=100%、0 错误、0 fallback、0 429 —— **连续第八轮全绿**（R1170~R1177 均 100%，窗口请求量 101-182、延迟 P50 8.9-9.9s 高度稳定）。
- all pexec、无 key 劣化、tier_attempts 完全为空（无 key 间切换），per-key 分布均匀，avg 10.2-12.4s 稳定。
- 6h SR=99.5% + 逐小时高流量（最高 355/h）稳定 SR ≥98.9% → 整体链路完全健康稳态，无任何退化信号。

**无任何调参依据。** 守"改前必有数据"铁律——健康窗口不动作，避免为调而调。

## 上次修改效果 (R1176 → R1177)

R1176 SR=100% (174/174)。本轮 SR=**100%** (182/182)，0 错误，连续全绿再次验证 NOP 判断正确。Avg 11932→11075ms（微降）、P50 9388→8880ms、P95 29542→25784ms（均回落至低位区间）。tier_attempts 从上轮 2 条瞬时错误 → 本轮空表（0 错误），链路更干净。**无需要修的参数。** R1176 预置的应对策略均未触发（429=0、ATE 无窗口内增长、无 stream/buffer 错误聚集、无 IncompleteRead）。

## 下一步建议

- 保持观察。连续八轮全绿强 NOP 信号，下轮若仍无 429 回升 / 错误聚集，继续 NOP。
- 预置对策（仅当信号出现才动作，沿用之前设定）:
  - **429 回升 ≥5/30min** → `KEY_COOLDOWN_S` 30→60s。
  - **all_tiers_exhausted ≥3/30min 且单 key 聚集** → 检查该 key 出口 IP / 代理质量，非直接改参。
  - **stream_no_content_gap / buffer_exhausted 聚集**（≥2/30min 同种） → `NVU_BUFFER_TIMEOUT_STAIRS` 90→75 或检查 NVU_BUFFER_CALLERS 链路。
  - **NVStream_IncompleteRead 聚集 ≥30/h** → 查对应 key SOCKS5 端口与 UPSTREAM_TIMEOUT(50)。
- 本轮 30min tier_attempts 空表（0 瞬时错误），较上轮更干净，无任何 upstream 调整依据。
- 全 pexec 架构已连续多轮 SR≈100%，确认当前为最优，无需切换 integrate。