# RN1056: NOP — 链路健康 (SR 99.2%)，k2 连续两轮单次暂态流截断未达聚集阈值，不改参数

日期: 2026-08-08 10:02 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF 链路)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

RN1048~RN1055 及 R1170~R1191 连续全绿健康稳态。本窗口 **1 次暂态 `NVStream_IncompleteRead`**（k2, 38288ms），与 RN1055 同为 k2 的单次稀疏事件（RN1055 也是 1/127）。虽属"连续两轮同 key 各出现 1 次流截断"，但每轮发生率 ~0.8%、单点单次、无窗口内聚集（1/124），未达 RN1055 预设的"≥3/30min 同 key 聚集"动作阈值。守"改前必有数据"+"一次只改一个参数"铁律不动作。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **99.2%** (123/124, 1 error, 0 timeout) |
| 错误 / Fallback | **NVStream_IncompleteRead 1 / 0** |
| Avg / P50 / P95 / Max | 15977 / 10670 / 45867 / 59497 ms |
| 429 | 0 |
| upstream_type | nvcf_pexec 124/124 (100%) — 无 integrate |
| finish_reason | tool_calls 104, stop 19 |

**Per-key 200 延迟**（k2 为唯一错误位，延迟无异常）:
```
key0|22req|avg14117|P5050650
key1|25req|avg18728|P5151674
key2|26req|avg15278|P5145791   ← 1 error NVStream_IncompleteRead 38288ms
key3|25req|avg17171|P5041729
key4|25req|avg13502|P5030622
```
5 key 负载均匀 (22-26 req/key)、延迟同量级 (13.5-18.7s avg)。k2 唯一错误 (NVStream_IncompleteRead 38288ms) 为单点暂态流截断，无聚集无重复，avg/P95 无异常。

**tier_attempts**: 空（30min 内 0 触发 key 切换失败）。

**key_cycle_429s**: 0|46, 1|78 — 与上轮 (0|45, 1|82) 属噪声波动，30min 429=0 验明无 429/循环压力。

## 趋势

- **6h**: 1875/1871 → **SR=99.79%**（4 失败为稀疏残留，累积口径）
- **3h 逐小时**: 02:00 5/5 (100%), 01:00 236/235 (99.6%), 00:00 310/310 (100%), 23:00 302/302 (100%) — **最近整点小时基本全 100%**
- **24h all_tiers_exhausted**: 36（较上轮 37 略降，陈旧累积口径，本窗口 0 被完全兜住）

## 关于 hm4104 fallback 日志（非本容器问题）

最近 5min 的 fallback 日志为空（无 log），本窗口无 fallback 信号。hm4104 的 R840 content_filter zombie 后置 fallback 属 nv_gw 主链路（glm5.2 等）的内核侧流内容过滤，与 dsvf0731_nv40666 的 tier/参数无关，非本容器可归因或可调。仅备案。

## 修改记录

无（NOP）。维持当前参数：UPSTREAM_TIMEOUT=50, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=90, KEY_COOLDOWN_S=30, NVU_TIER_BUDGET_DSV4F0731_NV=180。

## 下一步建议

- k2 已连续两轮各 1 次 NVStream_IncompleteRead（每轮 ~0.8% 单点率），目前未达聚集阈值。**若未来 k2 (或全局) IncompleteRead 出现聚集（≥3/同一窗口）**，优先排查 k2 出口 IP / SOCKS5 代理 (7896) 质量 + 顺带评估 UPSTREAM_TIMEOUT，而非盲目调参。当前单点率不足以归因。
- 继续观察 24h all_tiers_exhausted 是否持续走低（当前 36，较上轮 37 略降）。
- 链路稳定则持续 NOP。