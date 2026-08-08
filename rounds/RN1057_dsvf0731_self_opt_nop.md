# RN1057: NOP — 链路健康 (SR 99.15%)，k2 第三轮单次暂态流截断 (0.8%) 未达聚集阈值，不改参数；更正 k2 代理映射注记

日期: 2026-08-08 ~10:06 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF 链路)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

RN1048~RN1056 全绿健康稳态延续。本窗口 **1 次暂态 `NVStream_IncompleteRead`** (k2, 38288ms)，与 RN1055/RN1056 **同为 k2 的单点稀疏事件**。这已是 **k2 连续第三轮各出现 1 次**流截断 —— 属"持续但稀疏"模式（每轮 ~0.8% 单点率，1/118、1/124、1/127），**非窗口内聚集**（单轮均仅 1 次，未达 RN1055 预设的"≥3/30min 同 key 聚集"动作阈值）。守"改前必有数据"+"一次只改一个参数"铁律不动作。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **99.15%** (117/118, 1 error, 0 timeout) |
| 错误 / Fallback | **NVStream_IncompleteRead 1 / 0** |
| Avg / P50 / P95 / Max | 16203 / 11071 / 45337 / 69498 ms |
| 429 / timeout | 0 / 0 |
| upstream_type | nvcf_pexec 118/118 (100%) — 无 integrate |
| finish_reason | tool_calls 99, stop 18 |

**Per-key 200 延迟**（k2 为唯一错误位，延迟无异常）:
```
key0|21req|avg12583|P5033772
key1|21req|avg18317|P5052664
key2|27req|avg17947|P5063768   ← 1 error NVStream_IncompleteRead 38288ms
key3|23req|avg16325|P5039670
key4|25req|avg14586|P5030622
```
5 key 负载均匀 (21-27 req/key)、延迟同量级 (12.6-18.3s avg)。k2 唯一错误为单点暂态，avg/P95 无异常。

**tier_attempts**: 空（30min 内 0 触发 key 切换失败）。

**key_cycle_429s**: 0|39, 1|79 — 与上轮一致属噪声波动，30min 429=0 验明无 429/循环压力。

## 趋势

- **6h**: 1865/1861 → **SR=99.79%**（4 失败为稀疏残留，累积口径）
- **3h 逐小时**: 02:00 22/22 (100%), 01:00 236/235 (99.6%), 00:00 310/310 (100%), 23:00 295/295 (100%) — **最近整点小时基本全 100%**
- **24h all_tiers_exhausted**: 36（与上轮持平，陈旧累积口径，本窗口 0 被完全兜住）

## 容器状态

`dsvf0731_nv40666` Up 8 hours；`nv_gw` Up 31h；`hm4104` Up 3 days。`/health` ok，proxy_role=passthrough，nv_num_keys=5，pid 发现正常 (dsv4f0731_nv 在 nvcf_pexec_models)。

## hm4104 fallback 日志（非本容器问题）

最近 5min 无 fallback 日志，本窗口无 fallback 信号。hm4104 的 R840 content_filter zombie 后置 fallback 属 nv_gw 主链路 (glm5.2 等) 内核侧流内容过滤，与 dsvf0731_nv40666 的 tier/参数无关。仅备案。

## 修改记录

无（NOP）。维持当前参数：UPSTREAM_TIMEOUT=50, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=90, KEY_COOLDOWN_S=30, NVU_TIER_BUDGET_DSV4F0731_NV=180, NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3, NVU_KEYMGR_429_{BASE,MAX}_COOLDOWN=120。

## 勘误（更正 RN1056 注记）

RN1056 注记写"k2 出口 IP / SOCKS5 代理 (7896)"，实际按 env 映射 `NVU_PROXY_URL<key_idx>` 为 **k2 → socks5h://172.18.0.1:7904** (key1=7897, key3=7894, key4=7896, key5=7895)。若未来 k2 聚集触发排查，对象应为 **7904** 代理，非 7896。便于后续轮次定位。

## 下一步建议

- k2 已**连续三轮各 1 次** NVStream_IncompleteRead（RN1055/1056/1057，每轮 ~0.8% 单点率），属"持久性稀疏"而非聚集。**保持观察**：若其升级为窗口内聚集（≥3/30min）或轮次连续 ≥5 轮仍各出现 ≥1 次，则启动排查 k2 → 7904 SOCKS5 / 出口 IP (134.195.101.197, egress2) 的链路质量，并评估 UPSTREAM_TIMEOUT 是否需微调。当前单点率与零延迟影响不足以归因，且守"一次只改一参数"铁律 --- 不基于单点事件盲目调参。
- 继续观察 24h all_tiers_exhausted（当前 36，持平，应随窗口滚动走低）。
- 链路稳定则持续 NOP。