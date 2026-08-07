# R1036: 链路极健康 SR 100% (连续第7轮), 429=0 错误=0 fallback=0, 5 key 均匀 — NOP

> 时间: 2026-08-08 06:32 UTC
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
> 状态: **NOP (无参数修改)** — 30min SR 100% (148/148), 6h SR 99.6%, 429=0, fallback=0, 错误=0
> Fallback: hm4104 近 5min 无 fallback 日志 (0 次), PRIMARY_URL 确认指向本容器

## 1. 背景 (改前必有数据)

R1035 为 NOP (30min SR 100%)。本轮 30min 窗口再次全绿: SR 100%, 429=0, 错误=0,
fallback=0, 5 key 延迟/load 完全均匀。链路保持最佳并发稳态, **连续七轮 100% SR**
(R1030/R1031/R1032/R1033/R1034/R1035/R1036 均 100%)。

### 30min 窗口 — nv_requests (tier_model='dsv4f0731_nv')
- 总量 148, 200=148, err=0, **SR=100%** (148/148)
- Avg/P50/P95/Max: 12180ms / 8883ms / 30442ms / 48196ms
  (延迟健康: avg 12.2s, p50 8.9s, 处于近期健康稳态区间; p95 3.04s 略升但 p50 稳定)
- 错误: **0** (错误分类表为空)
- upstream: nvcf_pexec 全部 (148/148), integrate 0
- finish_reason: tool_calls=122, stop=26 (正常工具调用型负载)
- 429: **0**, key_cycle_429s: k0=52, k1=96 (正常轮转计数, 无实际 429 失败)

### 30min per-key 200 延迟
| key | n | avg_ok_ms | max_ok_ms |
|-----|---|-----------|-----------|
| 0   | 30 | 9984      | 24312     |
| 1   | 28 | 12314     | 26068     |
| 2   | 30 | 12612     | 36253     |
| 3   | 29 | 11799     | 27562     |
| 4   | 31 | 14122     | 40153     |

5 key 全部活跃健康, load 分布均匀 (28-31/每 key), 延迟均匀 (10.0-14.1s avg, 方差略有
放大但仍在健康范围内)。k0 延迟最低 (10.0s), k2/k4 略高 (12.6s/14.1s) 属正常波动,
无单 key 劣化。

### Per-key 错误
- **无** (per-key 错误表为空)

### tier_attempts (30min, tier='dsv4f0731_nv')
- 本窗口无 tier_attempts 条目 — 说明所有请求首 key 即成功, 未触发 key 切换/重试出口。

### 6h / 3h / 24h 趋势
- **6h: 2028 总, 2020 ok, SR=99.6%**, 8 err, 0 429
- 3h 逐小时: 22:00=166/166(100%), 21:00=355/355(100%), 20:00=405/405(100%), 19:00=183/183(100%)
  → SR 稳定, 近四小时全绿
- 24h all_tiers_exhausted: 77 (早前劣化累积, 本 30min 窗口 0)

### Fallback 日志 (hm4104, 最近 5min)
- **无 fallback 日志** — 主链路健康, 未触发 fallback
- PRIMARY_URL 确认指向本容器 (dsvf0731_nv40666:40666)

## 2. 决策: NOP (无参数修改)

**依据:**
1. **30min SR=100% (148/148), 6h SR=99.6% (2020/2028)** — 完美, 远超 ≥95% 阈值,
   且为**连续第七轮 100% SR** (R1030-R1036 均 100%)。
2. **429=0, 错误=0, fallback=0, tier_attempts 为空** — 无任何冷却/轮转/fastbreak
   压力, 所有请求首 key 直达成功。
3. **延迟健康**: avg 12180ms / p50 8883ms, p50 与 R1035 (8445ms) 相当, 处于近期稳态区间。
4. **5 key load 分布均匀 (28-31/每 key) + 延迟总体均匀** — 无 key 级问题。
5. **改前必有数据**: 无任何持续问题可归因于参数; 链路保持最佳并发稳态, 不应扰动。

## 3. 当前状态 (30min 主指标 + 6h 趋势)

- 30min SR: **100%** (148/148) / **6h SR: 99.6%** (2020/2028)
- Avg/P50/P95: 12180ms / 8883ms / 30442ms
- 错误 (30min): **0**
- 429: 0
- upstream: pexec 全部 (148/148), integrate 0
- fallback: **0** (hm4104 近 5min 无 fallback, PRIMARY 指向正确)

## 4. 上次修改效果 (R1035 NOP → 本轮)

- SR 保持 **100%** (R1035 100% → 本轮 100%), 6h 维持 99.6%。连续七轮完美。
- 延迟: avg 10872ms (R1035) → **12180ms** (本轮), p50 8445ms → **8883ms** —
  p50 稳定, avg 微升但仍处健康稳态区间, 波动正常 (p95 受少量长尾请求影响)。
- 错误 = 0, 429 = 0, fallback = 0, 与 R1035 一致, 无退化。

## 5. 下一步建议

1. **维持现状**: 链路连续七轮 100% SR 最佳状态, 无参数改动需求。
2. **若 SR 持续 ≥99.5% 更多轮**: 可评估重新启用 integrate lane (NV_INTEGRATE_KEYS) 增加
   上游协议冗余, 但当前 pexec 单 lane 极度稳定, 无冗余必要, 需谨慎评估是否值得扰动。
3. **若 NVCFPexecTimeout / NVStream_IncompleteRead 从瞬时偶发转为频繁**: 才考虑
   UPSTREAM_TIMEOUT (50→60) 或 key 冷却微调; 当前 0 错误不触发。
4. **若单 key 延迟持续劣化** (某 key avg 持续 >18s 且落后于其他 key): 才考虑 key 级冷却
   调整 / integrate key 重分配; 当前均匀。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, nvcf_pexec_models 含 dsv4f0731_nv, port 40666)
- [x] 数据完整: 30min SR/延迟/错误分布/tier_attempts/fallback/6h 趋势/24h 均已采集
- [x] hm4104 近 5min 无 fallback 日志, PRIMARY_URL 确认指向本容器 (dsvf0731_nv40666:40666)
- [x] 决策数据驱动: 30min SR=100%, 6h SR=99.6%, 429=0, 错误=0, fallback=0, 5 key 均匀 → NOP