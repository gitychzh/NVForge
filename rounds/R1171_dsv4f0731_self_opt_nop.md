# R1171: dsv4f0731_nv40666 NOP — 30min 全绿 (SR=100%, 0错误, 0 fallback, 0 429)

日期: 2026-08-08 07:22 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF 链路)

## 决策：NOP（不改任何参数）

## 30min 窗口数据

| 指标 | 值 |
|---|---|
| SR | **100%** (134/134) |
| 错误 / Fallback | **0 / 0** |
| Avg / P50 / P95 | 15853 / 12224 / 45913 ms |
| 429 | 0 |
| upstream_type | nvcf_pexec 134/134 (100%) — 全 pexec，无 integrate |
| finish_reason | tool_calls 115, stop 19 |

**Per-key 200 延迟**（全 5 key 无错误，健康）:
```
key0|24req|avg16339|p9543683
key1|27req|avg19635|p9550667
key2|27req|avg15533|p9548188
key3|27req|avg10706|p9522694
key4|29req|avg17019|p9537370
```
key3 持平最慢档（avg 10706 最快），5 key 分布均匀，无劣化 key。per-key 错误为空表——30min 内 **0 错误**。

**tier_attempts**: 空（全直接成功，无 key 间切换）。
**key_cycle_429s**: 0|48, 1|86 — 累计计数（容器 Up 5h 的 lifetime 值），非本窗口信号。30min 实际 429=0、错误表空、tier_attempts 空，三证一致排除窗口内 429 压力。

## 趋势

- **6h**: 1995/1985 → **SR=99.5%**，10 失败，0 fallback
- **3h 逐小时**: 20:00 244(100%), 21:00 355(100%), 22:00 262/265(98.9%), 23:00 98(100%) — 高流量（每小时 98-355）且逐小时 SR 全 ≥98.9%
- **24h all_tiers_exhausted**: 59（~2.5/h，均被 fallback 兜住，非本 30min 窗口信号）

## 关键判断

- 30min SR=100%、0 错误、0 fallback、0 429 —— 连续第二轮全绿（R1170 与 R1171 均 100%）。
- all pexec、无 key 劣化、无 key 间切换，per-key 分布均匀。
- 6h SR=99.5% + 逐小时高流量（最高 355/h）稳定 SR ≥98.9% → 整体链路稳中向好，无任何退化信号。

**无任何调参依据。** 守"改前必有数据"铁律——健康窗口不动作，避免为调而调。

## 上次修改效果 (R1170 → R1171)

R1170 SR=100% (123/123)。本轮 SR=**100%** (134/134)，0 错误，连续全绿验证上轮 NOP 判断正确。Avg 16221→15853ms 基本持平，延迟稳定。**无参数失效。**

## 下一步建议

- 保持观察。连续全绿强 NOP 信号，下轮若无 429 回升 / 错误聚集，继续 NOP。
- 预置对策（仅当信号出现才动作）:
  - **429 回升 ≥5/30min** → `KEY_COOLDOWN_S` 30→60s。
  - **all_tiers_exhausted ≥3/30min 且单 key 聚集** → 检查该 key 出口 IP / 代理质量，非直接改参。
  - **stream_no_content_gap / buffer_exhausted 聚集**（≥2/30min 同种） → `NVU_BUFFER_TIMEOUT_STAIRS` 90→75 或检查 NVU_BUFFER_CALLERS 链路。
  - **NVStream_IncompleteRead 聚集 ≥30/h** → 查对应 key SOCKS5 端口与 UPSTREAM_TIMEOUT(50)。
- 若 integrate 长期 0 使用且 pexec 稳定（已连续多轮全 pexec SR≈100%），可确认全 pexec 架构为当前最优，无切换 integrate 必要。
