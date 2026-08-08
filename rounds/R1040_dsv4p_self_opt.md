# R1040: 30min SR 98.48% 单次 NVStream_IncompleteRead(瞬态) 0 fallback 0 429 — NOP

> 时间: 2026-08-08 12:52 UTC
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
> 状态: **NOP (无参数修改)** — 30min SR 98.48% (65/66), 1 次瞬态 NVStream_IncompleteRead, 0 fallback, 0 429
> Fallback: hm4104 近 5min **无 fallback 日志**

## 1. 背景 (改前必有数据)

R1033-R1039 七连 NOP (各窗口 98.68%-100% SR)。本轮 30min 窗口出现 **1 次
`NVStream_IncompleteRead`** (k4, 35491ms, 流被上游 NVCF 截断), SR=98.48%, 但 0 fallback、0 429、
5 key 均匀、延迟稳定 — 属单次瞬态 NVCF 流中断, 非配置性根因, 判定为 NOP。

### 30min 窗口 — nv_requests
- 总量 66, 200=65, err=1, **SR=98.48%** (65/66)
- Avg/P50/P95: 26130ms / 18379ms / 96227ms (p50 中值 18.4s, p95 96.2s 属 pexec 长尾; avg 较上轮
  23.9s 抬升至 26.1s 由单次 35.5s 流中断 + 长尾拉高, 详见 err 项)
- 错误: `NVStream_IncompleteRead|1|35491` — 单次流被上游截断 (k4)
- upstream: nvcf_pexec 全部 (66/66), integrate 0
- finish_reason: tool_calls=49, stop=16 (正常工具调用型负载)
- 429: **0**, key_cycle_429s: k0=28, k1=36, k2=2 (轮转计数, 无实际 429 失败)

### 30min per-key 200 延迟
| key | n | avg_ok_ms | max_ok_ms |
|-----|---|-----------|-----------|
| 0   | 9  | 20074     | 38918     |
| 1   | 12 | 27919     | 71947     |
| 2   | 17 | 28159     | 95830     |
| 3   | 16 | 29954     | 109555    |
| 4   | 11 | 19587     | 36966     |

5 key 负载均匀 (9-17 次/key), 200 延迟均匀 (19.6-30.0s avg), max 37-110s 属 pexec 长时推理长尾,
**无单 key 持续劣化**。k4 唯一错误为瞬时 IncompleteRead, 但其 200 延迟 19.6s 为最低, 非劣化信号。

### 6h / 3h / 24h 趋势
- **6h: 1420 总, 1413 ok, SR=99.51%**, 7 err, 0 429
- 3h 逐小时: 04:00=130/132(98.5%), 03:00=165/168(98.2%), 02:00=224/225(99.6%),
  01:00=34/35(97.1%) → 4 整点全部 97%+, 单 err 为瞬态
- 24h all_tiers_exhausted: 27 (与 R1039 同量级中长累积, 本 30min 窗口 0, 不属"频发")

### Fallback 日志 (hm4104, 近 5min)
- **无 fallback 日志** — 无 zombie 检测, 无 breaker-skip, 无 PRIMARY fallback。端到端无降级。

## 2. 决策: NOP (无参数修改)

**依据:**
1. **SR 达标**: 30min SR=98.48% (65/66), 6h SR=99.51% (1413/1420)。均远超 95% 阈值。
2. **单次 NVStream_IncompleteRead 属瞬态, 非频发**: 1/30min, 7/6h。诊断映射要求
   "NVStream_IncompleteRead" 考虑超时不够或 NVCF 端问题, 但单次 35.5s 流中断 (k4)、0 fallback
   触发, 属随机上游流抖动, 非全链路超时不足 (UPSTREAM_TIMEOUT=50 > 35.5s, 未触发超时)。
3. **0 fallback / 0 429 / tier_attempts 为空** — 无冷却、轮转、fastbreak 压力。端到端无降级。
4. **5 key 负载与 200 延迟完全均匀** (9-17 次/key, avg 19.6-30.0s) — 无单 key 劣化需 key 冷却/重分配。
   唯一错误的 k4 200 延迟反而最低, 明确非 key 劣化。
