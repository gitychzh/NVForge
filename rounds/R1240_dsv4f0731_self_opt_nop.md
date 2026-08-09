# R1240: dsvf0731_nv40666 self-opt NOP — SR 92.5% (4轮最高), 越峰明确, 6错全为过载/安全帽/客户端, 无容器杠杆

> 时间: 2026-08-09 18:15 UTC (R1239 后 ~30min)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
> 状态: **NOP (无参数修改)** — 30min SR 92.5% (74/80), 为 R1237-R1240 四轮最高
> (R1237=86.8% / R1238=86.8% / R1239=89.3% / **R1240=92.5%**), 越峰明确;
> 6 错误全为长时耗 (146-176s): 3× all_tiers_exhausted (tier 过载烧满) + 2× stream_absolute_cap
> (NVU_STREAM_ABSOLUTE_CAP_S=150 安全帽兜底) + 1× client_gone_during_flush (客户端断开, 非上游);
> 无净429, 无 key 劣化, upstream 100% pexec 正常, tier_attempts 空;
> hm4104 fallback 仍有残影 (content_filter zombie + primary FAIL 切 ms_gw), 3h SR 单调回升 → 高峰过载已越过。

## 结论: NOP (不改任何参数)

## 依据 (30min 窗口, 2026-08-09 ~18:02)

| 指标 | 值 |
|---|---|
| 总量/成功/失败 | 80 / 74 / 6 (SR=92.5%) |
| Avg/P50/P95 | 57691 / 37432 / 180062 ms |
| 净429 | 0 |
| upstream_type | nvcf_pexec 80 req, 74 SR=92.5% (100% pexec, integrate 0) |
| finish_reason | tool_calls 59, stop 13, null 2 |

### 错误分类 (6错: 3×ATE + 2×stream_absolute_cap + 1×client_gone_during_flush)
| error_type | n | avg_ms | 判定 |
|---|---|---|---|
| all_tiers_exhausted | 3 | 146681 | tier 级, 5 key 全烧满 budget → NVCF 过载 |
| stream_absolute_cap | 2 | 169915 | NVU_STREAM_ABSOLUTE_CAP_S=150 安全帽兜底 (流超 150s 截断), 非批量 |
| client_gone_during_flush | 1 | 176070 | 客户端在 flush 时断开, 非上游故障 |

### per-key 200 延迟 (count/avg/p95)
- k0: 26 / 50522 / 148345 | k1: 12 / 55090 / 116136 | k2: 13 / 48001 / 109802 | k3: 16 / 50004 / 129678 | k4: 7 / 37231 / 75878
- 各区 37-55s 均衡健康, k4 avg 最低 (37.2s)/p95 最低 (75.9s) 最健康; k0 负载最重 (26) 但 SR 健康, 无劣化。

### per-key 错误细分
- k0: all_tiers_exhausted 3 + stream_absolute_cap 2 | k1: client_gone_during_flush 1
- ATE 3 次为 tier 级 5-key 全失败归属 (k0 伪象), 非 k0 代理故障; stream_absolute_cap 为 k0 单流安全帽兜底。

### key_cycle_429s (内部循环计数, 非净错误)
- k0=12, k1=65, k2=1, k4=2 (k3 无)
- k1 持续偏高(65)但 net 429=0, key manager 已吸收 → cooldown 工作正常, 无需调 KEY_COOLDOWN。

### tier_attempts
- **空** (本窗口无独立 key 切换 attempt 记录) — 与 ATE 全烧满 budget 一致, 无 key 级切换模式可归因。

### hm4104 fallback (最近5min) — 残影但 3h SR 单调回升
- 3 条: `CONTENT_FILTER_ZOMBIE` (primary 流中 content_filter, R840 zombie) 切 ms_gw
  + `PRIMARY-ZOMBIE-FALLBACK` + `FALLBACK-STREAM` (primary→ms_gw 流式切)。
- 与 R1238/R1239 同类过载震荡残影, 但本轮 30min SR 92.5% 为四轮最高, 越峰证据更强。

### 趋势
- 6h: 656/583/73 = **88.9% SR**, 0 429
- 3h逐小时: 10h=4/4(100%) / 09h=140/125(89.3%) / 08h=123/101(82.1%) / 07h=72/58(80.6%)
  - **07h→10h SR 单调回升 (80.6%→82.1%→89.3%→100%)**, 高峰过载已明确越过。
