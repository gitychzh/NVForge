# R1170: dsv4f0731_nv40666 NOP — 30min 全绿 (SR=100%, 0错误, 0 fallback)

日期: 2026-08-08 07:18 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF 链路)

## 决策：NOP（不改任何参数）

## 30min 窗口数据

| 指标 | 值 |
|---|---|
| SR | **100%** (123/123) |
| 错误 / Fallback | **0 / 0** |
| Avg / P50 / P95 | 16221 / 12473 / 47618 ms |
| 429 | 0 |
| upstream_type | nvcf_pexec 124/124 (100%) — 全 pexec，无 integrate |
| finish_reason | tool_calls 105, stop 19 |

**Per-key 200 延迟**（全 5 key 无错误，健康）:
```
key0|21req|avg17651|p9547928
key1|25req|avg19825|p9551502
key2|27req|avg15825|p9548188
key3|25req|avg10423|p9523518
key4|26req|avg17507|p9537766
```
key3 持平最慢档（avg 10423 / p95 23518 最快），5 key 分布均匀，无劣化 key。per-key 错误为空表——30min 内 **0 错误**。

**tier_attempts**: 空（全直接成功，无 key 间切换）。

## 趋势

- **6h**: 1989/1979 → **SR=99.5%**，10 失败，0 fallback
- **3h 逐小时**: 20:00 275(100%), 21:00 355(100%), 22:00 262/265(98.9%), 23:00 76(100%) — 高流量(每小时 76-355)且逐小时 SR 全 ≥98.9%
- **24h all_tiers_exhausted**: 60（~2.5/h，均被 fallback 兜住，非本 30min 窗口信号）

## 关键判断

- 30min SR=100%、0 错误、0 fallback、0 429 —— **优于** 前三轮 (R1167 97.2% / R1168 97.1% / R1169 96.7%)。
- 前几轮连续观察到的单点瞬态噪声（ate/buffer/gap 各~1%）本轮**完全未出现**——进一步确认那些是底层常态噪声而非系统退化。
- 全 pexec、无 integrate、无 key 劣化、无 key_cycle 429 压力（本轮计数为累计非窗口）。
- 6h SR=99.5% + 逐小时高流量稳定 SR → 整体链路稳中向好。

**无任何调参依据。** 守"改前必有数据"铁律——健康窗口不动作，避免为调而调。

## 上次修改效果 (R1169 → R1170)

R1169 SR=96.7% (89/92, 3 单点错误)。本轮 SR=**100%** (123/123)，0 错误。上一轮判断"单点错误为常态噪声、不聚集将 NOP"得到验证——本轮错误消失。Avg 22884→16221ms 回落至常态，确认 R1169 的 avg 抬高由慢错误所致。**无参数失效。**

## 下一步建议

- 保持观察。30min 全绿为强 NOP 信号，下轮若无 429 回升 / 错误聚集，继续 NOP。
- 预置对策（仅当信号出现才动作）:
  - **429 回升 ≥5/30min** → `KEY_COOLDOWN_S` 30→60s。
  - **all_tiers_exhausted ≥3/30min 且单 key 聚集** → 检查该 key 出口 IP / 代理质量，非直接改参。
  - **stream_no_content_gap / buffer_exhausted 聚集**（≥2/30min 同种） → `NVU_BUFFER_TIMEOUT_STAIRS` 90→75 或检查 NVU_BUFFER_CALLERS 链路。
  - **NVStream_IncompleteRead 聚集 ≥30/h** → 查对应 key SOCKS5 端口与 UPSTREAM_TIMEOUT(50)。
- 若 integrate 长期 0 使用且 pexec 稳定，可考虑是否让 integrate 路由参（NV_KEY_INTEGRATE_KEYS）保持禁用——当前全 pexec 架构在 SR=100% 下无切换必要。