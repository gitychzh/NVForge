# R1183: dsv4f0731_nv40666 NOP — 30min 全绿 (SR=100%, 0错误, 0 fallback, 0 429)

日期: 2026-08-08 08:14 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF 链路)

## 决策：NOP（不改任何参数）

连续第十四轮全绿（R1170~R1183 均 SR=100%），健康稳态，守"改前必有数据"铁律不动作。

## 30min 窗口数据（脚本注入 + 独立 DB 交叉验证）

| 指标 | 值 |
|---|---|
| SR | **100%** (脚本 156/156；独立 DB 复查 155/155，均 status=200) |
| 错误 / Fallback | **0 / 0** |
| Avg / P50 / P95（独立 DB） | 11694 / 9187 / 28116 ms (max 65748) |
| 429 | 0 |
| upstream_type | nvcf_pexec 156/156 (100%) — 全 pexec，无 integrate |
| finish_reason | tool_calls 131, stop 25 |

**Per-key 200 延迟**（独立脚本，全 5 key 无错误，健康）:
```
key0|29req|mean12221|p95 26438
key1|33req|mean11045|p95 21777
key2|29req|mean10429|p95 20431
key3|32req|mean12597|p95 29765
key4|33req|mean11667|p95 29288
```
5 key 负载均匀 (29-33 req/key)、延迟同量级 (10.4-12.6s avg)，无劣化 key。per-key 错误为空——30min 内 **0 错误**。

**tier_attempts**: 30min 内 87 次 `pexec_success` + 1 次 `NVCFPexecRemoteDisconnected`（单次，已被 key 循环兜住，最终请求仍 200，非阈值信号；NVU_PEXEC_TIMEOUT_FASTBREAK=3 需连续 3 次才触发）。requests 级 0 错误与之一致。

**key_cycle_429s**: 0|65, 1|91 — 与 R1182 (0|69, 1|97) 相比 k0 -4、k1 -6，回落为噪声波动，无异常增长。30min 429=0 验明无 429/循环压力。

## 趋势

- **6h**: 2028/2033 → **SR=99.75%**，5 失败，0 fallback
- **3h 逐小时**: 00:00 73(100%), 23:00 316(100%), 22:00 262/265(98.9%), 21:00 267(100%) — 高流量且逐小时 SR 全 ≥98.9%
- **24h all_tiers_exhausted**: 48（~2.0/h，均被 fallback 兜住，非本 30min 窗口信号，与 R1182 的 49 基本持平）

## 关键判断

- 30min SR=100%、0 错误、0 fallback、0 429 — **连续第十四轮全绿**（R1170~R1183 均 100%，窗口请求量 56-316、延迟 avg 稳定在 10.4-12.6s 带）。
- 全部 pexec、无 key 劣化、per-key 分布均匀 (29-33/key)、avg 10.4-12.6s 稳定。单次 `NVCFPexecRemoteDisconnected` 已被 key 循环兜住，不足为凭。
- 6h SR=99.75% + 逐小时高流量（最高 316/h）稳定 SR ≥98.9% → 整体链路完全健康稳态，无任何退化信号。
- P95 带 20.4-29.8s 为 NVCF pexec 正常稀疏尾部（max 65.7s 单尖峰亦为稀疏尾部），SR 仍 100%。

**无任何调参依据。** 守"改前必有数据"铁律——健康窗口不动作，避免为调而调。

## 上次修改效果 (R1182 → R1183)

R1182 SR=100% (155/155 独立 DB)。本轮 SR=**100%** (155/155)，0 错误，连续全绿再次验证 NOP 判断正确。per-key 延迟带 10.1-12.7s → 10.4-12.6s（同量级稳定，噪声内）。tier_attempts 仅 1 次瞬时 `NVCFPexecRemoteDisconnected`（被 key 循环兜住，最终请求 200），链路仍干净；key_cycle_429s 回落（k0 69→65, k1 97→91），无 429 压力。**无需要修的参数。** R1182 预置的应对策略均未触发（429=0、无 stream/buffer 错误聚集、无 IncompleteRead 聚集）。

## 下一步建议

- 保持观察。连续十四轮全绿强 NOP 信号，下轮若仍无 429 回升 / 错误聚集，继续 NOP。
- 预置对策（仅当信号出现才动作，沿用之前设定）:
  - **429 回升 ≥5/30min** → `KEY_COOLDOWN_S` 30→60s。
  - **all_tiers_exhausted ≥3/30min 且单 key 聚集** → 检查该 key 出口 IP / 代理质量，非直接改参。
  - **NVCFPexecRemoteDisconnected / stream_no_content_gap / buffer_exhausted 聚集**（同种 ≥3/30min） → 排查上游出口而非盲目调超时（单次事件已被 key 循环兜住，不足为凭）。