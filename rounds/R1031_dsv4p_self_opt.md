# R1031: 链路持续完全健康 30min SR 100% 0错误 0 fallback 5key 均匀 — NOP

> 时间: 2026-08-08 05:12 UTC
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
> 状态: **NOP (无参数修改)** — 30min SR 100% (188/188), 0 错误, 0 429, 0 fallback, 5 key 全部健康均匀
> Fallback: hm4104 近 5min **无 fallback 日志**

## 1. 背景 (改前必有数据)

R1030 为 NOP (30min SR 100%)。本轮 30min 窗口 **SR=100%, 0 错误, 0 429, 0 fallback** — 链路维持完全健康稳态, 无需任何参数调整。

### 30min 窗口 — nv_requests
- 总量 188, 200=188, err=0, **SR=100%** (188/188)
- Avg/P50/P95: 9564ms / 7873ms / 21922ms (延迟健康, 与 R1030 同量级, p50 中值 7.9s)
- 错误: **无** (错误分类表为空)
- upstream: nvcf_pexec 全部 (188/188), integrate 0
- finish_reason: tool_calls=162, stop=27 (正常工具调用型负载)
- 429: **0**, key_cycle_429s: k0=72, k1=117 (正常轮转计数, 无实际 429 失败)

### 30min per-key 200 延迟
| key | n | avg_ok_ms | max_ok_ms |
|-----|---|-----------|-----------|
| 0   | 37 | 9669      | 20335     |
| 1   | 37 | 7940      | 18666     |
| 2   | 38 | 9779      | 20710     |
| 3   | 39 | 9361      | 21983     |
| 4   | 37 | 11076     | 29204     |

5 key 负载完全均匀 (37-39 次/key), 延��高度均匀 (7.9-11.1s avg), 无单 key 劣化。

### 6h / 3h / 24h 趋势
- **6h: 1957 总, 1948 ok, SR=99.5%**, 9 err, 0 429
- 3h 逐小时: 21:00=71/71(100%), 20:00=405/405(100%), 19:00=349/348(99.7%),
  18:00=293/292(99.7%)
  → SR 稳定 99.5%+, 无持续恶化, 仅极少量单次 err
- 24h all_tiers_exhausted: 100 (早前劣化累积, 本 30min 窗口 0)

### Fallback 日志 (hm4104, 近 5min)
- **无 fallback 日志** — 无 zombie 检测, 无 breaker-skip, 无 PRIMARY fallback。端到端无降级。

## 2. 决策: NOP (无参数修改)

**依据:**
1. **SR 达标且满格**: 30min SR=100% (188/188), 6h SR=99.5% (1948/1957)。远超 95% 阈值。
2. **0 错误 / 0 429 / tier_attempts 为空** — 无冷却、轮转、fastbreak 压力。无 key 级问题。
3. **R1030 确认的稳定态延续**: 连续两轮 30min SR 100%, 链路稳态完全成立。
4. **5 key 负载与延迟完全均匀** (37-39 次/key, avg 7.9-11.1s) — 无单 key 劣化需 key 冷却/重分配。
5. **upstream 全 pexec 稳定**: 188/188 走 nvcf_pexec, integrate 0。pexec 链路可靠, 无切 integrate 必要。
6. **fallback 完全干净**: hm4104 5min 无任何 fallback/兜底事件, 端到端无降级。
7. **一次只改一个参数**: 当前无任何单一 env 改动能干净归因地进一步改善 100% SR。
   修改参数只会引入风险而无比收益。NOP 最稳。

当前实际 env 值 (本容器): UPSTREAM_TIMEOUT=50, TIER_COOLDOWN_S=90, KEY_COOLDOWN_S=30,
NVU_KEYMGR_429_BASE/MAX_COOLDOWN=120, NVU_KEYMGR_CONN_BASE_COOLDOWN=30, NVU_PEXEC_TIMEOUT_FASTBREAK=3,
NVU_EMPTY_200_FASTBREAK=3, NVU_TIER_BUDGET_DSV4F_NV=180, TIER_TIMEOUT_BUDGET_S=180 — 全部维持, 无改。

## 3. 当前状态 (30min 主指标 + 6h 趋势)

- 30min SR: **100%** (188/188) / **6h SR: 99.5%** (1948/1957)
- Avg/P50/P95: 9564ms / 7873ms / 21922ms
- 错误 (30min): **无**
- 429: 0
- upstream: pexec 全部 (188/188), integrate 0
- fallback: 0 (hm4104 5min 无任何 fallback 日志)

## 4. 上次修改效果 (R1030 NOP → 本轮)

- **SR 维持满格**: 100% (R1030 30min) → **100%** (本轮 30min); 6h 从 99.5% → **99.5%**。
- **错误清零持续**: 0 (R1030) → **0** (本轮)。连续两轮无任何 error_type。
- **fallback 清零持续**: 0 (R1030) → **0** (本轮)。
- **429=0 持续**: 连续多轮无 429。
- 延迟同量级 (p50 8.3s→7.9s, 基本持平)。链路处于**完全健康稳态**。

## 5. 下一步建议

1. **维持现状**: 100% SR + 0 fallback + 0 429 为理想稳态, 不改任何参数。
2. **持续监控下探**: 关注 6h SR 是否维持 99.5%+ (当前窗口 9 err 绝对值小)。若 6h SR 跌破
   98% 或 30min 内任一 error_type 持续 >3, 才开始考虑 UPSTREAM_TIMEOUT / key 冷却微调。
3. **若单 key 延迟持续 >30s 或错误集中**: 才考虑 key 级冷却调整 / integrate 通路重分配;
   当前 5 key 均匀无此需求。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] 数据完整: 30min SR/延迟/错误分布/fallback/6h 趋势/24h 均已采集
- [x] 无错误分类表输出 (错误表为空, 佐证 err=0)
- [x] per-key 5 key 均匀, 无单 key 劣化
- [x] hm4104 近 5min 无 fallback 日志, 端到端无降级
- [x] 决策数据驱动: SR 100% + 0 错误 + 0 429 + 0 fallback → NOP