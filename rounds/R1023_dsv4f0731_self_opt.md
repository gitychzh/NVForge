# R1023: RemoteDisconnected 风暴延续 — 模型特异性劣化持续 (deepseek-v4-flash function 级) 无参数修改 (恢复观察轮)

> 时间: 2026-08-05 08:50 BJT (00:50 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 flash via NVCF)
> 状态: **恢复观察轮 (无参数修改)** — RemoteDisconnected 远程瞬断持续主导, 且再次证实为**模型特异性**
>   (同容器同 key 同出口 glm5_2_nv 100% 成功) → NVCF deepseek-v4-flash function 级劣化, 无本容器可解参数
> Fallback: hm4104 持续 fallback 到 dsv4f0731_ms (primary 502/超时触发)

## 1. 背景 (改前必有数据)

R1021/R1022 已记录同一 RemoteDisconnected 风暴并判定模型特异性 NOP。本轮 (间隔 ~45min)
为**同一风暴延续**, 关键证据再次确认劣化为**模型特异性**, 且 529 阶段已过去 (转向 RemoteDisconnected 主导)。

### 30min 窗口 — nv_requests (当前)
- 总量 18, 200=14, 502=4, **SR=77.8%** (较 R1022 47% 回升, 但仍远低于正常)
- Avg/P50/P95: 60298ms / 60030ms / 125335ms
- finish_reason: tool_calls=9, stop=5 (正常业务流量)
- 429: 0 (非 429 主导)

### 30min tier_attempts 失败细分 (per-attempt 层)
- **NVCFPexecRemoteDisconnected: 31 (绝对主导)**
- empty_200: 4
- 529_nv_overloaded: 3
- 请求层 all_tiers_exhausted: 4 (每请求烧尽 5 key)

### ⭐ 关键证据 — 模型特异性复现 (同容器同窗)
| tier_model | total | ok | SR |
|---|---|---|---|
| glm5_2_nv    | 87   | 87 | **100%** |
| dsv4f0731_nv | 17   | 11 | **64.7%** |

- 同一容器、同一 5 组 NVU_KEY、同一 5 个 mihomo 出口 (7894/7895/7896/7897/7904)
- glm5_2_nv 同链路 100% 成功 → 故障隔离到 deepseek-v4-flash 的具体 NVCF function,
  非网络/key/出口/本容器参数问题

### 24h trend (nv_tier_attempts, dsv4f0731_nv 逐小时)
| hour (UTC) | RemoteDisconnected | 529 | empty_200 | total |
|---|---|---|---|---|
| 00:00 | 28 | 2 | 3 | 33 |
| 23:00 | 32 | 2 | 4 | 38 |
| 22:00 | 33 | 3 | 3 | 39 |
| 21:00 | 28 | 5 | 5 | 38 |
| 20:00 | 15 | **113** | 1 | 135 |
| 19:00 | 16 | **191** | 0 | 207 |
| 18:00 |  9 | **118** | 2 | 129 |

- 18:00-20:00 UTC 为 529 过载阶段 (113-191/hr), 21:00 后转向 RemoteDisconnected 主导 (28-33/hr)
- 当前为 RemoteDisconnected 主导阶段, 每请求烧尽 5 key → all_tiers_exhausted

## 2. 决策: 无参数修改 (恢复观察轮)

**依据:**
1. **模型特异性再次证实** — glm5_2_nv 同容器同 key 同出口 100% 成功, 仅
   deepseek-v4-flash function 失败。这不是 mihomo/网络/出口问题 (否则所有模型都挂)。
2. **远程 TLS-EOF 非任何容器参数可消除** — up/downstream timeout、key cooldown、
   budget、fast-break 均无法把 NVCF 侧 reset 连接变成成功。
3. **function 级劣化无法在容器侧缓解** — 除非冗余替代 function/upstream, 但那是架构层,
   超出自优化参数范围。
4. **改前必有数据**: 无单一参数有数据支撑可提升 SR。改任何 cooldown/timeout 只会徒增
   归因噪声。glm5_2_nv 100% 已把变量隔离干净。

## 3. 当前状态 (30min 主指标)

- 30min SR: **77.8%** (14/18), 较 R1022 47% 回升 (风暴仍在, 但略缓和)
- Avg/P50/P95: 60298ms / 60030ms / 125335ms
- 错误分布: NVCFPexecRemoteDisconnected=31, empty_200=4, 529_nv_overloaded=3 (per-attempt)
- 请求层: all_tiers_exhausted=4
- 429: 0 (非 429 主导, key_cycle_429s 全 0)
- upstream: pexec 18/200=14, integrate 0
- fallback: hm4104 持续 fallback 到 ms_gw (primary 502/超时触发)

## 4. 上次修改效果 (R1022 观察轮)

- 无参数修改, 无参数效果可评
- SR 47% → 77.8% (30min 窗口), 为风暴自然波动, 非任何参数效应
- 模型特异性证据持续成立 (glm5_2_nv 100%)

## 5. 下一步建议

1. **若 RemoteDisconnected 持续 >60% 且仅 dsv4f0731_nv 受影响**: 确认是 NVCF
   deepseek-v4-flash function 上游劣化, 无容器参数可解。
2. **若持续恶化**: 评估架构层缓解 — 备用 NVCF function_id / 切换到 peer 的 function /
   或依赖 hm4104→ms_gw fallback (当前最稳路径)。
3. **下一轮触发条件**: SR≥95% 且 RemoteDisconnected 消失 → NOP; 若出现**单 key** 劣化
   (非均匀跨 key) → 才考虑 key 级参数; 若 storm 持续 → 维持观察, 等待 NVCF function 恢复。

## 验证清单
- [x] /health 未改动 (无参数修改, 无需重启)
- [x] 数据完整: 30min SR/延迟/错误分布/fallback 均已采集
- [x] 决策数据驱动: 模型特异性 (glm5_2_nv 100% vs dsv4f0731_nv 64.7%) 证实 function 级劣化 → NOP