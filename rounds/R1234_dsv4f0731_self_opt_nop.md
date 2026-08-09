# R1234: dsv4f0731_nv40666 self-opt NOP — 30min SR回升至92.7%, 3错全为NVCF过载ATE烧满budget, hm4104 fallback随ATE burst波动(非容器可调)

> 时间: 2026-08-09 16:06 UTC (R1233 后 ~1h)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
> 状态: **NOP (无参数修改)** — 30min SR 92.7% (38/41), 较 R1233 (83.8%) 回升并超越 6h 均值;
> 3 错误全为 `all_tiers_exhausted` (tier 级 budget 烧满 ~185s = NVCF 过载烧完 5 key);
> hm4104 fallback 重新活跃 (近5min 多次 PRIMARY-FAIL 502@180s + breaker SKIP), 但为 ATE 过载瞬态的直接后果

## 结论: NOP (不改任何参数)

## 依据 (30min 窗口, 2026-08-09 ~16:06)

| 指标 | 值 |
|---|---|
| 总量/成功/失败 | 41 / 38 / 3 (SR=92.7%) |
| Avg/P50/P95 | 60215 / 34930 / 180044 ms |
| 净429 | 0 |
| upstream_type | nvcf_pexec 40 req, 38 SR=95%; 1 null (ATE 上报 null key) |
| finish_reason | tool_calls 31, stop 6, null 1 |

### 错误分类 (3错, 全为 tier 级 ATE = NVCF 过载烧满 budget)
| error_type | n | avg_ms |
|---|---|---|
| all_tiers_exhausted | 3 | 185290 |

### per-key 200 延迟 (count/avg/p95)
- k0: 15 / 53023 / 124048 | k1: 7 / 57188 / 154111 | k2: 8 / 49508 / 119795 | k3: 6 / 47457 / 83566 | k4: 2 / 18240 / 31798
- 各区 47-57s 均衡, k0 负载最重 (15 req) 但 avg 低, 无单 key 代理劣化。

### per-key 错误细分
- ATE: k0×2 (180046ms≈budget 烧满) + null×1 (195777ms)
- k0 ATE 集中为轮转起始位伪象 (tier 级 5-key 全失败归属), 非 k0 代理故障。

### key_cycle_429s (内部循环计数, 非净错误)
- k0=10, k1=29, k2=3 (k3/k4=0)
- k1 持续偏高(29)但 key manager 已吸收 (净429=0), 与 R1224-R1233 模式一致 → cooldown 工作正常。

### hm4104 fallback (最近5min) — ⚠ 重新活跃
- **多次 fallback**: 1× `PRIMARY-FAIL-STREAM` (nv_gw 502 after 180053ms≈budget 烧满) + 2× `PRIMARY-BREAKER-SKIP-STREAM` (circuit OPEN 直走 fallback) + 2× `FALLBACK-STREAM` (切 ms_gw)
- 较 R1233 (fallback 归零) 再次活跃, 但机制清晰: **NVCF 过载 → 请求烧满 180s budget → nv_gw 502 → 适配器切 ms_gw, 随后 breaker 打开短暂直走 fallback**。是 ATE 的直接下游效应, 非容器参数不健康。

### 趋势
- 6h: 522/573 = **91.1% SR**, 51 err, 0 429 (与 R1233 6h 91.4% 基本持平)
- 3h逐小时: 08h=8/9 / 07h=63/77(81.8%) / 06h=100/111(90.1%) / 05h=76/82(92.7%)
  → 07:00 一小时 81.8% 为 ATE burst 低点, 前后 90-93% 健康, 过载瞬态。
- 24h all_tiers_exhausted=121 (与 R1233 持平, 稳于 116-122 背景带, 无恶化)

