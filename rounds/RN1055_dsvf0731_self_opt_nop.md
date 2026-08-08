# RN1055: NOP — 链路基本健康 (SR 99.2%)，单次暂态流截断不足归因，不改参数

日期: 2026-08-08 09:58 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF 链路)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

继续遵守 RN1054 起的连续健康稳态（RN1048~RN1054 均 SR≈100%）。本窗口出现 **1 次暂态 `NVStream_IncompleteRead`**，但为单点稀疏事件、落在单 key（k2）、无聚集无重复，不足以归因于任何参数。守"改前必有数据"+"一次只改一个参数"铁律不动作。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **99.2%** (126/127, 1 error, 0 timeout) |
| 错误 / Fallback | **NVStream_IncompleteRead 1 / 0** |
| Avg / P50 / P95 / Max | 16190 / 11119 / 45753 / 59399 ms |
| 429 | 0 |
| upstream_type | nvcf_pexec 127/127 (100%) — 无 integrate |
| finish_reason | tool_calls 109, stop 17 |

**Per-key 200 延迟**（k2 为唯一错误位，延迟无异常）:
```
key0|23req|avg14049|P515
key1|25req|avg19056|P5151674
key2|26req|avg15366|P5145791   ← 1 error NVStream_IncompleteRead 38288ms
key3|26req|avg17646|P5141669
key4|26req|avg13847|P5130584
```
5 key 负载均匀 (23-26 req/key)、延迟同量级 (13.8-19.1s avg)。k1 P95 最高 (51674) 但无错误聚集，属正常噪声。唯一错误为 k2 的单次流截断 (38288ms) — 暂态、单点、无重复。

**tier_attempts**: 空（30min 内 0 触发 key 切换失败）。

**key_cycle_429s**: 0|45, 1|82 — 与上轮 (0|47, 1|77) 噪声波动，30min 429=0 验明无 429/循环压力。

## 趋势

- **6h**: 1886/1882 → **SR=99.79%**（4 失败为稀疏残留，累积口径）
- **3h 逐小时**: 01:00 224/223 (99.5%), 00:00 310/310 (100%), 23:00 316/316 (100%), 22:00 3/3 (100%) — **最近整点小时基本全 100%**
- **24h all_tiers_exhausted**: 37（陈旧累积口径，本窗口 0 被完全兜住）

## 关于 hm4104 fallback 日志（非本容器问题）

最近 5min 的 `CONTENT_FILTER_ZOMBIE` / `PRIMARY-ZOMBIE-FALLBACK` 是 **hm4104 适配器在 nv_gw 主链路（glm5.2 等其它模型链）** 检测到 R840 content_filter zombie 后切 ms_gw fallback。这是 nv_gw 主链路流内容的后置 fallback，**与 dsvf0731_nv40666 的 tier/参数无关**，非本容器可归因或可调。仅记录备案。

## 修改记录

无（NOP）。维持当前参数：UPSTREAM_TIMEOUT=50, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=90, KEY_COOLDOWN_S=30, NVU_TIER_BUDGET_DSV4F0731_NV=180。

## 下一步建议

- 单一 NVStream_IncompleteRead / ~127 req 发生率极低，不需动作。若未来同 key（k2）或全局 IncompleteRead 出现聚集（≥3/窗口），考虑 UPSTREAM_TIMEOUT 或 k2 冷却标记。
- 继续观察 24h all_tiers_exhausted 是否持续走低（当前 37，较上轮 38 略降）。
- 维持当前参数，链路稳定则持续 NOP。