5. **upstream 全 pexec 稳定**: 66/66 走 nvcf_pexec, integrate 0。无切 integrate 必要。
6. **一次只改一个参数**: 单次流中断不足以支撑干净归因的 env 改动。若为超时问题, 任意微调
   (如 UPSTREAM_TIMEOUT / TIER_TIMEOUT_BUDGET_S) 对 99%+ 链路属过度干预, 且 35.5s < 50s 超时
   已证明非超时根因。NOP 最稳。

当前实际 env 值 (本容器, 已 docker exec 复核): UPSTREAM_TIMEOUT=50, TIER_COOLDOWN_S=90,
KEY_COOLDOWN_S=30, NVU_KEYMGR_429_BASE/MAX_COOLDOWN=120, NVU_KEYMGR_CONN_BASE_COOLDOWN=30,
NVU_KEYMGR_CONN_MAX_COOLDOWN=60, NVU_KEYMGR_CONN_FAIL_THRESHOLD=3, NVU_KEYMGR_CONN_LONG_COOLDOWN=120,
NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3, NVU_TIER_BUDGET_DSV4F0731_NV=180,
TIER_TIMEOUT_BUDGET_S=180 — 全部维持, 无改。

## 3. 当前状态 (30min 主指标 + 6h 趋势)

- 30min SR: **98.48%** (65/66) / **6h SR: 99.51%** (1413/1420)
- Avg/P50/P95: 26130ms / 18379ms / 96227ms
- 错误 (30min): `NVStream_IncompleteRead` 1 (35491ms, 单次瞬态, k4)
- 429: 0
- upstream: pexec 全部 (66/66), integrate 0
- fallback: 0 (hm4104 5min 无任何 fallback 日志)

## 4. 上次修改效果 (R1038 NOP → R1039 NOP → 本轮)

- **SR 微动**: 100% (R1038) → 98.68% (R1039, 单次 all_tiers_exhausted) → **98.48%** (本轮,
  单次 NVStream_IncompleteRead); 6h 从 99.78% → 99.63% → **99.51%**。单 err 事件, 绝对值小,
  错误类型每次不同 (all_tiers_exhausted → NVStream_IncompleteRead), 均为随机瞬态, 非系统性劣化。
- **0 fallback 持续**: 0 (R1039) → **0** (本轮)。端到端仍无降级。
- **0 429 持续**: 连续多轮无 429。
- **5 key 均匀性维持**: 无单 key 持续劣化, R1038 均匀状态保持; 唯一错误 key k4 的 200 延迟为
  最低 (19.6s), 明确非 key 劣化。
- **延迟稳定**: p50 13.5s→18.4s, 属正常 pexec 长尾波动; 错误类型每轮不同, 无累积劣化。

## 5. 下一步建议

1. **维持现状**: 98.48% SR + 0 fallback + 0 429 仍为健康稳态, 不改任何参数。单次 NVStream_IncompleteRead
   不构成干预信号。
2. **持续监控下探**: 关注 30min 内错误是否**连续多轮 >1** 或单轮 >3, 或**同一错误类型复发**。
   若 NVStream_IncompleteRead 频发 (如 30min >3 或连续 2 轮复发集中在同一 key), 才考虑
   UPSTREAM_TIMEOUT 微调或该 key 的 SOCKS5 代理检查。当前 35.5s < 50s 超时, 已证明非超时根因。
3. **若单 key 延迟持续 >30s 或错误集中**: 才考虑 key 级冷却调整 / integrate 通路重分配; 当前
   5 key 均匀无此需求。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] 数据完整: 30min SR/延迟/错误分布/fallback/6h 趋势/24h 均已采集
- [x] 错误分类表: 仅 1 次 NVStream_IncompleteRead (35491ms, k4), 无 429/502/empty-200/all_tiers 等其他错误
- [x] per-key 5 key 完全均匀 (9-17 次/key), 唯一错误 k4 的 200 延迟为最低, 无单 key 持续劣化
- [x] hm4104 近 5min 无 fallback 日志, 端到端无降级
- [x] 决策数据驱动: SR 98.48% > 95%, 单次瞬态 NVStream_IncompleteRead, 0 fallback, 0 429 → NOP