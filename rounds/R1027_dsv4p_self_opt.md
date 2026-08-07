# R1027: 链路极健康 SR 99.3%, 单次瞬时 IncompleteRead — NOP

> 时间: 2026-08-08 03:06 UTC
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
> 状态: **NOP (无参数修改)** — 30min SR 99.3% (143/144), 6h SR 99.3%, 429=0, fallback=0
> Fallback: hm4104 近 5min 无 fallback 日志 (0 次)

## 1. 背景 (改前必有数据)

R1026 为 NOP 观察轮 (SR 95.9%, 链路健康稳态)。本轮 30min 窗口健康度进一步提升。
现行可调参数无 over-tune: UPSTREAM_TIMEOUT=50, TIER_TIMEOUT_BUDGET_S=180,
TIER_COOLDOWN_S=90, KEY_COOLDOWN_S=30, 429 BASE=MAX=120, CONN 30/60/3/120,
NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3。整链路 pexec 单 lane。

### 30min 窗口 — nv_requests
- 总量 144, 200=143, err=1, **SR=99.3%** (143/144)
- Avg/P50/P95/Max: 14292ms / 11532ms / 34893ms / 46670ms (延迟健康, p50 中值 11.5s)
- 错误 (1 个): **NVStream_IncompleteRead=1** (avg 33764ms, 单次, key1)
- upstream: nvcf_pexec 全部 (144/144), integrate 0
- finish_reason: tool_calls=125, stop=18 (正常工具调用型负载)
- 429: **0**, key_cycle_429s: k0=55, k1=89 (正常轮转计数, 无实际 429 失败)

### 30min per-key 200 延迟
| key | n | avg_ok_ms | max_ok_ms |
|-----|---|-----------|-----------|
| 0   | 27 | 13728     | 30948     |
| 1   | 28 | 13824     | 28772     |
| 2   | 30 | 13753     | 33015     |
| 3   | 29 | 13546     | 36885     |
| 4   | 29 | 15900     | 35487     |

5 key 全部活跃健康, 延迟高度均匀 (13.5-15.9s avg), 无单 key 劣化。

### Per-key 错误
- 仅 k1: NVStream_IncompleteRead=1
- 单次瞬时错误, 非模式化 — 无参数可归因

### 6h / 3h / 24h 趋势
- **6h: 1747 总, 1735 ok, SR=99.3%**, 12 err, 0 429
- 3h 逐小时: 19:00=30/30(100%), 18:00=346/347(99.7%), 17:00=273/279(97.8%), 16:00=244/244(100%)
  → SR 稳定 97.8-100%, 近一小时全绿
- 24h all_tiers_exhausted: 119 (早前劣化累积, 本 30min 窗口 0)

### Fallback 日志 (hm4104, 最近 5min)
- **无 fallback 日志** — 主链路健康, 未触发 fallback

## 2. 决策: NOP (无参数修改)

**依据:**
1. **30min SR=99.3% (143/144), 6h SR=99.3% (1735/1747)** — 远超 ≥95% 阈值, 极健康。
2. **429=0, fallback=0** — 无任何冷却/轮转/fastbreak 压力。
3. **延迟健康且均匀** — p50 11532ms, 5 key avg 13.5-15.9s 极其均匀, 无单 key 劣化。
4. **错误仅 1 个瞬时单 key** (k1 NVStream_IncompleteRead, avg 33764ms) — 流截断单次残余,
   非参数可归因, 不足以触发 NVU_PEXEC_TIMEOUT_FASTBREAK (阈值=3) 或任何冷却。
5. **改前必有数据**: 无任何持续数据支持参数改动 — 链路维持极健康稳态, 不应扰动。

## 3. 当前状态 (30min 主指标 + 6h 趋势)

- 30min SR: **99.3%** (143/144) / **6h SR: 99.3%** (1735/1747)
- Avg/P50/P95: 14292ms / 11532ms / 34893ms
- 错误 (30min): NVStream_IncompleteRead=1 (k1)
- 429: 0
- upstream: pexec 全部 (144/144), integrate 0
- fallback: **0** (hm4104 近 5min 无 fallback)

## 4. 上次修改效果 (R1026 NOP 观察轮)

- 链路健康进一步提升: SR 95.9% (R1026 30min) → **99.3%** (本轮 30min)，6h 同步 97.3% → 99.3%。
- 无参数扰动下链路更稳: 错误 5 (R1026) → 1 (本轮), 429=0, fallback=0 连续三轮。
- all_tiers_exhausted 0/30min (R1026 有 2), 残余劣化完全清零。

## 5. 下一步建议

1. **维持现状**: 链路连续 N 轮 NOP 健康且趋势走强 (SR 99.3%), 无参数改动需求。
2. **若 SR 持续 ≥99% 多轮**: 可评估重新启用 integrate lane
   (NV_INTEGRATE_KEYS) 增加上游协议冗余, 但需先确认 pexec 单 lane 稳定数日。
3. **若 NVStream_IncompleteRead 反复出现** (如 >3/30min 或单 key 集中):
   才考虑 UPSTREAM_TIMEOUT (50→60) 或该 key 冷却微调; 当前单次不触发。
4. **若单 key 延迟持续 >30s 或错误集中**: 才考虑 key 级冷却调整。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] 数据完整: 30min SR/延迟/错误分布/fallback/6h 趋势/24h 均已采集
- [x] 决策数据驱动: 30min SR=99.3%, 6h SR=99.3%, 429=0, fallback=0, 单次瞬时错误 → NOP