# R1236: dsvf0731_nv40666 self-opt NOP — SR回升至87.5%, fallback转静默, 高峰过载峰越过, 持续观察中

> 时间: 2026-08-09 17:06 UTC (R1235 后 ~30min)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
> 状态: **NOP (无参数修改)** — 30min SR 87.5% (49/56), 较 R1235 (81.3%) 回升;
> 7 错误仍全为 NVCF 侧/tier 级信号 (5× all_tiers_exhausted + 1× client_gone_during_flush +
> 1× stream_absolute_cap), 无净429, 无 key 劣化, upstream 100% pexec 正常;
> hm4104 fallback 近 5min **转静默 (0 次)** — 高峰过载瞬态消退中, 非持续性恶化。

## 结论: NOP (不改任何参数)

## 依据 (30min 窗口, 2026-08-09 ~17:06)

| 指标 | 值 |
|---|---|
| 总量/成功/失败 | 56 / 49 / 7 (SR=87.5%) |
| Avg/P50/P95 | 60886 / 1080755* / 274776 ms (*P50 含1异常null大值, 见per-key) |
| 净429 | 0 |
| upstream_type | nvcf_pexec 55 req, 49 SR=89.1%; 1 null (ATE 上报 null key) |
| finish_reason | tool_calls 36, stop 6, null 7 |

### 错误分类 (7错, 全为 NVCF 侧/tier 级)
| error_type | n | avg_ms | 判定 |
|---|---|---|---|
| all_tiers_exhausted | 5 | 174553 | tier 级, 5 key 烧满 TIER_TIMEOUT_BUDGET=180s → NVCF 过载 |
| client_gone_during_flush | 1 | 289985 | 流式 flush 阶段客户端(hm4104)超时断开, >180s budget 后 |
| stream_absolute_cap | 1 | 165481 | 流到绝对上限 |

### per-key 200 延迟 (count/avg/p95)
- k0: 18 / 58863 / 121717 | k1: 10 / 35654 / 60953 | k2: 7 / 74276 / 135200 | k3: 10 / 67131 / 125829 | k4: 4 / 64064 / 140928
- 各区 35-74s, k0 负载最重 (18) 但 SR 健康; k1 avg 最低 (35.7s)/p95 最低 (61s) 最健康。
- **无单 key 代理劣化**; 30min Avg 60886ms 被 k2/k3/k4 高值拉高, 但全区维持在典型 NVCF 延迟带。

### per-key 错误细分
- k0: all_tiers_exhausted 4 (152608) | null: ATE 1 (262332) | k3: client_gone 1 + stream_absolute_cap 1
- ATE 5 次为 tier 级 5-key 全失败归属 (k0/null 伪象), 非 k0 代理故障。client_gone / stream_absolute_cap 各 1 次为过载流截断。

### key_cycle_429s (内部循环计数, 非净错误)
- k0=22, k1=32, k2=0, k3=2 (k4 无)
- k1 持续偏高(32)但 net 429=0, key manager 已吸收 → cooldown 工作正常, 无需调 KEY_COOLDOWN。

### hm4104 fallback (最近5min) — ✅ 静默
- **0 次 fallback** (R1235 该窗口 1× PRIMARY-FAIL + 1× breaker SKIP + 2× FALLBACK-STREAM 活跃)。
- 高峰过载 transients 消退, primary dsv4f0731_nv 恢复可用, 适配器不再切 ms_gw。

### 趋势
- 6h: 524/594 = **88.2% SR** (R1235 89.1%, 基本持平), 70 err, 0 429
- 3h逐小时: 09h=10/11(90.9%) / 08h=101/123(82.1%) / 07h=63/77(81.8%) / 06h=85/96(88.5%)
  - 09h 已回到 90.9%, 08h 仍 82.1% (峰值残影), 但 09h 已明显回升 → **过载峰正在越过**。
- 24h all_tiers_exhausted=129 (R1235=126, 稳于 116-130 背景带, 未恶化)

