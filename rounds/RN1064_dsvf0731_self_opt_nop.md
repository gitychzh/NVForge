# RN1064: NOP — 链路持续健康 (SR 98.61%)，key4 孤立 NVStream_IncompleteRead 瞬态，0 429，0 fallback，0 all_tiers_exhausted，不改参数

日期: 2026-08-08 12:42 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF 链路)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

RN1048~RN1063 健康稳态延续。本窗口 **SR 98.61% (71/72)**，唯一事件为 **key4 单次 `NVStream_IncompleteRead` (35491ms)** —— 长流式响应被上游截断的单次瞬态。

与 RN1062/R1063 同模式：**孤立 1 次分布式瞬态错误，无聚集、无 429 净失败、无 fallback、无 all_tiers_exhausted、无 integrate 流量**。错误位落在 key4，但该 key 同窗口 200 延迟健康 (avg 26781ms)，非 key/代理级劣化，属 NVCF-side 流偶发截断。

守"改前必有数据"+"一次只改一个参数"铁律。对孤立瞬态调整超时/预算/冷却/快断无原理性收益（RN1048~1063 已反复论证），且会扰动当前稳定健康区间 → **不动作**。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **98.61%** (71/72, 1 error, 0 timeout) |
| 错误 / Fallback | **NVStream_IncompleteRead 1 @ key4 (35491ms) / 0** |
| Avg / P50 / P95 | 27011 / 18397 / 96010 ms |
| 429 / timeout / ATE | 0 / 0 / 0 |
| upstream_type | nvcf_pexec 72/72 (100%) — 无 integrate |
| finish_reason | tool_calls 58, stop 13 |

**Per-key 200 延迟**（30min 直查，5 key 负载/延迟均匀）:
```
key0|11req|avg22648|max38126
key1|14req|avg19825|max37953
key2|16req|avg30364|max95866
key3|15req|avg33003|max114659
key4|15req|avg26781|max68156   ← 1 error NVStream_IncompleteRead 35491ms (k4 孤立)
```
Key 间负载均匀 (11-16 req)、延迟同量级。单点错误 (1/72→1.4%) 对全局无统计影响。k3 的 max 114659ms 为长 tool_calls 链的正常长尾，非错误。

**key_cycle_429s（30min）**: key0=26, key1=43, key2=3。**0 个净 429 失败** —— 首 key 偶发 429 全部被轮转吸收到下一 key 成功，rotation 机制正常。tier_attempts 空。

## 趋势

| 窗口 | SR | 备注 |
|---|---|---|
| 6h | **99.37%** (1416/1425) | 9 error, 0 timeout |
| 3h | 每小时 77-225 req, SR 98.2%-99.6% | 04:00=112/114, 03:00=165/168, 02:00=224/225, 01:00=76/77 |
| 30min | 98.61% (71/72) | 1 次瞬态 NVStream_IncompleteRead |
| 24h | all_tiers_exhausted=28（滚动陈旧累计口径，正被滚动甩走） | 本 6h 无新增 ATE |

## 结论

链路处于稳定健康区间。单次 `NVStream_IncompleteRead` (35491ms, key4) 为 NVCF 长流式响应的偶发截断瞬态，rotation/冷却机制正常（0 净 429 失败、0 fallback、0 ATE、5 key 均匀）。无参数层面的可归因问题，**不改任何参数**。

## 下一步建议

- 持续监测 `NVStream_IncompleteRead` 是否复现。若未来窗口出现 >2 次/30min 或伴随同 key 延迟劣化，再评估是否需增大该 key 冷却或检查对应 SOCKS5 端口稳定性（当前无需）。
- 关注 all_tiers_exhausted 24h 口径是否继续回落（预期随滚动窗口甩走归零）。
- 保持当前健康稳态观测；仅在错误聚集/fallback 上升/finish_reason 退化时介入。