# R1238: dsvf0731_nv40666 self-opt NOP — SR 86.8% 持平, 7错全为ATE(NVCF过载), fallback再活跃(过载震荡), 无容器杠杆

> 时间: 2026-08-09 17:46 UTC (R1237 后 ~30min)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
> 状态: **NOP (无参数修改)** — 30min SR 86.8% (46/53), 与 R1237 (86.8%) 完全持平;
> 7 错误**全部**为 all_tiers_exhausted (tier 级, 每起烧满 TIER_TIMEOUT_BUDGET=180s), 无净429,
> 无 key 劣化, upstream 100% pexec 正常, tier_attempts 空 (无 key 切换模式记录);
> hm4104 fallback 重新活跃 (PRIMARY-FAIL-STREAM 502@180s + FALLBACK-STREAM) — 与 R1237 同类
> 高峰过载震荡 (08h 峰值残影), 非持续性恶化 (6h SR 87.8%, 24h ATE=132 稳于背景带)。

## 结论: NOP (不改任何参数)

## 依据 (30min 窗口, 2026-08-09 ~17:46)

| 指标 | 值 |
|---|---|
| 总量/成功/失败 | 53 / 46 / 7 (SR=86.8%) |
| Avg/P50/P95 | 62346 / 39574 / 221479 ms |
| 净429 | 0 |
| upstream_type | nvcf_pexec 52 req, 46 SR=88.5%; 1 null (ATE 上报 null key) |
| finish_reason | tool_calls 37, stop 5, null 4 |

### 错误分类 (7错, 全为 all_tiers_exhausted)
| error_type | n | avg_ms | 判定 |
|---|---|---|---|
| all_tiers_exhausted | 7 | 164991 | tier 级, 5 key 全烧满 TIER_TIMEOUT_BUDGET=180s → NVCF 过载 |

### per-key 200 延迟 (count/avg/p95)
- k0: 17 / 43094 / 72538 | k1: 11 / 36076 / 70251 | k2: 4 / 57649 / 131975 | k3: 7 / 39792 / 90431 | k4: 7 / 72971 / 174649
- 各区 36-73s 均衡, k0 负载最重 (17) 但 SR 健康/k1 avg 最低 (36s); k2/k4 高 p95 (132s/175s) 仅 4-7 样本, 波动非劣化。

### per-key 错误细分
- k0: all_tiers_exhausted 6 (148768) | null: ATE 1 (262332)
- ATE 7 次全为 tier 级 5-key 全失败归属 (k0/null 伪象), 非 k0 代理故障。

### key_cycle_429s (内部循环计数, 非净错误)
- k0=23, k1=30 (k2/k3/k4 无)
- k1 持续偏高(30)但 net 429=0, key manager 已吸收 → cooldown 工作正常, 无需调 KEY_COOLDOWN。

### tier_attempts
- **空** (本窗口无独立 key 切换 attempt 记录) — 与 ATE 全烧满 budget 一致, 无 key 级切换模式可归因。

### hm4104 fallback (最近5min) — ⚠ 重新活跃
- 2 条: `PRIMARY-FAIL-STREAM` (nv_gw 流式 502 after 180043ms ≈ budget 烧满) + `FALLBACK-STREAM` (切 ms_gw)。
- 与 R1237 同类: 高峰过载震荡 (ATE 烧满 → 502 → 切 fallback), 非容器参数不健康。

### 趋势
- 6h: 605/531/74 = **87.8% SR**, 0 429
- 3h逐小时: 09h=45/52(86.5%) / 08h=101/123(82.1%) / 07h=63/77(81.8%) / 06h=47/55(85.5%)
  - 08h 仍 82.1% (峰值残影), 但 09h 已回到 86.5% — 高峰过载震荡在 85% 上下, 未明显越过也未崩。
- 24h all_tiers_exhausted=132 (R1237=130, R1236=129, 稳于 116-132 背景带, 略升但未恶化)