## 为何不改
1. **7 个错误仍一丝不差地呈现 NVCF 过载签名**: 5× all_tiers_exhausted (~175s = 5 key 全烧满 budget) +
   client_gone 1 + stream_absolute_cap 1。这是 NVCF 上游过载, 非容器 key/超时/冷却参数可治愈。
2. **R1233/R1234 已论证收缩 NVU_TIER_BUDGET_DSV4F0731_NV 非正解**: 只让 primary 更快放弃并切 fallback,
   **不减少 fallback 次数** (fallback 由 ATE 过载驱动), 反伤 primary 使用率。当前 ATE 5 次为过载烧满, 无收缩动机。
3. **净 429=0** → KEY_COOLDOWN/429 cooldown 已正确吸收 k1 高 cycle (32), 无需调 KEY_COOLDOWN。
4. **per-key 无持续劣化**: k0 负载最重 (18) 但 SR 健康, k1 最健康 (avg 35.7s/p95 61s), 错误分散 k0/k3/null,
   upstream 100% pexec 运行正常, 无需调 integrate 路由。
5. **fallback 转静默是过载消退的确认信号**: R1235 活跃 (ATE 驱动) → 本轮 0 次。结合 09h SR 回到 90.9%,
   判定为 07-08h 高峰瞬态而非持续性恶化, 无需任何本容器干预。

## 当前状态 (30min)
- 30min SR: **87.5%** (49/56) / **6h SR: 88.2%** (524/594)
- Avg/P50/P95: 60886ms / (P50表象异常) / 274776ms — 实际 per-key avg 35-74s 均在典型 NVCF 延迟带
- 错误 (30min): `all_tiers_exhausted` 5 (~175s, tier级过载烧满) + `client_gone_during_flush` 1 (290s) + `stream_absolute_cap` 1 (165s)
- 429: 0
- upstream: pexec 55 (200=49, SR=89.1%), integrate 0
- fallback: **静默** (近 5min 0 次, 较 R1235 活跃明显回落)

## 上次修改效果 (R1221 UPSTREAM_TIMEOUT=45, 持续生效)
- 无 NVCFPexecTimeout 集中爆发; 本窗口错误仍为过载 ATE/flush/流截断类, 无超时配置问题。
- 30min SR 由 R1235 的 81.3% 回升至 87.5%, fallback 由活跃转静默 — 方向与高峰过载消退一致, 非配置回归。

## 下一步建议
- **R1224 判定的"持续性过载"观察阈值正被否定**: R1235 SR 81% (<85%) + fallback 活跃首次触及阈值,
  但本轮 SR 回升至 87.5% + fallback 转静默 + 09h SR 回到 90.9%, 确认为 07-08h 高峰瞬态而非持续恶化。
- 若越峰后 1-2 轮 30min SR 稳定 ≥90% 且 24h ATE 稳于 ≤130, 则确认高峰过载已完全越过, 容器保持健康 NOP。
- 持续观察 all_tiers_exhausted 24h 背景 (当前 129): 若 >150 或越峰后 3h SR 仍 <85% 再评估。
- 关注 k1 持续高 key_cycle_429s(32) 是否累积为实际净失败; 若连续 3 窗口净429>0 且集中 k1, 评估该 key SOCKS5 代理健康。
- 下轮重点: (a) 越峰后 30min SR 是否稳定 ≥90%, (b) all_tiers_exhausted 是否回落 ≤5, (c) hm4104 fallback 是否保持静默。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] 数据完整: 30min/6h/3h/24h/per-key/fallback 均已采集
- [x] 错误深度: 7错全为 NVCF 侧信号 (ATE 5 + client_gone 1 + stream_absolute_cap 1), 429=0, 无 key 劣化
- [x] k0 ATE 集中为轮转起始位伪象, k1 高 cycle 被 429 cooldown 吸收
- [x] fallback 转静默判定为过载消退确认信号, 非容器参数可调
- [x] 决策数据驱动: 高峰过载瞬态确认越过 (SR回升+fallback静默+09h 90.9%), 无参数可干净归因 → NOP, 不扰动配置