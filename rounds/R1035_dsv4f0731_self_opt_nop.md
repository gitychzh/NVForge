# R1035: 链路极健康 SR 100% (连续第6轮), 429=0 错误=0 fallback=0, 5 key 均匀 — NOP

> 时间: 2026-08-08 06:26 UTC
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
> 状态: **NOP (无参数修改)** — 30min SR 100% (164/164), 6h SR 99.6%, 429=0, fallback=0, 错误=0
> Fallback: hm4104 近 5min 无 fallback 日志 (0 次), PRIMARY_URL 确认指向本容器

## 1. 背景 (改前必有数据)

R1034 为 NOP (30min SR 100%)。本轮 30min 窗口再次全绿: SR 100%, 429=0, 错误=0,
fallback=0, 5 key 延迟/load 完全均匀。链路保持最佳并发稳态, **连续六轮 100% SR**
(R1030/R1031/R1032/R1033/R1034/R1035 均 100%)。

### 30min 窗口 — nv_requests (tier_model='dsv4f0731_nv')
- 总量 164, 200=164, err=0, **SR=100%** (164/164)
- Avg/P50/P95/Max: 10872ms / 8445ms / 26696ms / 32598ms
  (延迟健康: avg 10.9s, p50 8.4s, 与 R1034 avg 10309ms 相当)
- 错误: **0** (错误分类表为空)
- upstream: nvcf_pexec 全部 (164/164), integrate 0
- finish_reason: tool_calls=137, stop=27 (正常工具调用型负载)
- 429: **0**, key_cycle_429s: k0=62, k1=102 (正常轮转计数, 无实际 429 失败)

### 30min per-key 200 延迟
| key | n | avg_ok_ms | max_ok_ms |
|-----|---|-----------|-----------|
| 0   | 33 | 9843      | 24209     |
| 1   | 34 | 11989     | 26246     |
| 2   | 33 | 9318      | 25752     |
| 3   | 32 | 10889     | 22544     |
| 4   | 32 | 12331     | 31043     |

5 key 全部活跃健康, load 分布均匀 (32-34/每 key), 延迟均匀 (9.3-12.3s avg, 方差小),
无单 key 劣化。k2 延迟最低 (9.3s), k4 略高 (12.3s) 但仍在健康范围内 (与历史模式一致)。

### Per-key 错误
- **无** (per-key 错误表为空)

### tier_attempts (30min, tier='dsv4f0731_nv')
- 本窗口无 tier_attempts 条目 — 说明所有请求首 key 即成功, 未触发 key 切换/重试出口。

### 6h / 3h / 24h 趋势
- **6h: 2027 总, 2019 ok, SR=99.6%**, 8 err, 0 429
- 3h 逐小时: 22:00=142/142(100%), 21:00=355/355(100%), 20:00=405/405(100%), 19:00=213/213(100%)
  → SR 稳定, 近四小时全绿
- 24h all_tiers_exhausted: 81 (早前劣化累积, 本 30min 窗口 0)

### Fallback 日志 (hm4104, 最近 5min)
- **无 fallback 日志** — 主链路健康, 未触发 fallback
- PRIMARY_URL 确认指向本容器 (dsvf0731_nv40666:40666)

## 2. 决策: NOP (无参数修改)

**依据:**
1. **30min SR=100% (164/164), 6h SR=99.6% (2019/2027)** — 完美, 远超 ≥95% 阈值,
   且为**连续第六轮 100% SR** (R1030-R1035 均 100%)。
2. **429=0, 错误=0, fallback=0, tier_attempts 为空** — 无任何冷却/轮转/fastbreak
   压力, 所有请求首 key 直达成功。
3. **延迟健康**: avg 10872ms / p50 8445ms, 与 R1034 (avg 10309ms) 相当, 处于近期稳定区间。
4. **5 key load 分布均匀 (32-34/每 key) + 延迟高度均匀 (9.3-12.3s avg)** —
   无 key 级问题。
5. **改前必有数据**: 无任何持续问题可归因于参数; 链路保持最佳并发稳态, 不应扰动。

## 3. 当前状态 (30min 主指标 + 6h 趋势)

- 30min SR: **100%** (164/164) / **6h SR: 99.6%** (2019/2027)
- Avg/P50/P95: 10872ms / 8445ms / 26696ms
- 错误 (30min): **0**
- 429: 0
- upstream: pexec 全部 (164/164), integrate 0
- fallback: **0** (hm4104 近 5min 无 fallback, PRIMARY 指向正确)

## 4. 上次修改效果 (R1034 NOP → 本轮)

- SR 保持 **100%** (R1034 100% → 本轮 100%), 6h 维持 99.6%。连续六轮完美。
- 延迟稳定: avg 10309ms (R1034) → **10872ms** (本轮), p50 8449ms → **8445ms** —
  在健康稳态区间内波动, 正常。
- 错误 = 0, 429 = 0, fallback = 0, 与 R1034 一致, 无退化。

## 5. 下一步建议

1. **维持现状**: 链路连续六轮 100% SR 最佳状态, 无参数改动需求。
2. **若 SR 持续 ≥99.5% 数轮**: 可评估重新启用 integrate lane (NV_INTEGRATE_KEYS) 增加
   上游协议冗余, 但当前 pexec 单 lane 极度稳定, 无冗余必要, 需谨慎评估是否值得扰动。
3. **若 NVCFPexecTimeout / NVStream_IncompleteRead 从瞬时偶发转为频繁** (多次减速换 key
   仍失败 / 实际请求 fallback): 才考虑 UPSTREAM_TIMEOUT (50→60) 或 key 冷却微调;
   当前 0 错误不触发。
4. **若单 key 延迟持续劣化**: 才考虑 key 级冷却调整 / integrate key 重分配; 当前均匀。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, nvcf_pexec_models 含 dsv4f0731_nv, port 40666)
- [x] 数据完整: 30min SR/延迟/错误分布/tier_attempts/fallback/6h 趋势/24h 均已采集
- [x] hm4104 近 5min 无 fallback 日志, PRIMARY_URL 确认指向本容器 (dsvf0731_nv40666:40666)
- [x] 决策数据驱动: 30min SR=100%, 6h SR=99.6%, 429=0, 错误=0, fallback=0, 5 key 均匀 → NOP