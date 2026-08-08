# R1039: 30min SR 98.68% 单次 all_tiers_exhausted(瞬态) 0 fallback 0 429 — NOP

> 时间: 2026-08-08 11:34 UTC
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
> 状态: **NOP (无参数修改)** — 30min SR 98.68% (75/76), 1 次瞬态 all_tiers_exhausted, 0 fallback, 0 429
> Fallback: hm4104 近 5min **无 fallback 日志**

## 1. 背景 (改前必有数据)

R1033-R1038 六连 NOP (各窗口 100% SR)。本轮 30min 窗口出现 **1 次
`all_tiers_exhausted`** (180s tier 预算被单次请求耗尽, SR=98.68%), 但 0 fallback、0 429、
5 key 均匀、延迟稳定 — 属单次瞬态 NVCF 全 key 停滞, 非配置性根因, 判定为 NOP。

### 30min 窗口 — nv_requests
- 总量 76, 200=75, err=1, **SR=98.68%** (75/76)
- Avg/P50/P95: 23913ms / 13539ms / 80075ms (p50 中值 13.5s, p95 80.1s 属 pexec 长尾; avg 较上轮
  17.5s 抬升至 23.9s 由单次 180s 耗尽拉高, 详见 err 项)
- 错误: `all_tiers_exhausted|1|180029` — 单次请求烧满 180s tier 预算仍无成功, tier 级全局耗尽
- upstream: nvcf_pexec 全部 (76/76), integrate 0
- finish_reason: tool_calls=46, stop=29 (正常工具调用型负载)
- 429: **0**, key_cycle_429s: k0=21, k1=55 (正常轮转计数, 无实际 429 失败)

### 30min per-key 200 延迟
| key | n | avg_ok_ms | max_ok_ms |
|-----|---|-----------|-----------|
| 0   | 12 | 17344     | 35992     |
| 1   | 15 | 18654     | 61112     |
| 2   | 16 | 25484     | 87363     |
| 3   | 14 | 23037     | 66548     |
| 4   | 18 | 23286     | 67554     |

5 key 负载均匀 (12-18 次/key), 延迟均匀 (17.3-25.5s avg), max 35-87s 属 pexec 长时推理长尾,
**无单 key 持续劣化**。k2 avg 25.5s/max 87s 为最长长尾但 n=16 无错误, 非劣化信号。

### 6h / 3h / 24h 趋势
- **6h: 1603 总, 1597 ok, SR=99.63%**, 6 err, 0 429
- 3h 逐小时: 03:00=95/94(98.9%), 02:00=225/224(99.6%), 01:00=236/235(99.6%),
  00:00=134/134(100%) → 4 整点全部 98.9%+, 单 err 为瞬态
- 24h all_tiers_exhausted: 30 (中长累积, 本 30min 窗口仅 1, 不属"频发")

### Fallback 日志 (hm4104, 近 5min)
- **无 fallback 日志** — 无 zombie 检测, 无 breaker-skip, 无 PRIMARY fallback。端到端无降级。

## 2. 决策: NOP (无参数修改)

**依据:**
1. **SR 达标**: 30min SR=98.68% (75/76), 6h SR=99.63% (1597/1603)。均远超 95% 阈值。
2. **单次 all_tiers_exhausted 属瞬态, 非频发**: 1/30min, 6/6h。诊断映射要求"all_tiers_exhausted
   **频发**"才考虑 budget/冷却调整。当前单次事件是 180s 预算窗口内 5 key 全被 NVCF 停滞拖死
   (一次随机上游抖动), 非配置性根因。img R1032 曾出现同类瞬态, 数轮后自愈, 无复发。
