# R1241: dsvf0731_nv40666 self-opt NOP — SR 89.7% 小回落, 8错全为NVCF过载/安全帽/流瞬态, 无容器杠杆

> 时间: 2026-08-09 18:22 UTC (R1240 后 ~30min)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
> 状态: **NOP (无参数修改)** — 30min SR 89.7% (70/78), 较 R1240 (92.5%) 回落 2.8pt;
> 8 错误: 5× all_tiers_exhausted (tier 级过载烧满 budget) + 2× stream_absolute_cap
> (NVU_STREAM_ABSOLUTE_CAP_S=150 安全帽兜底) + 1× NVStream_IncompleteRead (k2 瞬态截断),
> 无净429, 无 key 劣化, upstream 100% pexec 正常, tier_attempts 空;
> hm4104 fallback 仍活跃 (PRIMARY-FAIL-STREAM 502@180s + breaker-SKIP + FALLBACK-STREAM) —
> 高峰过载震荡残影, 3h SR 仍在 85-90% 区间, 24h ATE=138 贴近背景带。

## 结论: NOP (不改任何参数)

## 依据 (30min 窗口, 2026-08-09 ~18:22)

| 指标 | 值 |
|---|---|
| 总量/成功/失败 | 78 / 70 / 8 (SR=89.7%) |
| Avg/P50/P95 | 65745 / 50497 / 175854 ms |
| 净429 | 0 |
| upstream_type | nvcf_pexec 78 req, 70 SR=89.7% (100% pexec, integrate 0) |
| finish_reason | tool_calls 56, stop 11, null 3 |

### 错误分类 (8错: 5×ATE + 2×stream_absolute_cap + 1×NVStream_IncompleteRead)
| error_type | n | avg_ms | 判定 |
|---|---|---|---|
| all_tiers_exhausted | 5 | 147010 | tier 级, 5 key 全烧满 TIER_TIMEOUT_BUDGET=180s → NVCF 过载 |
| stream_absolute_cap | 2 | 163870 | NVU_STREAM_ABSOLUTE_CAP_S=150 安全帽兜底 (流超 150s 截断), 非批量 |
| NVStream_IncompleteRead | 1 | 32736 | k2 单起, 流被上游截断 (瞬态), 非批量 |

### per-key 200 延迟 (count/avg/p95)
- k0: 22 / 64231 / 149099 | k1: 16 / 50363 / 96480 | k2: 14 / 63550 / 133706 | k3: 12 / 58341 / 117201 | k4: 6 / 37315 / 56017
- 各区 37-64s 均衡健康, k4 avg 最低 (37.3s)/p95 最低 (56.0s) 最健康; k0 负载最重 (22) 但 SR 健康, 无一致劣化。

### per-key 错误细分
- k0: all_tiers_exhausted 5 + stream_absolute_cap 1 | k2: NVStream_IncompleteRead 1 | k3: stream_absolute_cap 1
- ATE 5 次为 tier 级 5-key 全失败归属 (k0 伪象), 非 k0 代理故障; stream_absolute_cap / IncompleteRead 为单起瞬态。

### key_cycle_429s (内部循环计数, 非净错误)
- k0=22, k1=53, k2=1, k3=1, k4=1
- k1 持续偏高(53)但 net 429=0, key manager 已吸收 → cooldown 工作正常, 无需调 KEY_COOLDOWN。

### tier_attempts
- **空** (本窗口无独立 key 切换 attempt 记录) — 与 ATE 全烧满 budget 一致, 无 key 级切换模式可归因。

### hm4104 fallback (最近5min) — 仍活跃但为过载签名
- 5 条: PRIMARY-FAIL-STREAM 502@180s (budget 烧满) + FALLBACK-STREAM×3 + PRIMARY-BREAKER-SKIP-STREAM×2。
- 与 R1237-R1240 同类过载震荡: ATE 烧满 180s → 502 → 切 ms_gw, 非容器参数不健康。

### 趋势
- 6h: 679/601/78 = **88.5% SR**, 0 429
- 3h逐小时: 10h=56/49(87.5%) / 09h=140/125(89.3%) / 08h=123/101(82.1%) / 07h=46/38(82.6%)
  - 07h→09h SR 回升 (82.6%→89.3%), 10h 小回落 87.5% — 高峰过载震荡在 85-90% 区间, 未明显越过也未崩。
- 24h all_tiers_exhausted=138 (R1240=134, R1239=131, R1238=132 — 小升 4-7, 贴近背景带 116-138, 未恶化)

