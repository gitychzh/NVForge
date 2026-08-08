# RN1054: NOP — 链路持续健康 (SR 100%)，无参数调整

日期: 2026-08-08 09:52 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF 链路)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

连续全绿（RN1048~RN1053 及 R1170~R1191 均 SR=100% 或近全绿）健康稳态。守"改前必有数据"+"一次只改一个参数"铁律不动作。无任何持续劣化数据可归因于参数，改动只会引入风险。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **100%** (124/124, 0 error, 0 timeout) |
| 错误 / Fallback | **0 / 0** |
| Avg / P50 / P95 | 16159 / 11327 / 47456 ms |
| 429 | 0 |
| upstream_type | nvcf_pexec 124/124 (100%) — 全 pexec，无 integrate |
| finish_reason | tool_calls 105, stop 19 |

**Per-key 200 延迟**（全 5 key 无错误，健康）:
```
key0|21req|avg16289|P5151538
key1|28req|avg19714|P5151235
key2|26req|avg14929|P5143442
key3|26req|avg17146|P5141669
key4|23req|avg11987|P5129595
```
5 key 负载均匀 (21-28 req/key)、延迟同量级 (12.0-19.7s avg)，k4 略快但无错误聚集，无劣化 key。per-key 错误为空——30min 内 **0 错误**。

**tier_attempts**: 空（30min 内 0 错误，无 key 切换失败）。

**key_cycle_429s**: 0|47, 1|77 — 与上轮 (0|48, 1|56) 属噪声波动，30min 429=0 验明无 429/循环压力。

## 趋势

- **6h**: 1901/1898 → **SR=99.84%**，3 失败（稀疏速率残留，落在本窗口外），0 fallback
- **3h 逐小时**: 01:00 198(100%), 00:00 310(100%), 23:00 316(100%), 22:00 35(100%) — **最近 4 个整点小时全 100%**
- **24h all_tiers_exhausted**: 38（陈旧累积口径，非近期事件；本窗口 0，均被兜住）

## 修改记录

无（NOP）。

## 下一步建议

- 链路持续健康，维持当前参数 (UPSTREAM_TIMEOUT=50, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=90, KEY_COOLDOWN_S=30, NVU_TIER_BUDGET_DSV4F0731_NV=180)。
- 继续观察 24h all_tiers_exhausted 是否持续走低（当前 38，与上轮 41 略降）。
- 若未来出现某 key 错误聚集或延迟方差增大，再针对性调整。