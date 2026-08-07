# R1030: 链路极健康 SR 100%, 0 错误 0 429 0 fallback — NOP

> 时间: 2026-08-08 04:18 UTC
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
> 状态: **NOP (无参数修改)** — 30min SR 100% (204/204), 6h SR 99.5%, 429=0, err=0, fallback=0
> Fallback: hm4104 近 5min 无 fallback 日志 (0 次)

## 1. 背景 (改前必有数据)

R1029 为 NOP (30min SR 98.7%, 2 单次瞬时错误被 ms_gw 兜底)。本轮 30min 窗口**完全无错误**,
恢复极健康稳态: SR=100%, 429=0, fallback=0, tier_attempts 为空。主链路 pexec 单 lane 稳态未破坏。

现行可调参数无 over-tune: UPSTREAM_TIMEOUT=50, TIER_TIMEOUT_BUDGET_S=180,
TIER_COOLDOWN_S=90, KEY_COOLDOWN_S=30, 429 BASE=MAX=120, CONN 30/60/3/120,
NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3, NVU_TIER_BUDGET_DSV4F0731_NV=180。

### 30min 窗口 — nv_requests
- 总量 204, 200=204, err=0, **SR=100%** (204/204)
- Avg/P50/P95/Max: 9198ms / 7839ms / 21393ms / 25304ms (延迟健康, p50 中值 7.8s, 较上轮更优)
- 错误: **0**
- upstream: nvcf_pexec 全部 (203/203 ok, avg 9200ms), integrate 0
- finish_reason: tool_calls=175, stop=28 (正常工具调用型负载)
- 429: **0**, key_cycle_429s: k0=88, k1=115 (正常轮转计数, 无实际 429 失败)
- tier_attempts: 空 (无 key 切换/失败, 全部一次命中)

### 30min per-key 200 延迟
| key | n | avg_ok_ms | max_ok_ms |
|-----|---|-----------|-----------|
| 0   | 40 | 9403     | 20538     |
| 1   | 42 | 7980     | 19619     |
| 2   | 42 | 9983     | 22962     |
| 3   | 38 | 8395     | 21196     |
| 4   | 42 | 10160    | 22993     |

5 key 全部活跃, 负载近乎均匀 (38-42 各), 延迟高度均匀 (7.9-10.2s avg, max 19.6-23s), 无单 key 劣化。

### 6h / 3h / 24h 趋势
- **6h: 1884 总, 1874 ok, SR=99.5%**, 10 err, 0 429
- 3h 逐小时: 20:00=128/128(100%), 19:00=349/348(99.7%), 18:00=347/346(99.7%), 17:00=192/187(97.4%)
  → SR 稳定 97.4-100%, 最近一小时全绿
- 24h all_tiers_exhausted: 108 (早前劣化累积, 本 30min 窗口 0)

### Fallback 日志 (hm4104, 最近 5min)
- **无 fallback 日志** — 主链路健康, 未触发 fallback

## 2. 决策: NOP (无参数修改)

**依据:**
1. **30min SR=100% (204/204)**, err=0, **6h SR=99.5% (1874/1884)** — 远超 ≥95% 阈值, 极健康。
2. **429=0, fallback=0, tier_attempts 空** — 无任何冷却/轮转/fastbreak 压力; 全部请求一次命中 key, 无切换。
3. **延迟健康且均匀** — p50 7839ms (较上轮 13358ms 大幅走优), 5 key avg 7.9-10.2s 极其均匀, 无单 key 劣化。
4. **错误清零** — 上轮 2 单次瞬时错误本轮完全消失, 回落到极稳基线。非参数可归因, 无改动方向。
5. **改前必有数据**: 无任何持续数据支持参数改动 — 链路处于极健康稳态, 不应扰动。一次只改一个参数原则下无目标参数。

## 3. 当前状态 (30min 主指标 + 6h 趋势)

- 30min SR: **100%** (204/204) / **6h SR: 99.5%** (1874/1884)
- Avg/P50/P95: 9198ms / 7839ms / 21393ms
- 错误 (30min): **0**
- 429: 0
- upstream: pexec 全部 (203/203), integrate 0
- fallback: **0** (hm4104 近 5min 无 fallback)

## 4. 上次修改效果 (R1029 → R1030)

- 30min SR: 98.7% (R1029) → **100%** (本轮), 错误 2→0, 恢复全绿。
- 6h SR 走强: 99.3% (R1029) → **99.5%** (本轮)。
- p50 延迟: 13358ms → **7839ms** (负载窗口差异, 但延迟更优)。
- 429=0, fallback=0 (R1029 曾 2× zombie 兜底), 无端到端劣化。链路在无扰动下保持极稳。

## 5. 下一步建议

1. **维持现状**: 链路连续多轮 NOP 极健康且本轮 SR 100%, 无参数改动需求。
2. **若 SR 持续 ≥99% 多轮**: 可评估重新启用 integrate lane
   (NV_INTEGRATE_KEYS) 增加上游协议冗余, 但需先确认 pexec 单 lane 稳定数日。
   当前 NV_INTEGRATE_KEYS 为空 (fully pexec single-lane), NV_INTEGRATE_PROXY_URLS 已预留
   7897/7895 双 socks5h (但未挂载 key)。
3. **若 NVStream_IncompleteRead / stream_first_byte_timeout 反复出现** (如 >3/30min 或单 key 集中):
   才考虑 UPSTREAM_TIMEOUT (50→60) 或该 key 冷却微调; 当前零错误不触发。
4. **若单 key 延迟持续 >30s 或错误集中**: 才考虑 key 级冷却调整 / integrate key 重分配。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] 容器状态 Up 2 hours (存活)
- [x] 数据完整: 30min SR/延迟/错误分布/fallback/6h 趋势/24h 均已采集
- [x] 决策数据驱动: 30min SR=100%, err=0, 6h SR=99.5%, 429=0, fallback=0, 无 key 劣化 → NOP