- 24h all_tiers_exhausted=134 (R1239=131, R1238=132 — 略升 2-3, 仍贴近背景带 116-132, 未恶化)

## 为何不改
1. **30min SR 92.5% 为四轮最高** (R1237=86.8%→R1240=92.5%), 3h 逐小时 SR 单调回升 (80.6%→100%),
   高峰过载已明确越过, 无需任何容器干预。
2. **3× ATE 全为 tier 级过载烧满签名** (avg ~147s = 5 key 全烧满 budget): NVCF 上游过载, 非容器
   key/超时/冷却参数可治愈。R1235-R1240 同签名, 无新批量错误类型出现。
3. **stream_absolute_cap 仅 2 起 (k0, ~170s)**: 为 NVU_STREAM_ABSOLUTE_CAP_S=150 安全帽兜底
   (流超 150s 截断), 防止单流无限挂起。2/80 废然瞬态, 非批量 (R1239 仅 1 起), 无调整动机。
4. **client_gone_during_flush 仅 1 起**: 客户端在 flush 阶段断开, 属客户端侧行为, 非上游故障, 无配置杠杆。
5. **R1233/R1234 已论证收缩 NVU_TIER_BUDGET_DSV4F0731_NV 非正解**: 只让 primary 更快放弃并切 fallback,
   **不减少 fallback 次数**, 反伤 primary 使用率。当前 ATE 3 次 (四轮最低) 且已回落, 无收缩动机。
6. **净 429=0**, key_cycle_429s (k1=65) 被 key manager 完全吸收 → KEY_COOLDOWN/429 cooldown 工作正常, 无需调整。
7. **per-key 无持续劣化**: k0-k4 avg 37-55s 均衡健康, 错误全归 tier 级 ATE (k0 伪象) + stream_absolute_cap 单起
   + client 断开, upstream 100% pexec 运行正常, 无需调 integrate 路由。

## 当前状态 (30min)
- 30min SR: **92.5%** (74/80), 四轮最高 / **6h SR: 88.9%** (583/656)
- Avg/P50/P95: 57691 / 37432 / 180062 ms — per-key avg 37-55s 均在典型 NVCF 延迟带
- 错误 (30min): `all_tiers_exhausted` 3 (~147s, tier级过载烧满) + `stream_absolute_cap` 2 (安全帽)
  + `client_gone_during_flush` 1 (客户端断开)
- 429: 0
- upstream: pexec 80 (200=74, SR=92.5%), integrate 0
- fallback: **残影** (近 5min 3× zombie/FAIL→ms_gw, 过载震荡残影, 3h SR 单调回升)

## 上次修改效果 (R1221 UPSTREAM_TIMEOUT=45, 持续生效)
- 无 NVCFPexecTimeout 集中爆发; 本窗口错误纯为 ATE (过载烧满) + stream_absolute_cap (安全帽) + client 断开,
  无超时配置问题。
- 30min SR 由 R1239 的 89.3% 升至 92.5% (四轮最高), 6h SR 87.9%→88.9% 回升 1pt — 越峰持续, 无配置回归。

## 下一步建议
- 持续观察越峰后稳态: 若 1-2 轮 30min SR 稳定 ≥90% 且 hm4104 fallback 转静默、24h ATE 稳于 ≤130,
  则确认高峰已越过, 容器保持健康 NOP。
- 若 SR 维持 ≥92% 且 24h ATE 回落, 可评估是否仍有收缩 stream cap 或整合参数的动机 (当前无)。
- 若 k1 连续 3 窗口净429>0 且集中 k1, 评估该 key SOCKS5 代理健康。
- 下轮重点: (a) 30min SR 能否站稳 ≥90%, (b) all_tiers_exhausted 是否回落 ≤3, (c) fallback 是否转静默。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] 数据完整: 30min/6h/3h/24h/per-key/fallback/tier_attempts 均已采集 (tier_attempts 本窗口空)
- [x] 错误深度: 6错全为 ATE(3) + stream_absolute_cap(2) + client_gone_during_flush(1), 429=0, 无 key 劣化
- [x] k0 ATE 集中为轮转起始位伪象, k1 高 cycle 被 429 cooldown 吸收
- [x] fallback 活跃判定为过载越峰残影 (30min SR 四轮最高 + 3h 单调回升 + 24h ATE 贴近背景带)
- [x] 决策数据驱动: SR 92.5% 健康, NVCF 过载签名无新错误类型, 无参数可干净归因 → NOP, 不扰动配置