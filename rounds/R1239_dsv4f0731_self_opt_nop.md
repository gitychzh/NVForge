# R1239: dsvf0731_nv40666 self-opt NOP — SR 89.3% 回升, ATE 回落(7→5), 高峰过载越过, 无容器杠杆

> 时间: 2026-08-09 18:16 UTC (R1238 后 ~30min)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
> 状态: **NOP (无参数修改)** — 30min SR 89.3% (50/56), 较 R1238 (86.8%) 回升 2.5pt;
> 5 错误全为 all_tiers_exhausted (tier 级过载烧满), 附加 1× stream_absolute_cap (k2 单个安全帽触发),
> 无净429, 无 key 劣化, upstream 100% pexec 正常, tier_attempts 空;
> hm4104 fallback 活跃 (PRIMARY-FAIL/DISCONNECT 502 + FALLBACK + breaker-SKIP) — 高峰过载震荡残影,
> 但 30min SR 已回 89.3%、24h ATE=131 稳于背景带 (116-132), 越峰迹象明确。

## 结论: NOP (不改任何参数)

## 依据 (30min 窗口, 2026-08-09 ~18:16)

| 指标 | 值 |
|---|---|
| 总量/成功/失败 | 56 / 50 / 6 (SR=89.3%) |
| Avg/P50/P95 | 52978 / 33835 / 181714 ms |
| 净429 | 0 |
| upstream_type | nvcf_pexec 56 req, 50 SR=89.3% (100% pexec, integrate 0) |
| finish_reason | tool_calls 40, stop 9, null 1 |

### 错误分类 (6错: 5×ATE + 1×stream_absolute_cap)
| error_type | n | avg_ms | 判定 |
|---|---|---|---|
| all_tiers_exhausted | 5 | 123098 | tier 级, 5 key 全烧满 TIER_TIMEOUT_BUDGET=180s → NVCF 过载 |
| stream_absolute_cap | 1 | 170685 | k2 单起, NVU_STREAM_ABSOLUTE_CAP_S=150 安全帽兜底 (流超 150s 截断), 非批量 |

### per-key 200 延迟 (count/avg/p95)
- k0: 15 / 40165 / 86999 | k1: 10 / 34318 / 83083 | k2: 9 / 52368 / 125796 | k3: 9 / 41725 / 85886 | k4: 7 / 55439 / 147675
- 各区 34-55s 均衡, k1 avg 最低 (34.3s)/p95 最低 (83.1s) 最健康; k4 高 p95 (147.7s) 仅 7 样本, 波动非劣化。

### per-key 错误细分
- k0: all_tiers_exhausted 5 (123098) | k2: stream_absolute_cap 1 (170685)
- ATE 5 次全为 tier 级 5-key 全失败归属 (k0 伪象), 非 k0 代理故障; stream_absolute_cap 为 k2 单起安全帽兜底。

### key_cycle_429s (内部循环计数, 非净错误)
- k0=16, k1=39, k2=1 (k3/k4 无)
- k1 持续偏高(39)但 net 429=0, key manager 已吸收 → cooldown 工作正常, 无需调 KEY_COOLDOWN。

### tier_attempts
- **空** (本窗口无独立 key 切换 attempt 记录) — 与 ATE 全烧满 budget 一致, 无 key 级切换模式可归因。

### hm4104 fallback (最近5min) — ⚠ 仍活跃但 SR 已回升
- 近 5min 5 条: 3× FALLBACK-STREAM (primary→ms_gw 流式切) + 2× PRIMARY-BREAKER-SKIP-STREAM。
- 与 R1238 同类过载震荡, 但本轮 30min SR 89.3% 已回升 (R1238=86.8%), ATE 回落 7→5, 越峰迹象明确。

### 趋势
- 6h: 618/543/75 = **87.9% SR**, 0 429
- 3h逐小时: 09h=68/77(88.3%) / 08h=101/123(82.1%) / 07h=63/77(81.8%) / 06h=26/31(83.9%)
  - 09h 已回 88.3% (R1238=86.5%), 08h 峰值残影 82.1% 仍在但后段改善 — 高峰过载越过。
- 24h all_tiers_exhausted=131 (R1238=132, 稳于 116-132 背景带, 未恶化)