## 为何不改
1. **8 个错误全部为 NVCF 侧过载/流事件签名**: 5× all_tiers_exhausted (avg ~147s = 5 key 全烧满 180s budget)
   + 2× stream_absolute_cap (安全帽, 流超 150s 截断) + 1× NVStream_IncompleteRead (k2 瞬态截断)。
   均为 NVCF 上游过载/流行为, 非容器 key/超时/冷却参数可治愈。R1235-R1241 同签名, 无新批量错误类型。
2. **R1233/R1234 已论证收缩 NVU_TIER_BUDGET_DSV4F0731_NV 非正解**: 只让 primary 更快放弃并切 fallback,
   **不减少 fallback 次数** (fallback 由 ATE 过载驱动), 反伤 primary 使用率。当前 ATE 5 次为过载烧满, 无收缩动机。
3. **净 429=0**, key_cycle_429s (k1=53) 被 key manager 完全吸收 → KEY_COOLDOWN/429 cooldown 工作正常, 无需调整。
4. **per-key 无持续劣化**: k0-k4 avg 37-64s 均衡健康, 错误全归 tier 级 ATE (k0 伪象) + 单起流事件,
   upstream 100% pexec 运行正常, 无需调 integrate 路由。
5. **fallback 活跃是高峰过载震荡残影**: 与 R1237-R1240 同类 (502@180s=budget 烧满), 但 6h SR 88.5% 稳定、
   24h ATE=138 贴近背景带、30min SR 89.7% 未达 <80% 崩盘阈值。判定为过载震荡, 无需任何本容器干预。

## 当前状态 (30min)
- 30min SR: **89.7%** (70/78), 较 R1240 (92.5%) 回落 2.8pt / **6h SR: 88.5%** (601/679)
- Avg/P50/P95: 65745 / 50497 / 175854 ms — per-key avg 37-64s 均在典型 NVCF 延迟带
- 错误 (30min): `all_tiers_exhausted` 5 (~147s, tier级过载烧满) + `stream_absolute_cap` 2 (安全帽)
  + `NVStream_IncompleteRead` 1 (k2 瞬态)
- 429: 0
- upstream: pexec 78 (200=70, SR=89.7%), integrate 0
- fallback: **活跃** (近 5min 502@180s + FALLBACK-STREAM×3 + breaker-SKIP×2, 过载震荡残影)

## 上次修改效果 (R1221 UPSTREAM_TIMEOUT=45, 持续生效)
- 无 NVCFPexecTimeout/UPSTREAM_TIMEOUT 集中爆发; 本窗口错误纯为 ATE (过载烧满) + 安全帽 + 流瞬态, 无超时配置问题。
- 30min SR 由 R1240 的 92.5% 回落至 89.7% (过载震荡), 6h SR 88.9%→88.5% 持平 — 无配置回归, 为 NVCF 过载波动。

## 下一步建议
- 持续观察高峰过载震荡: 若 1-2 轮 30min SR 稳定 ≥90% 且 hm4104 fallback 转静默、24h ATE 稳于 ≤140,
  则确认高峰已越过, 容器保持健康 NOP。
- 若 SR 再跌 <85% 且 fallback 持续活跃 (非瞬态), 再评估 NVU_TIER_BUDGET_DSV4F0731_NV
  收缩 (180→120-150) 以让 primary 更快放弃 — 但需先确认这不是牺牲 primary 使用率换取响应速度。
- 若 k1 连续 3 窗口净429>0 且集中 k1, 评估该 key SOCKS5 代理健康。
- 下轮重点: (a) 30min SR 能否站回 ≥90% (b) all_tiers_exhausted 是否回落 ≤5 (c) fallback 是否转静默。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] 数据完整: 30min/6h/3h/24h/per-key/fallback/tier_attempts 均已采集 (tier_attempts 本窗口空)
- [x] 错误深度: 8错全为 ATE(5) + stream_absolute_cap(2) + NVStream_IncompleteRead(1), 429=0, 无 key 劣化
- [x] k0 ATE 集中为轮转起始位伪象, k1 高 cycle 被 429 cooldown 吸收
- [x] fallback 活跃判定为过载震荡残影 (6h SR 88.5% 稳定 + 24h ATE 贴近背景带), 非持续恶化
- [x] 决策数据驱动: NVCF 过载签名无新批量错误, 无参数可干净归因 → NOP, 不扰动配置