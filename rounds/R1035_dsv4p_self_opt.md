# R1035: 30min SR 100% 0错误 0 429 0 fallback 5key 均匀 6h SR 99.7% — NOP

> 时间: 2026-08-08 08:28 UTC
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
> 状态: **NOP (无参数修改)** — 30min SR 100% (155/155), 0 错误, 0 429, 0 fallback, 5 key 完全均匀
> Fallback: hm4104 近 5min **无 fallback 日志**

## 1. 背景 (改前必有数据)

R1034 为 NOP (30min SR 100%, 0 错误)。本轮 30min 窗口与上轮完全一致, **SR=100%,
0 错误, 0 429, 0 fallback**, 6h SR 99.7% — 链路维持高度健康稳态, 无参数调整需求。

### 30min 窗口 — nv_requests
- 总量 155, 200=155, err=0, **SR=100%** (155/155)
- Avg/P50/P95: 11292ms / 9384ms / 28116ms (延迟健康, p50 中值 9.4s)
- 错误: **无** (错误分类表为空)
- upstream: nvcf_pexec 全部 (155/155), integrate 0
- finish_reason: tool_calls=130, stop=25 (正常工具调用型负载)
- 429: **0**, key_cycle_429s: k0=69, k1=86 (正常轮转计数, 无实际 429 失败)

### 30min per-key 200 延迟
| key | n | avg_ok_ms | max_ok_ms |
|-----|---|-----------|-----------|
| 0   | 31 | 10646     | 28327     |
| 1   | 32 | 10741     | 26354     |
| 2   | 28 | 11423     | 19657     |
| 3   | 31 | 9944      | 28335     |
| 4   | 33 | 13589     | 30834     |

5 key 负载完全均匀 (28-33 次/key), 延迟高度均匀 (9.9-13.6s avg), max 19.7-30.8s 属
pexec 长时推理正常长尾, **无单 key 劣化**。

### 6h / 3h / 24h 趋势
- **6h: 1989 总, 1984 ok, SR=99.7%**, 5 err, 0 429
- 3h 逐小时: 00:00=145/145(100%), 23:00=316/316(100%), 22:00=265/262(98.9%),
  21:00=192/192(100%) → 仅 22:00 残留 3 次 err, 其余整点 100%, 无持续恶化
- 24h all_tiers_exhausted: 47 (早前劣化累积, 本 30min 窗口 0)

### Fallback 日志 (hm4104, 近 5min)
- **无 fallback 日志** — 无 zombie 检测, �� breaker-skip, 无 PRIMARY fallback。端到端无降级。

## 2. 决策: NOP (无参数修改)

**依据:**
1. **SR 达标且满格**: 30min SR=100% (155/155), 6h SR=99.7% (1984/1989)。远超 95% 阈值。
2. **0 错误 / 0 429 / tier_attempts 为空 且为空** — 无冷却、轮转、fastbreak 压力。无 key 级问题。
3. **连续三轮 NOP 窗口 (R1033/R1034/R1035) 均 100% SR** — 早前瞬时 NVCF 抖动彻底收敛且未复发,
   确认纯属随机上游瞬态, 无配置性根因。
4. **5 key 负载与延迟完全均匀** (28-33 次/key, avg 9.9-13.6s) — 无单 key 劣化需 key 冷却/重分配。
5. **upstream 全 pexec 稳定**: 155/155 走 nvcf_pexec, integrate 0。pexec 链路可靠, 无切 integrate 必要。
6. **fallback 完全干净**: hm4104 5min 无任何 fallback/兜底事件, 端到端无降级。
7. **一次只改一个参数**: 当前无任何单一 env 改动能干净归因地进一步改善 100% SR。
   修改参数只会引入风险而无比收益。NOP 最稳。

当前实际 env 值 (本容器): UPSTREAM_TIMEOUT=50, TIER_COOLDOWN_S=90, KEY_COOLDOWN_S=30,
NVU_KEYMGR_429_BASE/MAX_COOLDOWN=120, NVU_KEYMGR_CONN_BASE_COOLDOWN=30,
NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3, NVU_TIER_BUDGET_DSV4F_NV=180,
TIER_TIMEOUT_BUDGET_S=180 — 全部维持, 无改。

## 3. 当前状态 (30min 主指标 + 6h 趋势)

- 30min SR: **100%** (155/155) / **6h SR: 99.7%** (1984/1989)
- Avg/P50/P95: 11292ms / 9384ms / 28116ms
- 错误 (30min): **无**
- 429: 0
- upstream: pexec 全部 (155/155), integrate 0
- fallback: 0 (hm4104 5min 无任何 fallback 日志)

## 4. 上次修改效果 (R1034 NOP → 本轮)

- **SR 维持满格**: 100% (R1034 30min) → **100%** (本轮 30min); 6h 从 99.7% → **99.7%**。
  三轮连续 NOP 后 6h SR 稳居 99.5%+, 载重 155-175/窗口 稳定。
- **错误清零持续**: 0 (R1034) → **0** (本轮)。无错误簇复发。
- **fallback 清零持续**: 0 (R1034) → **0** (本轮)。
- **429=0 持续**: 连续多轮无 429。
- **5 key 均匀性维持**: 无单 key 持续劣化, R1034 均匀状态保持。

## 5. 下一步建议

1. **维持现状**: 100% SR + 0 fallback + 0 429 为理想稳态, 不改任何参数。
2. **持续监控下探**: 关注 6h SR 是否维持 99.5%+ (当前窗口 5 err 绝对值小, 全集中 22:00)。
   若 6h SR 跌破 98% 或 30min 内任一 error_type 持续 >3, 才开始考虑 UPSTREAM_TIMEOUT /
   key 冷却微调。
3. **若单 key 延迟持续 >30s 或错误集中**: 才考虑 key 级冷却调整 / integrate 通路重分配;
   当前 5 key 均匀无此需求。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] 数据完整: 30min SR/延迟/错误分布/fallback/6h 趋势/24h 均已采集
- [x] 无错误分类表输出 (错误表为空, 佐证 err=0)
- [x] per-key 5 key 完全均匀 (28-33 次/key), 无单 key 劣化
- [x] hm4104 近 5min 无 fallback 日志, 端到端无降级
- [x] 决策数据驱动: SR 100% + 0 错误 + 0 429 + 0 fallback → NOP