## 为何不改
1. **3 个错误 100% 为 `all_tiers_exhausted`** (~185s = NVCF 过载烧满 TIER_TIMEOUT_BUDGET=180s, 5 key 全失败)。这是 NVCF 侧上游过载, 非容器 key/超时/冷却参数可治愈。6h SR=91.1% 健康, 30min 92.7% 已回升。
2. **R1233 已论证收缩 NVU_TIER_BUDGET_DSV4F0731_NV(180→120) 非正解**: 只让 primary 更快放弃并切 fallback, **不减少 fallback 次数** (当前 fallback 由 ATE 过载驱动, 与 budget 长度无关), 反伤 primary 使用率。当前 30min SR 92.7% 高于 6h 均值, 无收缩动机。
3. **净 429=0** → KEY_COOLDOWN/429 cooldown 已正确吸收 k1 高 cycle 计数 (29), 无需调 KEY_COOLDOWN。
4. **per-key 无持续劣化**: k0 ATE 集中为轮转起始位伪象 (avg_ok 53s 全 key 正常), k1 无净失败 (429 被吸收), 各 key 47-57s 均衡。upstream 100% pexec 运行正常, 无需调 integrate 路由。
5. **fallback 活跃是 ATE 过载的下游瞬态**: 502@180s 恰为 budget 烧满所产生的 NVCF 502, breaker SKIP 是适配器对过载的正常保护, 主链路 SR 本身健康 (92.7%)。调整本容器参数无法消除 NVCF 过载, 只能更快触发 fallback (副作用)。

当前 env 维持: UPSTREAM_TIMEOUT=45, TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_DSV4F0731_NV=180,
KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90, NVU_KEYMGR_429_BASE/MAX_COOLDOWN=120,
NVU_KEYMGR_CONN_BASE=30/MAX=60/FAIL_THRESHOLD=3/LONG=120, NVU_PEXEC_TIMEOUT_FASTBREAK=3,
NVU_EMPTY_200_FASTBREAK=3。**无改动。**

## 当前状态 (30min)
- 30min SR: **92.7%** (38/41) / **6h SR: 91.1%** (522/573)
- Avg/P50/P95: 60215ms / 34930ms / 180044ms
- 错误 (30min): `all_tiers_exhausted` 3 (185s, tier 级 NVCF 过载)
- 429: 0
- upstream: pexec 40 (200=38, SR=95%), integrate 0
- fallback: **活跃** (近 5min 1× PRIMARY-FAIL 502@180s + 2× breaker SKIP + 2× FALLBACK-STREAM) — ATE 过载瞬态

## 上次修改效果 (R1221 UPSTREAM_TIMEOUT=45, 持续生效)
- 无 NVCFPexecTimeout 集中爆发, 无超时相关链错误, 延迟稳定。本窗口错误全为 NVCF 过载 ATE 残余,
  非超时配置问题。fallback 随 ATE burst 周期性波动 (R1233 归零 → 本轮活跃), 主链路健康。

## 下一步建议
- 区分 fallback 是"短暂 ATE burst 瞬态"还是"持续恶化": 若未来 2-3 轮 fallback 持续 >5 次/5min
  且 30min SR 跌破 85%, 则 NVCF 过载为持续性, 需从上游/代理层 (NVCF 侧) 治理, 而非本容器参数。
- 持续观察 all_tiers_exhausted 24h 背景 (当前 121 稳定): 若 >150 或 3h SR 高峰时段跌破 80% 再评估。
- 关注 k1 持续高 key_cycle_429s(29) 是否累积为实际净失败; 若连续 3 窗口净429>0 且集中 k1, 评估该 key SOCKS5 代理健康。
- 下轮重点: (a) 30min SR 是否保持 ≥90%, (b) all_tiers_exhausted 是否 ≤3, (c) hm4104 fallback 是否随 NVCF 过载消退而回落。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] 数据完整: 30min/6h/3h/24h/per-key/fallback 均已采集
- [x] 错误深度: all_tiers_exhausted 3 (185s=budget 烧满), 429=0, NVCF 过载残余
- [x] k0 错误集中 (2/3 ATE, 轮转起始位伪象), k1 高 cycle 被 429 cooldown 吸收, 无 key 劣化
- [x] fallback 活跃判定为 ATE 下游客 (502@180s=budget 烧满), 非容器参数不可调
- [x] 决策数据驱动: NVCF 过载瞬态, SR 92.7% 健康, 无参数可干净归因 → NOP, 不扰动配置