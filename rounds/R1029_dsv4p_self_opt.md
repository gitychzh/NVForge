# R1029: 链路健康 SR 98.7%, 2 单次瞬时错误均触发 CC 兜底, 死链 83s 浪费为源码级 — NOP

> 时间: 2026-08-08 03:20 UTC
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
> 状态: **NOP (无参数修改)** — 30min SR 98.7% (149/151), 6h SR 99.3%, 429=0, 5 key 全部健康均匀
> Fallback: hm4104 近 30min 2× CONTENT_FILTER_ZOMBIE → 2× fallback + 2× breaker-skip (瞬时, 被 ms_gw 接住)

## 1. 背景 (改前必有数据)

R1028 为 NOP (30min SR 99.4%)。本轮 30min 窗口 SR 微降至 98.7%, 出现 2 个单次瞬时错误
(分属不同 key / 不同 error_type), 均触发 hm4104 content_filter zombie 检测与 ms_gw fallback。
但主链路稳态未破坏: 6h SR 99.3%, 429=0, all_tiers_exhausted 窗口内 0, 5 key 延��高度均匀。

### 30min 窗口 — nv_requests
- 总量 151, 200=149, err=2, **SR=98.7%** (149/151)
- Avg/P50/P95/Max: 10029ms / 13358ms / 37015ms / 54812ms (延迟健康, p50 中值 13.4s)
- 错误 (2 个, 分属 k1 与 k0):
  - **NVStream_IncompleteRead=1** (k1, avg 33764ms=33.8s)
  - **stream_first_byte_timeout=1** (k0, avg 83238ms=83.2s)
- upstream: nvcf_pexec 全部 (151/151), integrate 0
- finish_reason: tool_calls=130, stop=19 (正常工具调用型负载)
- 429: **0**, key_cycle_429s: k0=56, k1=95 (正常轮转计数, 无实际 429 失败)

### 30min per-key 200 延迟
| key | n | avg_ok_ms | max_ok_ms |
|-----|---|-----------|-----------|
| 0   | 31 | 12207     | 24954     |
| 1   | 28 | 13727     | 28772     |
| 2   | 33 | 11904     | 24261     |
| 3   | 29 | 11255     | 39997     |
| 4   | 28 | 14933     | 35792     |

5 key 全部活跃健康, 延迟高度均匀 (11-15s avg), 无单 key 劣化。

### 6h / 3h / 24h 趋势
- **6h: 1760 总, 1747 ok, SR=99.3%**, 13 err, 0 429
- 3h 逐小时: 19:00=100/101(99.0%), 18:00=346/347(99.7%), 17:00=273/279(97.8%), 16:00=181/181(100%)
  → SR 稳定 97.8-100%, 无持续恶化
- 24h all_tiers_exhausted: 117 (早前劣化累积, 本 30min 窗口 0)

### Fallback 日志 (hm4104, 近 30min) — PRIMARY_URL=dsvf0731_nv40666:40666
- **64 REQ, 全部 model=dsv4f0731_nv** (确认 hm4104 直连本容器)
- **2 CONTENT_FILTER_ZOMBIE** + 2 PRIMARY-ZOMBIE-FALLBACK + 4 FALLBACK-STREAM
- **2 PRIMARY-BREAKER-SKIP-STREAM** (03:18:16 / 03:18:25, circuit 短暂 OPEN 直走 fallback)
- 与容器日志 2 个错误事件一一对应: 02:59:58 (NVStream_IncompleteRead) 与 03:18:05
  (stream_first_byte_timeout), 均已由 ms_gw 兜底接住, 未造成 CC 报错。

## 2. 决策: NOP (无参数修改)

**依据:**
1. **SR 达标**: 30min SR=98.7% (149/151) > 95% 阈值; 6h SR=99.3% (1747/1760)。无 SR 危机。
2. **错误为单次瞬时, 非模式化**: 2 错误分属不同 key (k0/k1)、不同 error_type, 均 <
   NVU_PEXEC_TIMEOUT_FASTBREAK 阈值(3) 与 NVU_KEYMGR_CONN_FAIL_THRESHOLD(3)。不触发冷却/熔断的持续条件。
