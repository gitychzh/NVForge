# R1031: 链路极健康 SR 100%, 429=0 错误=0 fallback=0, 5 key 均匀 — NOP

> 时间: 2026-08-08 04:42 UTC
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
> 状态: **NOP (无参数修改)** — 30min SR 100% (202/202), 6h SR 99.5%, 429=0, fallback=0, 错误=0
> Fallback: hm4104 近 5min 无 fallback 日志 (0 次), PRIMARY_URL 确认指向本容器

## 1. 背景 (改前必有数据)

R1030 为 NOP (30min SR 100%)。本轮 30min 窗口再次全绿: SR 100%, 429=0, 错误=0,
fallback=0, 5 key 延迟/load 完全均匀。链路保持最佳并发稳态, 连续两轮 100% SR。

### 30min 窗口 — nv_requests (tier_model='dsv4f0731_nv')
- 总量 200, 200=200, err=0, **SR=100%** (202/202 复核)
- Avg/P50/P95/Max: 9418ms / 8238ms / 21802ms / 30523ms
  (延迟健康: avg 9.4s, p50 8.2s)
- 错误: **0** (错误分类表为空)
- upstream: nvcf_pexec 全部 (200/200), integrate 0
- finish_reason: tool_calls=172, stop=28 (正常工具调用型负载)
- 429: **0**, key_cycle_429s: k0=86, k1=114 (正常轮转计数, 无实际 429 失败)

### 30min per-key 200 延迟
| key | n | avg_ok_ms | max_ok_ms |
|-----|---|-----------|-----------|
| 0   | 40 | 9741      | 20593     |
| 1   | 41 | 7063      | 11839     |
| 2   | 38 | 11093     | 23598     |
| 3   | 40 | 10371     | 21373     |
| 4   | 41 | 8973      | 21824     |

5 key 全部活跃健康, load 分布均匀 (38-41/每 key), 延迟均匀 (7.1-11.1s avg, 方差小),
无单 key 劣化。k1 延迟最低 (7.1s), k2 略高 (11.1s) 但仍在健康范围内。

### Per-key 错误
- **无** (per-key 错误表为空)

### 6h / 3h / 24h 趋势
- **6h: 1927 总, 1918 ok, SR=99.5%**, 9 err, 0 429
- 3h 逐小时: 20:00=285/285(100%), 19:00=349/348(99.7%), 18:00=347/346(99.7%), 17:00=70/65(92.9%)
  → SR 稳定, 近一小时全绿
- 24h all_tiers_exhausted: 104 (早前劣化累积, 本 30min 窗口 0)

### Fallback 日志 (hm4104, 最近 5min)
- **无 fallback 日志** — 主链路健康, 未触发 fallback
- PRIMARY_URL 确认 = `http://dsvf0731_nv40666:40666/v1`, PRIMARY_MODEL=dsv4f0731_nv 指向正确

## 2. 决策: NOP (无参数修改)

**依据:**
1. **30min SR=100% (202/202), 6h SR=99.5% (1918/1927)** — 完美, 远超 ≥95% 阈值,
   且为连续第二轮 100% SR (R1030 也是 100%)。
2. **429=0, 错误=0, fallback=0** — 无任何冷却/轮转/fastbreak 压力。
3. **延迟健康**: avg 9418ms / p50 8238ms, 与 R1030 (avg 9162ms) 相当, 处于近期稳定区间。
4. **5 key load 分布均匀 (38-41/每 key) + 延迟高度均匀 (7.1-11.1s avg)** —
   无 key 级问题。
5. **改前必有数据**: 无任何持续问题可归因于参数; 链路保持最佳并发稳态, 不应扰动。

## 3. 当前状态 (30min 主指标 + 6h 趋势)

- 30min SR: **100%** (202/202) / **6h SR: 99.5%** (1918/1927)
- Avg/P50/P95: 9418ms / 8238ms / 21802ms
- 错误 (30min): **0**
- 429: 0
- upstream: pexec 全部 (200/200), integrate 0
- fallback: **0** (hm4104 近 5min 无 fallback, PRIMARY 指向正确)

## 4. 上次修改效果 (R1030 NOP → 本轮)

- SR 保持 **100%** (R1030 100% → 本轮 100%), 6h 维持 99.5%。连续两轮完美。
- 延迟稳定: avg 9162ms (R1030) → **9418ms** (本轮), p50 8251ms → **8238ms** —
  基本��平, 处于健康稳态区间。
- 错误 = 0, 429 = 0, fallback = 0, 与 R1030 一致, 无退化。

## 5. 下一步建议

1. **维持现状**: 链路连续两轮 100% SR 最佳状态, 无参数改动需求。
2. **若 SR 持续 ≥99.5% 数轮**: 可评估重新启用 integrate lane (NV_INTEGRATE_KEYS) 增加
   上游协议冗余, 但当前 pexec 单 lane 极度稳定, 无冗余必要, 需谨慎评估是否值得扰动。
3. **若 NVStream_IncompleteRead / 单 key 延迟持续劣化**: 才考虑 UPSTREAM_TIMEOUT/
   key 冷却微调; 当前 0 错误且 5 key 均匀, 不触发。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, nvcf_pexec_models 含 dsv4f0731_nv, port 40666)
- [x] 数据完整: 30min SR/延迟/错误分布/fallback/6h 趋势/24h 均已采集
- [x] hm4104 近 5min 无 fallback 日志, PRIMARY_URL 确认指向本容器 (dsvf0731_nv40666:40666)
- [x] 决策数据驱动: 30min SR=100%, 6h SR=99.5%, 429=0, 错误=0, fallback=0, 5 key 均匀 → NOP