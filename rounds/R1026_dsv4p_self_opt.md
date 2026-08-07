# R1026: 链路保持健康稳态 SR 95.9%, 无单 key 劣化 — NOP

> 时间: 2026-08-07 15:28 UTC
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
> 状态: **NOP (无参数修改)** — 30min SR 95.9% (≥95%), 6h SR 97.3%, 延迟稳定, 无异常错误
> Fallback: hm4104 近 5min 无 fallback 日志 (0 次)

## 1. 背景 (改前必有数据)

R1025 为恢复后首轮健康确认 NOP (SR 97.1%, RemoteDisconnected 完全归零)。
本轮 30min 窗口继续维持健康: SR 95.9%, 无 429, 无 fallback, 延迟稳定。

### 30min 窗口 — nv_requests
- 总量 123, 200=118, err=5, **SR=95.9%** (118/123)
- Avg/P50/P95: 17562ms / 9898ms / 48780ms (延迟健康, p50 个位数秒)
- 错误 (5 个): zombie_empty_completion=3 (avg 61231ms), all_tiers_exhausted=2 (avg 180049ms)
  - 均为瞬时孤立残余, 非单 key 集中, 无 RemoteDisconnected / NVStream_IncompleteRead 主导特征
- upstream: nvcf_pexec 全部 (123/123), integrate 0
- finish_reason: tool_calls=99, stop=19 (正常工具调用型负载)
- 429: **0**, key_cycle_429s: k1=111 高但为正常轮转计数, 无实际 429 失败

### 30min per-key 200 延迟
| key | n | avg_ok_ms | max_ok_ms |
|-----|---|-----------|-----------|
| 0   | 25 | 17291     | 37636     |
| 1   | 21 | 10917     | 14847     |
| 2   | 26 | 15096     | 46195     |
| 3   | 20 | 12605     | 38297     |
| 4   | 26 | 11929     | 41972     |

5 key 全部活跃健康, 延迟均匀 (10-17s avg), 无单 key 劣化。

### Per-key 错误
- k0: all_tiers_exhausted=2 + zombie_empty_completion=1
- k2: zombie_empty_completion=1
- k4: zombie_empty_completion=1
- 跨 k0/k2/k4 均匀分布, 非单 key 集中劣化

### 6h / 3h / 24h 趋势
- **6h: 1617 总, 1574 ok, SR=97.3%**, 43 err, 0 429
- 3h 逐小时: 07:00=114/119(95.8%), 06:00=265/273(97%), 05:00=243/249(97.6%), 04:00=153/156(98.1%)
  → SR 稳定 95-98%, 无退化
- 24h all_tiers_exhausted: 356 (早前 RemoteDisconnected 风暴累积, 本窗仅 2)

### Fallback 日志 (hm4104, 最近 5min)
- **无 fallback 日志** — 主链路健康, 未触发 fallback

## 2. 决策: NOP (无参数修改)

**依据:**
1. **30min SR=95.9% (118/123), 6h SR=97.3% (1574/1617)** — 均 ≥95% 阈值, 高健康。
2. **429=0, fallback=0** — 无任何冷却/轮转/fastbreak 压力。
3. **延迟健康稳定** — p50 9898ms, 5 key avg 10-17s 均匀, 无单 key 劣化。
4. **错误仅 5 个瞬时残余** (zombie_empty_completion=3, all_tiers_exhausted=2), 跨 k0/k2/k4 均匀,
   非本容器参数可归因 (all_tiers_exhausted 为瞬时全 key 劣化时烧尽 budget, 非参数过紧)。
5. **改前必有数据**: 无任何持续数据支持参数改动 — 链路维持健康稳态, 不应扰动。

## 3. 当前状态 (30min 主指标 + 6h 趋势)

- 30min SR: **95.9%** (118/123) / **6h SR: 97.3%** (1574/1617)
- Avg/P50/P95: 17562ms / 9898ms / 48780ms
- 错误 (30min): zombie_empty_completion=3, all_tiers_exhausted=2
- 429: 0
- upstream: pexec 全部 (123/123), integrate 0
- fallback: **0** (hm4104 近 5min 无 fallback)

## 4. 上次修改效果 (R1025 NOP 观察轮)

- 链路维持健康稳态: SR 97.1% (R1025 30min) → 95.9% (本轮 30min), 6h 稳定 97.3%。
- 无参数扰动下, RemoteDisconnected 风暴清零保持, 429=0, fallback=0 连续两轮。
- all_tiers_exhausted 本窗 2 个 (avg 180s 烧尽 budget) 为瞬时全 key 劣化, 非参数可解。

## 5. 下一步建议

1. **维持现状**: 链路连续两轮 NOP 健康 (SR>95%), 无参数改动需求。
2. **若 SR 持续 ≥95% 多轮**: 可评估重新启用 integrate lane (NV_KEY_INTEGRATE_KEYS)
   增加上游协议冗余, 但需先确认 pexec 单 lane 稳定数日。
3. **若 all_tiers_exhausted 频发** (如 >5/30min 或 >10/6h): 说明瞬时全 key 劣化频现,
   才考虑 TIER_COOLDOWN_S / TIER_TIMEOUT_BUDGET_S 微调。
4. **若单 key 延迟持续 >30s 或错误集中**: 才考虑 key 级冷却调整。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] 数据完整: 30min SR/延迟/错误分布/fallback/6h 趋势/24h 均已采集
- [x] 决策数据驱动: 30min SR=95.9%, 6h SR=97.3%, 429=0, fallback=0 → NOP