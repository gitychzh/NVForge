# RN1058: NOP — 链路健康 (SR 99.19%)，k2 连续四轮各 1 次暂态流截断 (0.8%) 未达聚集阈值，不改参数

日期: 2026-08-08 10:12 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF 链路)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

RN1048~RN1057 全绿健康稳态延续。本窗口 **1 次暂态 `NVStream_IncompleteRead`** (k2, 38288ms)。此即 **k2 连续第四轮各出现 1 次**流截断（RN1055/1056/1057/1058，每轮 1 次，单点率 ~0.8%）。仍属"持久性稀疏"而非窗口内聚集（每轮均仅 1 次，未达 RN1055/RN1057 预设的"≥3/30min 同 key 聚集"动作阈值，也尚未满 RN1057 的"连续 ≥5 轮"排查线）。守"改前必有数据"+"一次只改一个参数"铁律不动作。

注意：k2 这 4 轮截断 **elapsed_ms 均为同一值 38288ms**——疑为确定性读取边界而非随机网络噪声，是需持续追踪的信号，但当前单点率与零延迟影响不足以归因动作。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **99.19%** (122/123, 1 error, 0 timeout) |
| 错误 / Fallback | **NVStream_IncompleteRead 1 / 0** |
| Avg / P50 / P95 / Max | 16012 / 11119 / 44389 / 68361 ms |
| 429 / timeout | 0 / 0 |
| upstream_type | nvcf_pexec 123/123 (100%) — 无 integrate |
| finish_reason | tool_calls 101, stop 21 |

**Per-key 200 延迟**（k2 为唯一错误位，延迟无异常）:
```
key0|23req|avg11940|P5032319
key1|21req|avg14977|P5044683
key2|28req|avg17341|P5045715   ← 1 error NVStream_IncompleteRead 38288ms（负载最高，28req）
key3|25req|avg19006|P5029595
key4|25req|avg15256|P5030622
```
5 key 负载基���均匀 (21-28 req/key)、延迟同量级 (11.9-19.0s avg)。k2 唯一错误单点暂态，avg/P95 无异常。

**tier_attempts**: 空（30min 内 0 触发 key 切换失败）。

**key_cycle_429s**: 0|42, 1|81 — 与上轮 (0|39, 1|79) 属噪声波动，30min 429=0 验明无 429/循环压力。

## 趋势

- **6h**: 1845/1841 → 累积口径（4 失败为稀疏残留）
- **3h 逐小时**: 02:00 45/45 (100%), 01:00 236/235 (99.6%), 00:00 310/310 (100%), 23:00 272/272 (100%) — 最近整点小时基本全 100%
- **24h all_tiers_exhausted**: 35（较上轮 36 略降，陈旧累积口径，本窗口 0 被完全兜住）

## 容器状态

`dsvf0731_nv40666` Up 8 hours；`nv_gw` Up 31h；`hm4104` Up 3 days。`/health` ok，proxy_role=passthrough，nv_num_keys=5，dsv4f0731_nv 在 nvcf_pexec_models。

## hm4104 fallback 日志（非本容器问题）

最近 5min fallback 日志为空，本窗口无 fallback 信号。hm4104 的 R840 content_filter zombie 后置 fallback 属 nv_gw 主链路 (glm5.2 等) 内核侧流内容过滤，与 dsvf0731_nv40666 的 tier/参数无关。仅备案。

## 修改记录

无（NOP）。维持当前参数：UPSTREAM_TIMEOUT=50, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=90, KEY_COOLDOWN_S=30, NVU_TIER_BUDGET_DSV4F0731_NV=180, NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3, NVU_KEYMGR_429_{BASE,MAX}_COOLDOWN=120。

## 下一步建议

- k2 已连续四轮各 1 次 NVStream_IncompleteRead（均 38288ms）。此为最需追踪信号：**若下一轮（RN1059，即连续第 5 轮）仍出现 ≥1 次**，将触发 RN1057 预设的排查线——启动对 k2 出口 IP / SOCKS5 代理 (7904, 出口 134.195.101.197) 的链路质量排查（验证 38288ms 固定值是否 PVCF 端确定性截图）。若升级为窗口内聚集（≥3/30min）则立即排查。
- 继续观察 24h all_tiers_exhausted（当前 35，持平走低）。
- 链路稳定则持续 NOP。