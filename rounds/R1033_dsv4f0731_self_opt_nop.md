# R1033: 链路极健康 SR 100% (连续第4轮), 429=0 错误=0 fallback=0, 5 key 均匀 — NOP

> 时间: 2026-08-08 04:55 UTC
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
> 状态: **NOP (无参数修改)** — 30min SR 100% (203/203), 6h SR 99.5%, 429=0, fallback=0, 错误=0
> Fallback: hm4104 近 5min 无 fallback 日志 (0 次), PRIMARY_URL 确认指向本容器

## 1. 背景 (改前必有数据)

R1032 为 NOP (30min SR 100%)。本轮 30min 窗口再次全绿: SR 100%, 429=0, 错误=0,
fallback=0, 5 key 延迟/load 完全均匀。链路保持最佳并发稳态, **连续四轮 100% SR**
(R1030/R1031/R1032/R1033 均 100%)。

### 30min 窗口 — nv_requests (tier_model='dsv4f0731_nv')
- 总量 203, 200=203, err=0, **SR=100%** (203/203)
- Avg/P50/P95/Max: 9627ms / 8251ms / 22186ms / 30437ms
  (延迟健康: avg 9.6s, p50 8.3s, 与 R1032 相当)
- 错误: **0** (错误分类表为空)
- upstream: nvcf_pexec 全部 (203/203), integrate 0
- finish_reason: tool_calls=176, stop=27 (正常工具调用型负载)
- 429: **0**, key_cycle_429s: k0=86, k1=117 (正常轮转计数, 无实际 429 失败)

### 30min per-key 200 延迟
| key | n | avg_ok_ms | max_ok_ms |
|-----|---|-----------|-----------|
| 0   | 39 | 10223     | 23417     |
| 1   | 41 | 7532      | 19465     |
| 2   | 39 | 11578     | 23492     |
| 3   | 41 | 9811      | 20039     |
| 4   | 43 | 9138      | 21341     |

5 key 全部活跃健康, load 分布均匀 (39-43/每 key), 延迟均匀 (7.5-11.6s avg, 方差小),
无单 key 劣化。k1 延迟最低 (7.5s), k2 略高 (11.6s) 但仍在健康范围内 (与历史模式一致)。

### Per-key 错误
- **无** (per-key 错误表为空)

### tier_attempts (30min, tier='dsv4f0731_nv')
- 本窗口无 tier_attempts 条目 — 说明所有请求首 key 即成功, 未触发 key 切换/重试出口。

### 6h / 3h / 24h 趋势
- **6h: 1945 总, 1936 ok, SR=99.5%**, 9 err, 0 429
- 3h 逐小时: 20:00=332/332(100%), 19:00=349/348(99.7%), 18:00=347/346(99.7%), 17:00=57/53(93%)
  → SR 稳定, 近一小时全绿
- 24h all_tiers_exhausted: 103 (早前劣化累积, 本 30min 窗口 0)

### Fallback 日志 (hm4104, 最近 5min)
- **无 fallback 日志** — 主链路健康, 未触发 fallback
- PRIMARY_URL 确认指向本容器 (dsvf0731_nv40666:40666)

## 2. 决策: NOP (无参数修改)

**依据:**
1. **30min SR=100% (203/203), 6h SR=99.5% (1936/1945)** — 完美, 远超 ≥95% 阈值,
   且为**连续第四轮 100% SR** (R1030/R1031/R1032/R1033 均 100%)。
2. **429=0, 错误=0, fallback=0, tier_attempts 为空** — 无任何冷却/轮转/fastbreak
   压力, 所有请求首 key 直达成功。
3. **延迟健康**: avg 9627ms / p50 8251ms, 与 R1032 (avg 9571ms) 相当, 处于近期稳定区间。
4. **5 key load 分布均匀 (39-43/每 key) + 延迟高度均匀 (7.5-11.6s avg)** —
   无 key 级问题。
5. **改前必有数据**: 无任何持续问题可归因于参数; 链路保持最佳并发稳态, 不应扰动。

## 3. 当前状态 (30min 主指标 + 6h 趋势)

- 30min SR: **100%** (203/203) / **6h SR: 99.5%** (1936/1945)
- Avg/P50/P95: 9627ms / 8251ms / 22186ms
- 错误 (30min): **0**
- 429: 0
- upstream: pexec 全部 (203/203), integrate 0
- fallback: **0** (hm4104 近 5min 无 fallback, PRIMARY 指向正确)

## 4. 上次修改效果 (R1032 NOP → 本轮)

- SR 保持 **100%** (R1032 100% → 本轮 100%), 6h 维持 99.5%。连续四轮完美。
- 延迟稳定: avg 9571ms (R1032) → **9627ms** (本轮), p50 8251ms → **8251ms** —
  基本持平, 处于健康稳态区间。
- 错误 = 0, 429 = 0, fallback = 0, 与 R1032 一致, 无退化。

## 5. 下一步建议

1. **维持现状**: 链路连续四轮 100% SR 最佳状态, 无参数改动需求。
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
- [x] 决策数据驱动: 30min SR=100%, 6h SR=99.5%, 429=0, 错误=0, fallback=0, 5 key 均匀 → NOP