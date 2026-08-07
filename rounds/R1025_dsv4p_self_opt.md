# R1025: RemoteDisconnected 风暴完全收敛, SR 97.3% 稳定 — NOP (恢复后首轮健康确认)

> 时间: 2026-08-07 15:08 UTC
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
> 状态: **NOP (无参数修改)** — SR>95%, 无异常错误, 延迟稳定
> Fallback: hm4104 近 5min 无 fallback 日志 (0 次)

## 1. 背景 (改前必有数据)

R1023-R1024 处于 RemoteDisconnected 远程瞬断风暴 (40min 16 次, SR 60-66%)。
本轮 30min 窗口显示 **风暴已完全收敛**：RemoteDisconnected 归零, SR 回升至 **97.1%** (30min) / **97.3%** (6h)，
为 R1017 以来首个高健康确认轮。

### 30min 窗口 — nv_requests (live 查询)
- 总量 140, 200=136, err=4, **SR=97.1%** (较 R1024 同窗 60% 大幅回升)
- Avg/P50/P95: 17860ms / 9787ms / 50463ms (延迟健康, p50 个位数秒)
- 错误 (4 个): zombie_empty_completion=2, all_tiers_exhausted=1, stream_absolute_cap=1
  - 均为孤立残余, 无 RemoteDisconnected / NVStream_IncompleteRead 主导特征
- upstream: pexec 全部 (140/140), integrate 0
- finish_reason: tool_calls=118, stop=18 (正常工具调用型负载)
- 429: **0**, key_cycle_429s: k0=14, k1=123, k2=1, k3=2 (k1 cycle 计数高但无实际 429 失败, 轮转正常)

### 30min per-key 200 延迟
| key | n | avg_ok_ms | max_ok_ms |
|-----|---|-----------|-----------|
| 0   | 31 | 21567     | 88310     |
| 1   | 26 | 10181     | 16221     |
| 2   | 22 | 11154     | 23602     |
| 3   | 28 | 14850     | 44046     |
| 4   | 29 | 17051     | 49403     |

5 key 全部活跃健康, 延迟均匀 (10-21s avg), 无单 key 劣化。错误跨 k0/k4 各 2 个, 均匀。

### 6h / 3h / 24h 趋势
- **6h: 1620 总, 1576 ok, SR=97.3%**, 44 err, 0 429
- 3h 逐小时: 07:00=38/40(95%), 06:00=265/273(97%), 05:00=243/249(97.6%), 04:00=238/242(98.3%)
  → SR 稳定 95-98%, 无退化
- 24h all_tiers_exhausted: 356 (早前 RemoteDisconnected 风暴累积, 本窗已归零)

### Fallback 日志 (hm4104, 最近 5min)
- **无 fallback 日志** — 主链路健康, 未触发 fallback

### Per-key 错误
- k0: all_tiers_exhausted=1 + zombie_empty_completion=1
- k4: stream_absolute_cap=1 + zombie_empty_completion=1
- 均匀跨 key, 非单 key 劣化

## 2. 决策: NOP (无参数修改)

**依据 (SR>95% 达标):**
1. **30min SR=97.1% (136/140), 6h SR=97.3% (1576/1620)** — 远超 95% 阈值, 高健康。
2. **RemoteDisconnected 完全归零** — R1023-R1024 主导的远程瞬断风暴彻底收敛, 本窗 0 次。
3. **429=0, fallback=0** — 无任何冷却/轮转/fastbreak 压力, key_cycle_429s 计数为正常轮转非失败。
4. **延迟健康** — p50 9787ms, 5 key avg 10-21s 均匀, 无单 key 劣化。
5. **错误仅 4 个孤立残余** (zombie_empty_completion=2, all_tiers_exhausted=1, stream_absolute_cap=1),
   均匀跨 k0/k4, 非本容器参数可归因。
6. **改前必有数据**: 无任何数据支持参数改动 — 链路已自行恢复至健康态, 不应扰动。

## 3. 当前状态 (30min 主指标 + 6h 趋势)

- 30min SR: **97.1%** (136/140) / **6h SR: 97.3%** (1576/1620)
- Avg/P50/P95: 17860ms / 9787ms / 50463ms
- 错误 (30min): zombie_empty_completion=2, all_tiers_exhausted=1, stream_absolute_cap=1
- 429: 0
- upstream: pexec 全部 (140/140), integrate 0
- fallback: **0** (hm4104 近 5min 无 fallback)

## 4. 上次修改效果 (R1024 观察轮 / R1017 revert integrate lane)

- **RemoteDisconnected 风暴完全收敛**: 40min 16 次 → 0 次 (R1024→R1025)
- **SR 大幅回升稳定**: 60% (R1024 30min) / 61.4% (R1023 6h) → **97.1% (30min) / 97.3% (6h)**
- **fallback 归零**: R1024 触发 1 次 → 本轮 0 次
- integrate upstream 保持归零, 5-key pexec 池冗余完整, 无参数扰动下自然恢复

## 5. 下一步建议

1. **维持现状**: 链路已恢复至健康稳态, 无参数改动需求。继续监测 SR 是否保持 ≥95%。
2. **若 SR 持续 ≥95%**: 连续多轮 NOP 确认稳态后, 可评估是否将 integrate lane
   (NV_KEY_INTEGRATE_KEYS) 重新启用以增加上游协议冗余 — 但需先确认 pexec 单 lane 已稳定数日。
3. **若 RemoteDisconnected 复发**: 属 NVCF 上游/mihomo 出口到 NVCF 的远程瞬断, 无本容器参数可解,
   评估是否需额外 NVCF egress IP 池 / 冗余 upstream provider。
4. **单 key 延迟方差**: 当前 5 key avg 10-21s 均匀, 无需调整; 若未来某 key avg 持续 >30s
   或错误集中, 才考虑 key 级冷却调整。

## 验证清单
- [x] /health 正常 (pre-collection + live: status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] 数据完整: 30min SR/延迟/错误分布/fallback/6h 趋势/24h 均已采集
- [x] 决策数据驱动: SR=97.3% (6h), 429=0, fallback=0, RemoteDisconnected 归零 → NOP