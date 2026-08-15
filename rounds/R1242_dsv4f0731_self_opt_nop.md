# R1242: dsvf0731_nv40666 self-opt NOP — SR 回升 93.8%, fallback 转静默, 24h ATE 稳于 138, 无容器杠��

> 时间: 2026-08-09 18:48 UTC (R1241 后 ~26min)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
> 状态: **NOP (无参数修改)** — 30min SR **93.8%** (76/81), 较 R1241 (89.7%) **回升 4.1pt, 站回 ≥90%**;
> 5 错误: 4× all_tiers_exhausted (tier 级过载烧满 budget) + 1× client_gone_during_flush (流冲刷期客户端断开),
> 无净 429, 无 key 劣化, upstream 100% pexec 正常, tier_attempts 空;
> **hm4104 fallback 转静默** (近 5min 无 fallback 日志) — 高峰过载震荡退去信号, 6h SR 88.2% 持稳,
> 24h ATE=138 完全停在 R1241 背景带 (116-138), 未继续累积。

## 结论: NOP (不改任何参数)

## 依据 (30min 窗口, 2026-08-09 ~18:48)

| 指标 | 值 |
|---|---|
| 总量/成功/失败 | 81 / 76 / 5 (SR=93.8%) |
| Avg/P50/P95 | 61616 / 47330 / 180059 ms |
| 净429 | 0 |
| upstream_type | nvcf_pexec 81 req, 76 SR=93.8% (100% pexec, integrate 0) |
| finish_reason | tool_calls 56, stop 17, null 3 |

### 错误分类 (5错: 4×ATE + 1×client_gone_during_flush)
| error_type | n | avg_ms | 判定 |
|---|---|---|---|
| all_tiers_exhausted | 4 | 148703 | tier 级, 5 key 全烧满 TIER_TIMEOUT_BUDGET=180s → NVCF 过载残余 |
| client_gone_during_flush | 1 | 268142 | 流冲刷期客户端断开 (上游已开始回包但连接断), 单起 |

### per-key 200 延迟 (count/avg/p95)
- k0: 23 / 54339 / 132517 | k1: 18 / 48733 / 93295 | k2: 15 / 63488 / 166204 | k3: 17 / 39540 / 74796 | k4: 3 / 125498 / 185505
- k0-k3 avg 39-63s 均衡健康 (典型 NVCF 延迟带); k4 avg 125s/p95 185s 偏高但**仅 3 请求** (小样本, 负载轻),
  且无对应错误, 非持续劣化, 不构成调整 integrate 路由的动机。

### per-key 错误细分
- k0: all_tiers_exhausted 4 | k3: client_gone_during_flush 1
- ATE 4 次为 tier 级 5-key 全失败归属 (k0 轮转起始位伪象), 非 k0 代理故障; client_gone 单起瞬态。

### key_cycle_429s (内部循环计数, 非净错误)
- k0=26, k1=53, k3=2
- k1 持续偏高(53)但 net 429=0, key manager 已吸收 → cooldown 工作正常, 无需调 KEY_COOLDOWN。

### tier_attempts
- **空** (本窗口无独立 key 切换 attempt 记录) — 与 ATE 全烧满 budget 一致, 无 key 级切换模式可归因。

### hm4104 fallback (最近5min) — 转静默
- **无 fallback 日志** (R1241 尚有 5 条: 502@180s + FALLBACK-STREAM×3 + breaker-SKIP×2)。
- 主链路 nv_gw 可用性恢复信号 — 高峰过载震荡退去, 与 SR 回升 93.8% 互证。

### 趋势
- 6h: 695/613/82 = **88.2% SR**, 0 429
- 3h逐小时: 10h=130/118(90.8%) / 09h=140/125(89.3%) / 08h=123/101(82.1%) / 07h=19/18(94.7%)
  - 08h→10h SR 回升 (82.1%→89.3%→90.8%), 当前窗口 93.8% 进一步走高 — 过载退潮、SR 站回 ≥90%。
- 24h all_tiers_exhausted=138 (与 R1241 完全持平 — 本窗口 4 次 ATE 后 24h 计数未继续累积, 背景带压制)

