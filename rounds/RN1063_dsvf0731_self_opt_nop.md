# RN1063: NOP — 链路持续健康 (SR 98.77%)，单次 all_tiers_exhausted 瞬态(180s预算耗尽)，key0孤立错误，0 fallback，0 429，不改参数

日期: 2026-08-08 11:56 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF 链路)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

RN1048~RN1062 健康稳态延续。本窗口 **SR 98.77% (80/81)**，唯一事件为 **key0 单次 `all_tiers_exhausted` (178825ms)** —— 单次请求烧满 180s tier 总预算仍无成功，属 NVCF 全 key 偶发停滞瞬态。

与 RN1062/R1039 同模式：**孤立 1 次 all_tiers_exhausted，无聚集、无 429 净失败、无 fallback、无 IncompleteRead、无 integrate 流量**。错误位落在 key0，属全部 5 key 分布式 NVCF-side 随机瞬态模式，与 key/代理/参数无关。

守"改前必有数据"+"一次只改一个参数"铁律。对分布式稀疏瞬态调超时/预算/冷却/快断无原理性收益（RN1048~1062 已反复论证），且会扰动当前稳定健康区间 → **不动作**。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **98.77%** (80/81, 1 error, 0 timeout) |
| 错误 / Fallback | **all_tiers_exhausted 1 @ key0 (178825ms) / 0** |
| Avg / P50 / P95 | 27981 / 14955 / 97731 ms |
| 429 / timeout | 0 / 0 |
| upstream_type | nvcf_pexec 81/81 (100%) — 无 integrate |
| finish_reason | tool_calls 67, stop 13 |
| 24h all_tiers_exhausted | 30（近 6h 净失败 7/1531 → 陈旧累计口径滚动甩走）|

**Per-key 200 延迟**（30min 直查，5 key 负载/延迟均匀）:
```
key0|17req|avg32013|P50 90672   ← 1 error all_tiers_exhausted 178825ms (k0 孤立复现)
key1|16req|avg21914|P50 56058
key2|18req|avg22030|P50 75879
key3|16req|avg24873|P50 62853
key4|13req|avg30634|P50 119052
```
Key 间负载均匀 (13-18 req)、延迟基本同量级。单点错误 (1/81→1.2%) 对全局无统计影响。

**key_cycle_429s（30min，重要健康信号）**: key0=18, key1=62, key2=1。**0 个净 429 失败** —— 首 key 偶发 429 全部被轮转吸收到下一个 key 成功，rotation 机制完全工作正常。tier_attempts 空（无 key 循环进入失败态）。

## 趋势

| 窗口 | SR | 备注 |
|---|---|---|
| 6h | **99.54%** (1524/1531) | 7 error, 0 timeout |
| 3h | 每小时 157-224 req, SR 98.7%-100% | 03:00 有 2 err |
| 30min | 98.77% (80/81) | 1 次瞬态 all_tiers_exhausted |

## 结论

链路处于稳定健康区间。单次 `all_tiers_exhausted` (178825ms) 为 NVCF 全 key 偶发瞬态停滞，rotation/冷却机制正常（0 净 429 失败、0 fallback、5 key 均匀）。无参数层面的可归因问题，**不改任何参数**。

## 下一步建议

- 持续监测 all_tiers_exhausted 是否在 24h 口径内消退（当前 30，陈旧累计在滚动甩走）。
- 若 all_tiers_exhausted 在未来窗口出现 >2 次/30min 或伴随 fallback 上升，再评估 TIER_BUDGET 是否需从 180s 微调（当前无需）。
- 关注 key0 是否在该位置持续复现（当前为孤立瞬态，不构成 key 级劣化）。