## 为何不改
1. **5 个 ATE 全为 all_tiers_exhausted 签名** (avg ~123s = 5 key 全烧满 180s budget): NVCF 上游过载烧满,
   非容器 key/超时/冷却参数可治愈。R1235-R1239 同签名, 无新批量错误类型出现。
2. **stream_absolute_cap 仅 1 起 (k2, 170s)**: 为 NVU_STREAM_ABSOLUTE_CAP_S=150 安全帽兜底 (流超 150s 截断),
   防止单流无限挂起。单起瞬态, 非批量 (R1238 无此类型), 无调整动机。
3. **R1233/R1234 已论证收缩 NVU_TIER_BUDGET_DSV4F0731_NV 非正解**: 只让 primary 更快放弃并切 fallback,
   **不减少 fallback 次数**, 反伤 primary 使用率。当前 ATE 5 次为过载烧满且已回落, 无收缩动机。
4. **净 429=0**, key_cycle_429s (k1=39) 被 key manager 完全吸收 → KEY_COOLDOWN/429 cooldown 工作正常, 无需调整。
5. **per-key 无持续劣化**: k0-k4 avg 34-55s 均衡健康, 错误全归 tier 级 ATE (k0 伪象) + stream_absolute_cap 单起,
   upstream 100% pexec 运行正常, 无需调 integrate 路由。
6. **fallback 活跃是高峰过载震荡残影**: 30min SR 已回 89.3% (R1238=86.8%), 6h SR 87.9% 稳定、24h ATE=131 稳于背景带、
   30min SR 未达 <80% 崩盘阈值。越峰迹象明确, 无需任何本容器干预。

## 当前状态 (30min)
- 30min SR: **89.3%** (50/56), 较 R1238 (86.8%) 回升 2.5pt / **6h SR: 87.9%** (543/618)
- Avg/P50/P95: 52978 / 33835 / 181714 ms — per-key avg 34-55s 均在典型 NVCF 延迟带
- 错误 (30min): `all_tiers_exhausted` 5 (~123s, tier级过载烧满) + `stream_absolute_cap` 1 (k2 单起安全帽)
- 429: 0
- upstream: pexec 56 (200=50, SR=89.3%), integrate 0
- fallback: **活跃** (近 5min 3× FALLBACK-STREAM + 2× breaker-SKIP, 过载震荡残影)

## 上次修改效果 (R1221 UPSTREAM_TIMEOUT=45, 持续生效)
- 无 NVCFPexecTimeout 集中爆发; 本窗口错误纯为 ATE (过载烧满) + stream_absolute_cap 单起, 无超时配置问题。
- 30min SR 由 R1238 的 86.8% 升至 89.3% (回升 2.5pt), 6h SR 87.8%→87.9% 持平 — 越峰回升, 无配置回归。

## 下一步建议
- 持续观察越峰: 若 1-2 轮 30min SR 稳定 ≥90% 且 hm4104 fallback 转静默、24h ATE 稳于 ≤130, 则确认高峰已越过。
- 若 SR 再跌 <85% 且 fallback 持续活跃 (非瞬态), 再评估 NVU_TIER_BUDGET_DSV4F0731_NV
  收缩 (180→120-150) 以让 primary 更快放弃 — 但需先确认这不是牺牲 primary 使用率换取响应速度。
- 若 k1 连续 3 窗口净429>0 且集中 k1, 评估该 key SOCKS5 代理健康。
- 下轮重点: (a) 30min SR 是否升至 ≥90%, (b) all_tiers_exhausted 是否回落 ≤3, (c) fallback 是否转静默。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] 数据完整: 30min/6h/3h/24h/per-key/fallback/tier_attempts 均已采集 (tier_attempts 本窗口空)
- [x] 错误深度: 5错全为 all_tiers_exhausted (~123s 烧满 budget) + stream_absolute_cap 1 (k2 安全帽), 429=0, 无 key 劣化
- [x] k0 ATE 集中为轮转起始位伪象, k1 高 cycle 被 429 cooldown 吸收
- [x] fallback 活跃判定为高峰过载震荡残影 (30min SR 回升 + 24h ATE 稳于背景带), 越峰迹象明确
- [x] 决策数据驱动: NVCF 过载签名无新批量错误, 无参数可干净归因 → NOP, 不扰动配置