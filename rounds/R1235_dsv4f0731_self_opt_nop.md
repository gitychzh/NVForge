# R1235: dsvf0731_nv40666 self-opt NOP — 30min SR回落至81.3%(12错), 全为NVCF过载tier级信号, 首触"持续性过载"阈值但无本容器杠杆

> 时间: 2026-08-09 16:36 UTC (R1234 后 ~30min)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
> 状态: **NOP (无参数修改)** — 30min SR 81.3% (52/64), 较 R1234 (92.7%) 明显回落;
> 12 错误全为 NVCF 侧/tier 级信号 (6× all_tiers_exhausted 烧满 budget + 3× client_gone_during_flush +
> 流截断类 3), 无净429, 无 key 劣化, upstream 100% pexec 正常;
> hm4104 fallback 重新活跃 (502@180s = ATE budget 烧满, breaker SKIP), 为过载下游瞬态。
> **首次触及 R1224/R1234 建议的"持续性过载"判断阈值 (30min SR<85% + fallback活跃)**, 但根因仍为 NVCF 上游过载, 本容器无参数可干净归因。

## 结论: NOP (不改任何参数)

## 依据 (30min 窗口, 2026-08-09 ~16:36)

| 指标 | 值 |
|---|---|
| 总量/成功/失败 | 64 / 52 / 12 (SR=81.3%) |
| Avg/P50/P95 | 67614 / 43043 / 278648 ms |
| 净429 | 0 |
| upstream_type | nvcf_pexec 62 req, 52 SR=83.9%; 2 null (ATE 上报 null key) |
| finish_reason | tool_calls 42, stop 7, null 3 |

### 错误分类 (12错, 全为 NVCF 侧/tier 级)
| error_type | n | avg_ms | 判定 |
|---|---|---|---|
| all_tiers_exhausted | 6 | 176770 | tier 级, 5 key 全部烧满 TIER_TIMEOUT_BUDGET=180s → NVCF 过载 |
| client_gone_during_flush | 3 | 232332 | 流式 flush 阶段客户端(hm4104)超时断开, >180s budget 后 |
| NVStream_IncompleteRead | 1 | 38595 | 流被上游截断 |
| buffer_exhausted | 1 | 149047 | 流缓冲耗尽 |
| stream_absolute_cap | 1 | 160258 | 流到绝对上限 |

### per-key 200 延迟 (count/avg/p95)
- k0: 16 / 33876 / 89927 | k1: 9 / 49884 / 97224 | k2: 13 / 45504 / 101175 | k3: 7 / 39151 / 76587 | k4: 7 / 52173 / 80202
- 各区 34-52s 均衡, k0 负载最重 (16) 且 avg 最低 (33.9s), **无单 key 代理劣化**。

### per-key 错误细分
- k0: ATE 4 (125512) + IncompleteRead 1 | null: ATE 2 (279287) | k4: client_gone 2 (240766) | k3: buffer_exhausted 1 | k1: stream_absolute_cap 1 + client_gone 1
- ATE 6 次为 tier 级 5-key 全失败归属 (k0/null 伪象), 非 k0 代理故障。client_gone 3 次分散 k1/k4, 为过载下客户端放弃。

### key_cycle_429s (内部循环计数, 非净错误)
- k0=25, k1=37, k2=1, k3=1
- k1 持续偏高(37)但 net 429=0, key manager 已吸收 → cooldown 工作正常, 无需调 KEY_COOLDOWN。

### hm4104 fallback (最近5min) — ⚠ 活跃
- 1× `PRIMARY-FAIL-STREAM` (nv_gw 502 after 180038ms ≈ budget 烧满) + 1× `PRIMARY-BREAKER-SKIP-STREAM` (circuit OPEN) + 2× `FALLBACK-STREAM` (切 ms_gw)
- 机制与 R1234 一致: **NVCF 过载 → 请求烧满 180s budget → nv_gw 502 → 适配器切 ms_gw**, breaker 短暂打开。ATE 的下游效应, 非容器参数不健康。

### 趋势
- 6h: 523/587 = **89.1% SR** (较 R1234 6h 91.1% 小幅下滑), 64 err, 0 429
- 3h逐小时: 08h=62/76(81.6%) / 07h=63/77(81.8%) / 06h=100/111(90.1%) / 05h=30/33(90.9%)
  → 07-08h 负载高峰时段 SR 跌至 81-82%, 06h 及更早 90%+ 健康 → **过载集中在最近 1-2h 高峰窗口**。
