# R1030: 链路完全健康 30min SR 100% 0错误 0 fallback 5key 均匀 — NOP

> 时间: 2026-08-08 04:52 UTC
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
> 状态: **NOP (无参数修改)** — 30min SR 100% (196/196), 0 错误, 0 429, 0 fallback, 5 key 全部健康均匀
> Fallback: hm4104 近 5min **无 fallback 日志**, 无 zombie/breaker/minor 兜底

## 1. 背景 (改前必有数据)

R1029 为 NOP (30min SR 98.7%, 2 单次瞬时错误)。本轮 30min 窗口 **SR=100%, 0 错误,
0 429, 0 fallback** — 无任何劣化信号。主链路稳态完全健康, 无需任何参数调整。

### 30min 窗口 — nv_requests
- 总量 196, 200=196, err=0, **SR=100%** (196/196)
- Avg/P50/P95: 10036ms / 8335ms / 31527ms (延迟健康, 与 R1029 同量级, p50 中值 8.3s)
- 错误: **无** (错误分类表为空)
- upstream: nvcf_pexec 全部 (196/196), integrate 0
- finish_reason: tool_calls=170, stop=26 (正常工具调用型负载)
- 429: **0**, key_cycle_429s: k0=79, k1=117 (正常轮转计数, 无实际 429 失败)

### 30min per-key 200 延迟
| key | n | avg_ok_ms | max_ok_ms |
|-----|---|-----------|-----------|
| 0   | 38 | 10461     | 23533     |
| 1   | 40 | 7722      | 21249     |
| 2   | 38 | 11895     | 23598     |
| 3   | 39 | 9567      | 18685     |
| 4   | 41 | 10621     | 31025     |

5 key 负载完全均匀 (38-41 次/key), 延迟高度均匀 (7.7-11.9s avg), 无单 key 劣化。
注意 R1029 中异常的 k0 (83s 死链) 与 k1 (33.8s IncompleteRead) 本轮均恢复正常
(k0 avg 10.5s, k1 avg 7.7s) — 上次瞬时错误未复发。

### 6h / 3h / 24h 趋势
- **6h: 1933 总, 1924 ok, SR=99.5%**, 9 err, 0 429
- 3h 逐小时: 20:00=354/354(100%), 19:00=349/348(99.7%), 18:00=347/346(99.7%),
  17:00=38/35(SSR 92.1% 低流量窗口, 绝对值仅 3 err)
  → SR 稳定 99.5%+, 无持续恶化
- 24h all_tiers_exhausted: 102 (早前劣化累积, 本 30min 窗口 0)

### Fallback 日志 (hm4104, 近 5min)
- **无 fallback 日志** — 无 zombie 检测, 无 breaker-skip, 无 PRIMARY fallback。
  对比 R1029 存在 2×CONTENT_FILTER_ZOMBIE + 2×breaker-skip, 本轮完全干净。

## 2. 决策: NOP (无参数修改)

**依据:**
1. **SR 达标且满格**: 30min SR=100% (196/196), 6h SR=99.5% (1924/1933)。远超 95% 阈值。
2. **0 错误 / 0 429 / tier_attempts 为空** — 无冷却、轮转、fastbreak 压力。无 key 级问题。
3. **R1029 瞬时错误未复发**: k0 死链 (83s) 与 k1 IncompleteRead (33.8s) 本轮均正常,
   证实为瞬时波动而非模式化劣化。
4. **5 key 负载与延迟完全均匀** (38-41 次/key, avg 7.7-11.9s) — 无单 key 劣化需 key 冷却/重分配。
5. **upstream 全 pexec 稳定**: 196/196 走 nvcf_pexec, integrate 0。pexec 链路可靠, 无切 integrate 必要。
6. **fallback 完全干净**: hm4104 5min 无任何 fallback/兜底事件, 端到端无降级。
7. **一次只改一个参数**: 当前无任何单一 env 改动能干净归因地进一步改善 100% SR。
   改动参数只会引入风险而无比收益。NOP 最稳。

## 3. 当前状态 (30min 主指标 + 6h 趋势)

- 30min SR: **100%** (196/196) / **6h SR: 99.5%** (1924/1933)
- Avg/P50/P95: 10036ms / 8335ms / 31527ms
- 错误 (30min): **无**
- 429: 0
- upstream: pexec 全部 (196/196), integrate 0
- fallback: 0 (hm4104 5min 无任��� fallback 日志)

## 4. 上次修改效果 (R1029 NOP → 本轮)

- **SR 提升并满格**: 98.7% (R1029 30min) → **100%** (本轮 30min); 6h 从 99.3% → **99.5%**。
- **错误清零**: 2 (R1029: IncompleteRead + stream_first_byte_timeout) → **0** (本轮)。
  R1029 的两个问题 key (k0/k1) 本轮均恢复正常延迟, 证实为瞬时波动。
- **fallback 清零**: 2×zombie + 2×breaker-skip (R1029) → **0** (本轮)。
- 429=0 持续, 延迟同量级 (p50 13.4s→8.3s, 更优)。链路从"健康"升级为"完全健康"。

## 5. 下一步建议

1. **维持现状**: 100% SR + 0 fallback + 0 429 为理想稳态, 不改任何参数。
2. **持续监控下探**: 关注 6h SR 是否维持 99.5%+ (当前窗口 9 err 主要来自 17:00 低流量
   窗口的 3 err, 绝对值小)。若 6h SR 跌破 98% 或 30min 内任一 error_type 持续 >3、
   才开始考虑 UPSTREAM_TIMEOUT / key 冷却微调。
3. **源码级关注点保留 (不属本容器 env 可修)**: R1029 确认的 stream_first_byte_timeout
   死链 83s 浪费 (handlers.py socket.timeout→continue 结构) 仍为架构/维护方源码项,
   本轮未复发不作为本容器行动项。
4. **若单 key 延迟持续 >30s 或错误集中**: 才考虑 key 级冷却调整 / integrate 通路重分配;
   当前 5 key 均匀无此需求。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] 数据完整: 30min SR/延迟/错误分布/fallback/6h 趋势/24h 均已采集
- [x] 无错误分类表输出 (错误表为空, 佐证 err=0)
- [x] per-key 5 key 均匀, 无单 key 劣化
- [x] hm4104 近 5min 无 fallback 日志, 端到端无降级
- [x] 决策数据驱动: SR 100% + 0 错误 + 0 429 + 0 fallback → NOP