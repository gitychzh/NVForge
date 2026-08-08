# RN1059: NOP — 链路健康 (SR 99.16%)，错误均为 NVCF 侧分布式稀疏残留 (无聚集/无延迟影响)，k2 定值流截断本轮再露面 (01:54) 但维持单点稀疏，不改参数

日期: 2026-08-08 10:42 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF 链路)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

RN1048~RN1058 健康稳态延续。本窗口 **SR 99.16% (118/119)**，唯一事件为 **k3 `zombie_empty_completion` (5084ms, finish_reason=stop)**。

3h 交叉核验（nv_requests 直查，非仅注入窗口）：本 30min 窗口 k2 未见上次的 NVStream_IncompleteRead，但 **01:54 k2 出现 1 次定值 38288ms 流截断**（即 RN1055~1058 追踪的 k2 模式延续，本次落在注入窗口外）。同时 02:38 出现新的 k3 zombie。

**24h 全量错误审计**（80 行）给出确定性判断：**两类残留均为 NVCF 侧分布式稀疏噪声，与 key/代理/参数无关**：
- `zombie_empty_completion` 24h **分布于全部 5 key**（k0=7, k2=6, k4=6, k3=5, k1=4），单 key 速率 ~0.1/时 → **非 key 聚集**，NVCF 端随机空响应。
- `NVStream_IncompleteRead` 24h 各 key 1~3 次，k2 的 38288ms 定值（32181/36379/38288）确认确定性读边界，仍为"持久性稀疏"（~1/8h）。
- 两错误均非 ≥3/30min 同 key 聚集，均无延迟劣化，无 429，无 fallback，无 timeout。
- 早期 08-07 03:00–08:52 的 `all_tiers_exhausted`/`stream_absolute_cap` 密集段早已全清；**近 14h 无 all_tiers_exhausted**（最后为 08-07 17:47-17:59 瞬发簇，已兜住），24h 计数随滚动走低 36→35→32。

守"改前必有数据"+"一次只改一参数"铁律。针对分布式稀疏残留调超时/预算/冷却/快断均无原理性收益，且会扰动当前稳定健康区间 → **不动作**。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **99.16%** (118/119, 1 error, 0 timeout) |
| 错误 / Fallback | **zombie_empty_completion 1 @ k3 (5084ms) / 0** |
| Avg / P50 / P95 / Max | 16524 / 11203 / 44628 / 83048 ms |
| 429 / timeout | 0 / 0 |
| upstream_type | nvcf_pexec 119/119 (100%) — 无 integrate |
| finish_reason | tool_calls 96, stop 22 |

**Per-key 200 延迟**（30min 直查，5 key 负载/延迟均匀）:
```
key0|23req|avg16480|P5011084|P9540307
key1|23req|avg13511|P509547 |P9531147   ← 负载最低，延迟最低
key2|25req|avg17376|P509775 |P9548453   ← 本窗口无错误（IncompleteRead 落在 01:54 窗口外）
key3|26req|avg17588|P5011195|P9548083   ← 1 error zombie 5084ms
key4|24req|avg16278|P5014982|P9531241
```
Key 间负载与延迟同量级 (13.5-17.6s avg, 23-26 req)。单点错误对全局无统计影响。tier_attempts 空（0 key 循环失败），key_cycle_429s=0|34,1|84,2|1 属噪声，429=0 验明无压力。

## 趋势

- **6h**: 1762/1757 → **SR=99.72%**（5 失败为稀疏残留）
- **3h 逐小时**: 02:00 165/164 (99.4%), 01:00 236/235 (99.6%), 00:00 310/310 (100%), 23:00 89/89 (100%) — 整点小时基本全 100%
- **24h all_tiers_exhausted**: 32（较上轮 35 续降；近 14h 已无新增，陈旧累积口径在滚动甩走）

## 容器状态

`dsvf0731_nv40666` Up 8 hours；`nv_gw` Up 31h；`hm4104` Up 3 days；`nv_gw_stable` Up 6d。`/health` ok，proxy_role=passthrough，nv_num_keys=5，dsv4f0731_nv 在 nvcf_pexec_models。

## hm4104 fallback 日志（非本容器问题）

最近 5min fallback 日志为空，本窗口无 fallback 信号。备案同前。

## 修改记录

无（NOP）。维持当前参数（env 实测）：UPSTREAM_TIMEOUT=50, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=90, KEY_COOLDOWN_S=30, NVU_TIER_BUDGET_DSV4F0731_NV=180, NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3, NVU_KEYMGR_429_{BASE,MAX}_COOLDOWN=120, NVU_KEYMGR_CONN_{BASE,MAX,LONG}_COOLDOWN=30/60/120, NVU_KEYMGR_CONN_FAIL_THRESHOLD=3。

## 下一步建议

- **zombie_empty_completion 升级为 24h 分布式噪声的新主角**：全部 5 key 皆有，走势随机（单 key ~0.1/时）。因跨全部 key 且无聚集，判定为 NVCF 端随机空响应，**非本容器可控参数可改善**；持续交叉核验但无需为此调参。
- k2 定值 (38288ms) NVStream_IncompleteRead **本轮 01:54 再现**（RN1055 起已 ~5 次）。仍为"持久性稀疏"，未达 ≥3/30min 聚集阈值。建议聚焦推理：确定值 almeta 为 NVCF 端确定性读边界 — 关注它是否随窗口滚动升级。
- 若后续出现**同 key ≥3/30min** 或 **单小时 ≥5 次**任一错误聚集，才启动该 key 出口 IP / SOCKS5 代理链路针对性排查。
- 继续观察 24h all_tiers_exhausted（当前 32，持续走低即健康）。
- 链路稳定则持续 NOP。