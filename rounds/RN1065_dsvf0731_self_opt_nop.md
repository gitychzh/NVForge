# RN1065: NOP — 链路持续健康 (SR 98.41%)，key0 孤立 all_tiers_exhausted(180s预算耗尽)，0 fallback，0 429，不改参数

日期: 2026-08-08 13:06 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF 链路)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

RN1048~RN1064 健康稳态延续。本窗口 **SR 98.41% (62/63)**，唯一事件为 **key0 单次 `all_tiers_exhausted` (180032ms)** —— 单次请求烧满 180s tier 总预算仍无成功，属 NVCF 全 key 偶发停滞瞬态。

与 RN1063 (key0 同 178825ms ATE) 完全同模式：**孤立 1 次 ATE，无聚集、无 429 净失败、无 fallback、无 IncompleteRead、无 integrate 流量**。错误位落在 key0，属全部 5 key 分布式 NVCF-side 随机瞬态模式，与 key/代理/参数无关。

守"改前必有数据"+"一次只改一个参数"铁律。对分布式稀疏瞬态调超时/预算/冷却/快断无原理性收益（RN1048~1064 已反复论证），且会扰动当前稳定健康区间 → **不动作**。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **98.41%** (62/63, 1 error, 0 timeout) |
| 错误 / Fallback | **all_tiers_exhausted 1 @ key0 (180032ms) / 0** |
| Avg / P50 / P95 | 18151 / 110839 / 153153 ms |
| 429 / timeout / ATE | 0 / 0 / 1 |
| upstream_type | nvcf_pexec 63/63 (100%) — 无 integrate |
| finish_reason | tool_calls 50, stop 12 |

**Per-key 200 延迟**（30min 直查，5 key 负载/延迟均匀）:
```
key0|11req|avg19780|max30965   ← 1 error ATE 180032ms
key1|13req|avg28229|max72476
key2|12req|avg40867|max127643
key3|16req|avg33840|max92293
key4|10req|avg17321|max29519
```
Key 间负载均匀 (10-16 req)、延迟同量级。单点错误 (1/63→1.6%) 对全局无统计影响。k2 的 max 127643ms 为长 tool_calls 链的正常长尾，非错误。

**key_cycle_429s（30min）**: key0=22, key1=39, key2=1。**0 个净 429 失败** —— 首 key 偶发 429 全部被轮转吸收到下一 key 成功，rotation 机制正常。tier_attempts 空。

## 趋势

| 窗口 | SR | 备注 |
|---|---|---|
| 6h | **99.43%** (1387/1395) | 8 error, 0 timeout |
| 3h | 每小时 16-201 req, SR 100%-98.6% | 05:00=16/16, 04:00=142/145, 03:00=165/168, 02:00=200/201 |
| 30min | 98.41% (62/63) | 1 次瞬态 ATE |
| 24h | all_tiers_exhausted=27（滚动陈旧累计口径，正被滚动甩走） | 本 6h 无新增 ATE 聚集 |

## 结论

链路处于稳定健康区间。单次 `all_tiers_exhausted` (180032ms, key0) 为 NVCF 全 5 key 偶发停滞的瞬态（同 RN1063 key0 模式），rotation/冷却机制正常（0 净 429 失败、0 fallback、5 key 均匀、无 ATE 聚集）。无参数层面的可归因问题，**不改任何参数**。

## 下一步建议

- 持续监测 `all_tiers_exhausted` 是否复现或聚集。若未来窗口出现 >2 次/30min 或伴随同 key 延迟劣化，再评估是否需调整 TIER_TIMEOUT_BUDGET_S / TIER_COOLDOWN_S（当前无需）。
- 关注 all_tiers_exhausted 24h 口径是否继续回落（预期随滚动窗口甩走归零）。
- 保持当前健康稳态观测；仅在错误聚集/fallback 上升/finish_reason 退化时介入。