## 为何不改
1. **7 个错误全部呈现 all_tiers_exhausted 签名** (avg ~165s = 5 key 全烧满 180s budget):
   这是 NVCF 上游过载, 非容器 key/超时/冷却参数可治愈。R1235-R1237 同签名, 无新错误类型出现。
2. **R1233/R1234 已论证收缩 NVU_TIER_BUDGET_DSV4F0731_NV 非正解**: 只让 primary 更快放弃并切 fallback,
   **不减少 fallback 次数** (fallback 由 ATE 过载驱动), 反伤 primary 使用率。当前 ATE 7 次为过载烧满, 无收缩动机。
3. **净 429=0**, key_cycle_429s (k1=30) 被 key manager 完全吸收 → KEY_COOLDOWN/429 cooldown 工作正常, 无需调整。
4. **per-key 无持续劣化**: k0 负载最重 (17) 但 SR 健康, 错误全归 tier 级 ATE (k0/null 伪象), k2/k4 高 p95 仅小数样本,
   upstream 100% pexec 运行正常, 无需调 integrate 路由。
5. **fallback 活跃是过载震荡而非持续恶化**: 与 R1237 同类 (702@180s=budget 烧满), 但 6h SR 87.8% 稳定、24h ATE=132 稳于背景带、
   30min SR 86.8% 未达 <80% 崩盘阈值。判定为高峰瞬态震荡, 无需任何本容器干预。

## 当前状态 (30min)
- 30min SR: **86.8%** (46/53) / **6h SR: 87.8%** (531/605)
- Avg/P50/P95: 62346 / 39574 / 221479 ms — per-key avg 36-73s 均在典型 NVCF 延迟带
- 错误 (30min): `all_tiers_exhausted` 7 (~165s, tier级过载烧满)
- 429: 0
- upstream: pexec 52 (200=46, SR=88.5%), integrate 0
- fallback: **活跃** (近 5min 1× PRIMARY-FAIL 502@180s + 1× FALLBACK-STREAM, 与 R1237 同类过载震荡)

## 上次修改效果 (R1221 UPSTREAM_TIMEOUT=45, 持续生效)
- 无 NVCFPexecTimeout 集中爆发; 本窗口错误纯为 ATE (过载烧满), 无超时配置问题。
- 30min SR 由 R1237 的 86.8% 持平 (46/53 = 46/53), 6h SR 88.0%→87.8% 基本持平 — 无配置回归, 为过载震荡。

## 下一步建议
- 持续观察 06-09h 高峰过载震荡: 若越峰后 (10h 起) 1-2 轮 30min SR 稳定 ≥90% 且 hm4104 fallback 转静默、
  24h ATE 稳于 ≤135, 则确认高峰已越过, 容器保持健康 NOP。
- 若越峰后 3h SR 仍 <85% 且 fallback 持续活跃 (非瞬态), 再评估 NVU_TIER_BUDGET_DSV4F0731_NV
  收缩 (180→120-150) 以让 primary 更快放弃、hm4104 更快切 ms_gw — 但需先确认这不是牺牲 primary 使用率换取响应速度。
- 若 k1 连续 3 窗口净429>0 且集中 k1, 评估该 key SOCKS5 代理健康。
- 下轮重点: (a) 越峰后 (10h+) 30min SR 是否升至 ≥90%, (b) all_tiers_exhausted 是否回落 ≤5, (c) fallback 是否转静默。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] 数据完整: 30min/6h/3h/24h/per-key/fallback/tier_attempts 均已采集 (tier_attempts 本窗口空)
- [x] 错误深度: 7错全为 all_tiers_exhausted (~165s 烧满 budget), 429=0, 无 key 劣化
- [x] k0 ATE 集中为轮转起始位伪象, k1 高 cycle 被 429 cooldown 吸收
- [x] fallback 活跃判定为高峰过载震荡 (6h SR 稳定 + 24h ATE 稳于背景带), 非持续恶化
- [x] 决策数据驱动: NVCF 过载签名无新错误类型, 无参数可干净归因 → NOP, 不扰动配置