- 24h all_tiers_exhausted=126 (R1234=121, 稳于 116-126 背景带, 略升但未恶化)

## 为何不改
1. **12 个错误一丝不差地呈现 NVCF 过载签名**: 6× all_tiers_exhausted (~177s = 5 key 全烧满 budget) +
   3× client_gone_during_flush (>180s 后客户端放弃) + 3× 流截断类。这是 NVCF 上游过载, 非容器 key/超时/冷却参数可治愈。
2. **R1233/R1234 已论证收缩 NVU_TIER_BUDGET_DSV4F0731_NV 非正解**: 只让 primary 更快放弃并切 fallback, **不减少 fallback 次数** (fallback 由 ATE 过载驱动, 与 budget 长度无关), 反伤 primary 使用率。当前 ATE 6 次仍为过载烧满, 无收缩动机。
3. **净 429=0** → KEY_COOLDOWN/429 cooldown 已正确吸收 k1 高 cycle (37), 无需调 KEY_COOLDOWN。
4. **per-key 无持续劣化**: k0 负载最重但 avg 最低 (33.9s), 错误分散 k0/k1/k3/k4/null, upstream 100% pexec 运行正常, 无需调 integrate 路由。
5. **fallback 活跃是 ATE 过载的下游瞬态**: 502@180s 恰为 budget 烧满所产 NVCF 502。本窗口 SR=81% 首次触及 R1224 建议的"持续性过载"观察阈值, 但为 07-08h 高峰 1-2h 窗口的集中过载 (06h 及以前 90%+), 6h=89.1% 仍健康。调整本容器参数无法消除 NVCF 高峰过载, 只能更快触发 fallback (副作用)。

## 当前状态 (30min)
- 30min SR: **81.3%** (52/64) / **6h SR: 89.1%** (523/587)
- Avg/P50/P95: 67614ms / 43043ms / 278648ms
- 错误 (30min): `all_tiers_exhausted` 6 (176s, tier级过载烧满) + `client_gone_during_flush` 3 (232s) + IncompleteRead 1 + buffer_exhausted 1 + stream_absolute_cap 1
- 429: 0
- upstream: pexec 62 (200=52, SR=83.9%), integrate 0
- fallback: **活跃** (近 5min 1× PRIMARY-FAIL 502@180s + 1× breaker SKIP + 2× FALLBACK-STREAM) — ATE 过载瞬态

## 上次修改效果 (R1221 UPSTREAM_TIMEOUT=45, 持续生效)
- 无 NVCFPexecTimeout 集中爆发; 本窗口错误全为过载 ATE/flush/流截断类, 无超时配置问题。
- 30min SR 由 R1234 的 92.7% 回落至 81.3%, 但方向与 07-08h 高峰过载一致, 非配置回归。

## 下一步建议
- **本窗口 (SR 81% <85% + fallback 活跃) 已首次触及 R1224 判定的"持续性过载"观察阈值**。但需区分"高峰 1-2h 瞬态" vs"持续恶化": 若接下来 2-3 轮 (越过高负载峰) 30min SR 仍未回到 ≥90%, 且 24h ATE 持续 >130, 则确认为持续性 NVCF 过载, 需从**上游/代理层 (NVCF 侧 / 请求调度 / 减少并发)** 治理, 而非本容器参数。
- 持续观察 all_tiers_exhausted 24h 背景 (当前 126, 略升): 若 >150 或越峰后 3h SR 仍 <85% 再评估。
- 关注 k1 持续高 key_cycle_429s(37) 是否累积为实际净失败; 若连续 3 窗口净429>0 且集中 k1, 评估该 key SOCKS5 代理健康。
- 下轮重点: (a) 越峰后 30min SR 是否回到 ≥90%, (b) all_tiers_exhausted 是否回落 ≤5, (c) hm4104 fallback 是否随高峰过载消退而回落。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] 数据完整: 30min/6h/3h/24h/per-key/fallback 均已采集
- [x] 错误深度: 12错全为 NVCF 侧信号 (ATE 6 + client_gone 3 + 流截断 3), 429=0, 无 key 劣化
- [x] k0 ATE 集中为轮转起始位伪象, k1 高 cycle 被 429 cooldown 吸收
- [x] fallback 活跃判定为 ATE 下游客 (502@180s=budget 烧满), 非容器参数不可调
- [x] 决策数据驱动: 高峰 1-2h 过载瞬态, 6h=89.1% 健康, 无参数可干净归因 → NOP, 不扰动配置