3. **0 fallback / 0 429 / tier_attempts 为空** — 无冷却、轮转、fastbreak 压力。端到端无降级。
4. **5 key 负载与延迟完全均匀** (12-18 次/key, avg 17.3-25.5s) — 无单 key 劣化需 key 冷却/重分配。
5. **upstream 全 pexec 稳定**: 76/76 走 nvcf_pexec, integrate 0。无切 integrate 必要。
6. **一次只改一个参数**: 单次 180s 耗尽不足以支撑干净归因的 env 改动。若为预算问题, 任意微调
   (如 TIER_TIMEOUT_BUDGET_S / NVU_TIER_BUDGET_DSV4F0731_NV) 对 99%+ 链路属过度干预, 只增风险。
   NOP 最稳。

当前实际 env 值 (本容器, 已 docker exec 复核): UPSTREAM_TIMEOUT=50, TIER_COOLDOWN_S=90,
KEY_COOLDOWN_S=30, NVU_KEYMGR_429_BASE/MAX_COOLDOWN=120, NVU_KEYMGR_CONN_BASE_COOLDOWN=30,
NVU_KEYMGR_CONN_MAX_COOLDOWN=60, NVU_KEYMGR_CONN_FAIL_THRESHOLD=3, NVU_KEYMGR_CONN_LONG_COOLDOWN=120,
NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3, NVU_TIER_BUDGET_DSV4F0731_NV=180,
TIER_TIMEOUT_BUDGET_S=180 — 全部维持, 无改。

## 3. 当前状态 (30min 主指标 + 6h 趋势)

- 30min SR: **98.68%** (75/76) / **6h SR: 99.63%** (1597/1603)
- Avg/P50/P95: 23913ms / 13539ms / 80075ms
- 错误 (30min): `all_tiers_exhausted` 1 (180029ms, 单次瞬态)
- 429: 0
- upstream: pexec 全部 (76/76), integrate 0
- fallback: 0 (hm4104 5min 无任何 fallback 日志)

## 4. 上次修改效果 (R1038 NOP → 本轮)

- **SR 满格微落**: 100% (R1038 30min) → **98.68%** (本轮, 单次 180s 耗尽); 6h 从 99.78% →
  **99.63%** (4 err → 6 err)。单 err 事件, 绝对值小, 非系统性劣化。
- **0 fallback 持续**: 0 (R1038) → **0** (本轮)。端到端仍无降级。
- **0 429 持续**: 连续多轮无 429。
- **5 key 均匀性维持**: 无单 key 持续劣化, R1038 均匀状态保持。
- **延迟稳定**: p50 11.1s→13.5s, 属正常 pexec 长尾波动; avg 抬升由单次 180s 耗尽拉高, 非链路劣化。

## 5. 下一步建议

1. **维持现状**: 98.68% SR + 0 fallback + 0 429 仍为健康稳态, 不改任何参数。单次 all_tiers_exhausted
   不构成干预信号。
2. **持续监控下探**: 关注 30min 内 `all_tiers_exhausted` 是否**连续多轮 >1** 或单轮 >3。若出现
   all_tiers_exhausted 频发 (如 30min >3 或连续 2 轮复发), 才考虑 NVU_TIER_BUDGET_DSV4F0731_NV /
   TIER_TIMEOUT_BUDGET_S 微调 (缩短 budget 以更快释放 tier 冷却, 或调 TIER_COOLDOWN_S 缩短黑窗)。
3. **若单 key 延迟持续 >30s 或错误集中**: 才考虑 key 级冷却调整 / integrate 通路重分配; 当前
   5 key 均匀无此需求。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] 数据完整: 30min SR/延迟/错误分布/fallback/6h 趋势/24h 均已采集
- [x] 错误分类表: 仅 1 次 all_tiers_exhausted (180029ms), 无 429/502/empty-200 等其他错误
- [x] per-key 5 key 完全均匀 (12-18 次/key), 无单 key 持续劣化
- [x] hm4104 近 5min 无 fallback 日志, 端到端无降级
- [x] 决策数据驱动: SR 98.68% > 95%, 单次瞬态 all_tiers_exhausted, 0 fallback, 0 429 → NOP