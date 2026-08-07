# R1032: 30min SR 98.1% 仅 2 次上游瞬时 NVCF 断连 6h 99.5% 0 429 0 fallback — NOP

> 时间: 2026-08-08 07:15 UTC
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
> 状态: **NOP (无参数修改)** — 30min SR 98.1% (101/103), 2 次瞬时错误 (k0 all_tiers_exhausted + k4 buffer_exhausted), 0 429, 0 fallback
> Fallback: hm4104 近 5min **无 fallback 日志**

## 1. 背景 (改前必有数据)

R1031 为 NOP (30min SR 100%)。本轮为低流量窗口 (30min 仅 103 请求, 对比 R1031 的 188),
出现 2 次瞬时上游 NVCF 错误, 但 6h SR 仍为 99.5%, 无 key 级劣化、无 fallback、无 429。

### 30min 窗口 — nv_requests
- 总量 103, 200=101, err=2, **SR=98.1%** (101/103)
- Avg/P50/P95: 19239ms / 13681ms / 55893ms (延迟偏中高, 因含 2 个长尾错误拉高 avg/p95)
- 错误分类: all_tiers_exhausted=1 (35070ms, k0), buffer_exhausted=1 (79860ms, k4)
- upstream: nvcf_pexec 全部, integrate 0
- finish_reason: tool_calls=85, stop=16 (正常工具调用型负载)
- 429: **0**, key_cycle_429s: k0=33, k1=70 (正常轮转计数)

### 30min per-key 200 延迟
| key | n | avg_ok_ms | max_ok_ms |
|-----|---|-----------|-----------|
| 0   | 18 | 19951     | 53254     |
| 1   | 19 | 18585     | 45662     |
| 2   | 21 | 18328     | 50403     |
| 3   | 19 | 11782     | 24541     |
| 4   | 24 | 22738     | 57566     |

5 key 负载均匀, 延迟 11.8-22.7s avg 同量级, 无单 key 劣化 (最大 k4=22.7s 仍在 pexec
正常范围)。注意此窗口单个成功请求 max 高达 53-57s — 属 pexec 长时推理的正常长尾。

### 90min 详尽错误审计 (tier_attempts + nv_requests)
- **22:44:20** buffer_exhausted (58s) — 请求级 buffer 耗尽
- **22:44:40** stream_no_content_gap (k1, 138s) — 流中无内容间隔
- **22:47:03** buffer_exhausted (k4, 79.8s)
- **22:47:23** all_tiers_exhausted (k0, 35s)
- **23:06:49** buffer_exhausted (167s)
- 全部 `fallback_occurred=false`, `fallback_actually_attempted=false`
- tier_attempts 2h: pexec_success=361, **NVCFPexecRemoteDisconnected=6 (avg 35s)**,
  **NVCFPexecTimeout=3 (avg 53s, max 57s)** → 根因是上游 NVCF 断连/超时的瞬时簇, 非 key 级配置问题

### 6h / 3h / 24h 趋势
- **6h: 1980 总, 1970 ok, SR=99.5%**, 10 err, 0 429
- 3h 逐小时: 23:00=49/49(100%), 22:00=265/262(98.9%), 21:00=355/355(100%),
  20:00=305/305(100%) → 错误簇集中在 22:44-22:47 (3 次) + 23:06, 瞬时波动
- 24h all_tiers_exhausted: 62 (早前劣化累积, 本 30min 窗口 1)

### Fallback 日志 (hm4104, 近 5min)
- **无 fallback 日志** — 端到端无降级。502 直接返回调用方, 无 zombie/breaker-skip。

## 2. 决策: NOP (无参数修改)

**依据:**
1. **SR 达标**: 30min SR=98.1%, 6h SR=99.5% (1970/1980), 远超 95% 阈值。
2. **错误为上游瞬时 NVCF 断连**: tier_attempts 根因 = NVCFPexecRemoteDisconnected(6) +
   NVCFPexecTimeout(3), 均集中在 22:44-22:47 + 23:06 的瞬时簇。**非本容器 env 可修的
   系统性/ key 级问题** — UPSTREAM_TIMEOUT=50→更高只会烧更多预算在死连上
   (见 nvcf-pexec-timeout 桶分析经验), 改低/改 fastbreak 都无依据。
3. **0 429 / 0 fallback**: 无 key 冷却压力, 无降级。key_cycle_429s 计数低 (0-70)。
4. **5 key 均匀**: 成功请求 5 key 负载 18-24 次、延迟 11.8-22.7s 同量级, 无单 key 劣化。
5. **错误绝对值小**: 90min 仅 5 次 502, 2h tier 层 9 次失败 vs 361 次成功 (~2.4%)。
   属随机上游抖动的正常水平, 不需调参。
6. **一次只改一个参数**: 当前无任何单参数改动可干净归因地改善瞬时 NVCF 抖动。NOP 最稳。

当前实际 env 值维持: UPSTREAM_TIMEOUT=50, TIER_COOLDOWN_S=90, KEY_COOLDOWN_S=30,
NVU_KEYMGR_429_BASE/MAX_COOLDOWN=120, NVU_KEYMGR_CONN_BASE_COOLDOWN=30,
NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3, NVU_TIER_BUDGET_DSV4F_NV=180,
TIER_TIMEOUT_BUDGET_S=180 — 全部不变。

## 3. 当前状态 (30min 主指标 + 6h 趋势)

- 30min SR: **98.1%** (101/103) / **6h SR: 99.5%** (1970/1980)
- Avg/P50/P95: 19239ms / 13681ms / 55893ms
- 错误 (30min): all_tiers_exhausted=1, buffer_exhausted=1
- 429: 0
- upstream: pexec 全部, integrate 0
- fallback: 0 (hm4104 5min 无任何 fallback 日志)

## 4. 上次修改效果 (R1031 NOP → 本轮)

- **SR 略降但达标**: 100% (R1031 30min) → **98.1%** (本轮); 6h 从 99.5% → **99.5%** 持平。
- 本轮为更低流量窗口 (188→103 req), 2 次瞬时上游 NVCF 断连 (k0/k4) 属随机抖动,
  与 R1029 曾出现的 k0 死链/k1 IncompleteRead 同性质的瞬时波动, 非模式化劣化。
- **fallback 清零持续**: 0 (R1031) → **0** (本轮); 429=0 持续。
- 5 key 均匀性维持: 无单 key 持续劣化, R1031 均匀状态保持。

## 5. 下一步建议

1. **维持现状**: 98%+ SR + 0 fallback + 0 429 为健康稳态, 不改参数。
2. **持续监控下探**: 若 30min 内同一 error_type 持续 >3 或 6h SR 跌破 98%, 才考虑
   UPSTREAM_TIMEOUT / key 冷却微调。当前 NVCFRemoteDisconnected 瞬时簇已在 30min 内收敛。
3. **若单 key 延迟持续 >30s 或跨窗口错误集中**: 才考虑 key 级冷却 / integrate 通路重分配;
   本轮 5 key 均匀无此需求。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] 数据完整: 30min SR/延迟/错误分布/fallback/6h 趋势/24h 均已采集
- [x] 详尽错误审计: 90min 5 次 502 全部核实 (buffer_exhausted/all_tiers_exhausted/
      stream_no_content_gap), 根因为上游瞬时 NVCF 断连/超时, fallback 均为 false
- [x] per-key 5 key 均匀, 无单 key 劣化
- [x] hm4104 近 5min 无 fallback 日志, 端到端无降级
- [x] 决策数据驱动: SR 达标 + 错误为瞬时上游抖动 + 0 429 + 0 fallback → NOP