# R1223: dsv4f0731_nv40666 NOP — 30min SR=92.86%(42req小样本) 3错为NVCF侧(tier级ATE×2烧满budget + 1×zombie), 24h ATE=111持续背景非尖峰, 0 fallback/0净429/无单key劣化, 无容器杠杆

日期: 2026-08-09 11:20 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DeepSeek V4 Pro via NVCF pexec)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

30min SR=39/42=**92.86%**（首度跌破 95% NOP 阈值，但 42req 为统计小样本）。3 个错误全部为
NVCF 侧事件，无本容器可归因杠杆。24h 逐小时拆解证明 ATE 为持续背景(1-8/hr×24h)，非本窗尖峰。

**证据链**：
1. **all_tiers_exhausted ×2 (avg 174617ms)** — 2 个均烧满整段 ~175s/180s budget 的 tier 级事件
   （5 key 全部尝试后均失败，全键同质 NVCF 过载）。**24h 逐小时拆解 (nv_requests)**：
   ATE 在 24h 内每个整点均有 1-8 例（00:00=3, 01:00=4, 02:00=3, 03:00=3, 前日各时段 1-8），
   **24h ATE=111 持续背景**，非本窗突然恶化。与 R1215-R1222 判定同型：NVCF 侧过载，预算/冷却
   无杠杆（全键同时失败，缩短 budget 只加速失败不影响成功转换）。
2. **zombie_empty_completion ×1 (3285ms, k2)** — 报告 200 但无内容，3285ms 快速检测触发。
   24h 背景 11 例 (0-3/hr)，本窗仅 1 例，**低于 NVU_EMPTY_200_FASTBREAK=3 阈值**（需连续 3 次
   空 200 才触发 fast-fail 整 tier），非配置杠杆。
3. **净 429 = 0** — 请求级 429 计数 0。key_cycle_429s (k0=13, k1=28, k2=1) 为内部轮转吸收计数，
   无请求级 429 失败。
4. **per-key 200 延迟全部健康且负载均匀** — k0=9req/24458ms, k1=7/61965, k2=9/40814,
   k3=8/28441, k4=6/54727 (avg ms)。错误归因 k0(ATE×2)与 k2(zombie)仅循环/起点，无单 key
   持续劣化（k0 延迟 24.5s 为最低，非劣化信号）。
5. **upstream_type 全 pexec (42/42), integrate=0, tier_attempts 空** — 无 pexec/integrate 失衡，
   无 key 间切换异常。finish_reason: tool_calls 25 / stop 14（正常工具调用型负载）。
6. **hm4104 fallback 日志（近 5min）= 无** — 端到端无降级。
7. **3h 逐小时趋势** — 03:00=23/25(92%), 02:00=114/117(97.4%), 01:00=100/104(96.2%),
   00:00=71/77(92.2%)。本窗 92.86% 与 00:00 段 92.2% 同量级，属 NVCF 背景过载波动，非新劣化。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **92.86%** (39/42, 3 err) |
| Avg / P50 / P95 | 45943 / 33790 / 175557 ms |
| 429 | 0 |
| upstream_type | nvcf_pexec 42/42 (100%), integrate 0 |
| finish_reason | tool_calls 25, stop 14 |

**错误分类**：`all_tiers_exhausted: 2 (avg 174617ms)` + `zombie_empty_completion: 1 (3285ms, k2)`

**Per-key 200 延迟**（负载均匀, 无单 key 劣化）:
```
key0|9req|avg24458
key1|7req|avg61965
key2|9req|avg40814
key3|8req|avg28441
key4|6req|avg54727
```

**趋势**:
- 6h: 685 req, SR=95.6% (655 ok / 30 err)
- 3h 逐小时: 03:00=23/25(92%), 02:00=114/117(97.4%), 01:00=100/104(96.2%), 00:00=71/77(92.2%)
- 24h all_tiers_exhausted = **111**（逐小时 1-8/hr 持续背景, 24h 内每整点均有, 非尖峰）

## 决策依据汇总

本窗 92.86% 跌破 NOP 阈值，但样本仅 42req（3 错=7.1%），且 3 错全部为 NVCF 侧背景事件：
- 2× tier 级 ATE 烧满 180s budget（全键同质过载，预算/冷却无杠杆）
- 1× zombie（低于 EMPTY_200_FASTBREAK=3 阈值，单发非连续）

24h 逐小时拆解证明 ATE=1-8/hr 为**持续背景**（R1211-R1222 已连续 ~12 轮 NOP 判定同型），
非本窗恶化。无单 key 劣化、0 净 429、0 fallback、无 pexec/integrate 失衡。按"必须有数据支撑
+ 一次只改一个参数"原则，无任何可归因杠杆，维持当前参数（UPSTREAM_TIMEOUT=45,
TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_DSV4F0731_NV=180, TIER_COOLDOWN_S=90,
KEY_COOLDOWN_S=30, NVU_KEYMGR_429_BASE/MAX=120, EMPTY_200_FASTBREAK=3, PEXEC_TIMEOUT_FASTBREAK=3）。

## 下一步建议

- 若 ATE 背景率在后续窗口**持续高于 ~8/hr** 或单窗 ATE≥3 且 3h 趋势下行，才重新评估是否需
  收紧 TIER_TIMEOUT_BUDGET_S(180) 以缩短单次烧 budget 时间（改善失败请求延迟，但无法转换
  成功——需权衡 NVCF 全键过载峰值期）。
- 若 zombie_empty_completion 单窗 ≥3（命中 EMPTY_200_FASTBREAK 阈值）或连续多轮在**同一 key**
  复发，才考虑该 key 的 SOCKS5 代理检查或 key 冷却调整。
- 本窗 92.86% 属 42req 小样本 + NVCF 背景 ATE 的概率波动，非配置回归，建议 NOP 稳守。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] 数据完整: 30min SR/延迟/错误分布/fallback/6h 趋势/24h ATE 逐小时均已采集
- [x] 错误分类: 2× all_tiers_exhausted (174.6s 烧满 budget) + 1× zombie_empty_completion (3285ms)
- [x] 24h 逐小时拆解: ATE=1-8/hr×24h 持续背景 (24h=111), 非本窗尖峰
- [x] per-key 5 key 负载均匀 (6-9 req/key), 无单 key 持续劣化
- [x] hm4104 近 5min 无 fallback 日志, 端到端无降级
- [x] 决策数据驱动: 3错全为 NVCF 侧背景事件, 无容器杠杆 → NOP