3. **429=0, all_tiers_exhausted 窗口内 0** — 无冷却/轮转/fastbreak 压力。
4. **5 key 延迟高度均匀 (11-15s), 无单 key 劣化** — 无 key 级问题需要 key 冷却/重分配。
5. **根因核查 (改前必有数据)**: 83s 的 stream_first_byte_timeout 是死链浪费, 与 R11 发现的
   NVCFPexecTimeout >cutoff 死链浪费同型。但源码核查 (`handlers.py` R1411 注释 + R1648 实现) 表明
   该 **deadline (NVU_STREAM_FIRST_BYTE_DEADLINE_S 默认20s) 对 200-then-hang 死链形同虚设**:
   `socket.timeout` 被 catch 后 `continue`, 循环卡在 `resp.read()` 直到底层层 ~66s connect timeout
   才 break (~97s)。**这是源码级 socket-continue 结构问题, 非 env 可干净归因修复** — 单改
   NVU_STREAM_FIRST_BYTE_DEADLINE_S (设为更低) 不会改变实际 break 时机 (deadline 根本到不了)。
   不宜用 env 微调掩盖源码 bug。归入架构/源码层排查, 本轮不改。
6. **一次只改一个参数**: 无任何单一 env 改动能干净归因地改善当前稳态 — 加之为源码级问题, NOP 最稳。

## 3. 当前状态 (30min 主指标 + 6h 趋势)

- 30min SR: **98.7%** (149/151) / **6h SR: 99.3%** (1747/1760)
- Avg/P50/P95: 10029ms / 13358ms / 37015ms
- 错误 (30min): NVStream_IncompleteRead=1 (k1, 33.8s), stream_first_byte_timeout=1 (k0, 83.2s)
- 429: 0
- upstream: pexec 全部 (151/151), integrate 0
- fallback: 2× zombie 检测 + 2× breaker-skip, 均被 ms_gw 兜底, 无 CC 报错

## 4. 上次修改效果 (R1028 NOP → 本轮)

- SR 微降: 99.4% (R1028 30min) → **98.7%** (本轮 30min), 6h 维持 99.3%。
- 错误从 1 (R1028 单次 IncompleteRead) → 2 (本轮 IncompleteRead + stream_first_byte_timeout),
  均为单次瞬时, 分属不同 key。属正常瞬时波动, 非恶化趋势。
- 429=0, fallback 由 ms_gw 兜底, 无端到端失败。链路保持稳定。

## 5. 下一步建议

1. **维持现状**: 主链路稳态 (6h 99.3%), 本轮 2 个瞬时错误被 ms_gw 兜底, 无端到端影响。NOP 合理。
2. **源码级关注点 (架构/维护方)**: stream_first_byte_timeout 死链 83s 浪费根因在
   `handlers.py` R1411 注释的 socket.timeout→continue 结构 — 死链 break 依赖 ~66s connect timeout
   (97s) 而非 20s first-byte deadline。建议源码修复: read() 连续超时 N 次(如<5s×2) 即视为死链,
   提前走 deadline break, 而非 continue 到底层 timeout。若修复上线, 该类型误差时段预计 83s→~20s。
3. **若 NVStream_IncompleteRead / stream_first_byte_timeout 反复出现 (如 >3/30min 或单 key 集中)**:
   才考虑 UPSTREAM_TIMEOUT/key 冷却微调; 当前单次不触发。
4. **若单 key 延迟持续 >30s 或错误集中**: 才考虑 key 级冷却调整 / integrate key 重分配。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] 数据完整: 30min SR/延迟/错误分布/fallback/6h 趋势/24h 均已采集
- [x] hm4104 PRIMARY_URL 确认指向本容器 (dsvf0731_nv40666), fallback 事件可归因于本容器模型
- [x] 源码核查 stream_first_byte_timeout 死链根因 → 确认为源码级 socket-continue bug, 非 env 可改
- [x] 决策数据驱动: SR 达标 + 429=0 + 单次瞬时错误 + 根因非 env 可修 → NOP