## 为何不改
1. **SR 站回 ≥90% (93.8%) 且 fallback 转静默** — 与 R1241 到本轮的回升轨迹一致, 高峰过载震荡正退去。
   5 个错误全部为 NVCF 侧过载/流事件签名 (4× ATE 烧满 budget + 1× client_gone), 非容器 key/超时/冷却参数可治愈。
2. **R1233/R1234 已论证收缩 NVU_TIER_BUDGET_DSV4F0731_NV 非正解**: 只让 primary 更快放弃并切 fallback,
   反伤 primary 使用率。当前 4 次 ATE 为过载燃烧, 且 24h ATE 已停止累积, 无收缩动机。
3. **净 429=0**, key_cycle_429s (k1=53) 被 key manager 完全吸收 → KEY_COOLDOWN/429 cooldown 工作正常, 无需调整。
4. **per-key 无持续劣化**: k0-k3 avg 39-63s 均衡健康, k4 仅 3 请求且无错误 (小样本延迟偏高非劣化) —
   不构成调 integrate 路由或 key 分配的依据; upstream 100% pexec 运行正常。
5. **24h ATE=138 完全持平 R1241** (未继续累积) — 过载在 30min 窗口的 4 次 ATE 为该窗口瞬时, 未拉高 24h 背景带,
   判定过载震荡退去中, 无需任何本容器干预。

## 当前状态 (30min)
- 30min SR: **93.8%** (76/81), 较 R1241 (89.7%) **回升 4.1pt, 站回 ≥90%** / **6h SR: 88.2%** (613/695)
- Avg/P50/P95: 61616 / 47330 / 180059 ms — per-key avg 39-63s (k0-k3) 均在典型 NVCF 延迟带
- 错误 (30min): `all_tiers_exhausted` 4 (~148s, tier级过载烧满) + `client_gone_during_flush` 1 (单起)
- 429: 0
- upstream: pexec 81 (200=76, SR=93.8%), integrate 0
- fallback: **静默** (近 5min 无 fallback 日志, R1241 尚有 5 条)

## 上次修改效果 (R1241 NOP → 本轮)
- **SR 回升**: 30min 89.7% → **93.8%** (站回 ≥90%); 6h SR 88.5% → 88.2% 持平 — 过载震荡退去, 无配置回归。
- **fallback 转静默**: R1241 活跃 (5 条) → 本轮 **无 fallback** — 主链路 nv_gw 可用性恢复。
- **错误收窄**: R1241 5×ATE + 2×stream_absolute_cap + 1×IncompleteRead → 本轮 4×ATE + 1×client_gone —
  流截断形态消失, 仅剩 tier 级过载残余。
- **24h ATE**: 138 → **138** (持平, 未继续累积) — 过载背景带受压制。

## 下一步建议
- 持续观察高峰过载震荡: 若再 1-2 轮 30min SR 稳定 ≥90% 且 hm4104 fallback 保持静默、24h ATE 稳于 ≤140,
  则确认高峰已越过, 容器保持健康 NOP。
- 若 SR 再跌 <85% 且 fallback 重新活跃 (非瞬态), 再评估 NVU_TIER_BUDGET_DSV4F0731_NV
  收缩 (180→120-150) 以让 primary 更快放弃 — 但需先确认这不是牺牲 primary 使用率换取响应速度。
- 若 k1 连续 3 窗口净429>0 且集中 k1, 评估该 key SOCKS5 代理健康。
- 下轮重点: (a) SR 能否站回/维持 ≥90% (b) fallback 是否保持静默 (c) 24h ATE 是否 ≤140。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] 数据完整: 30min/6h/3h/24h/per-key/fallback/tier_attempts 均已采集 (tier_attempts 本窗口空)
- [x] 错误深度: 5错全为 ATE(4) + client_gone_during_flush(1), 429=0, 无 key 劣化
- [x] k0 ATE 集中为轮转起始位伪象, k1 高 cycle 被 429 cooldown 吸收; k4 低样本延迟偏高非劣化
- [x] fallback 转静默 (R1241 5条 → 本轮 0), 与 SR 回升 93.8% 互证
- [x] 决策数据驱动: SR 站回 ≥90% + fallback 静默 + 24h ATE 持平, 过载退去, 无参数可干净归因 → NOP, 不扰动配置