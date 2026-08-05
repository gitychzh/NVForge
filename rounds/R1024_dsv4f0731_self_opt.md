# R1024: RemoteDisconnected 风暴延续 (第3轮) — 模型特异性劣化持续, 无参数修改 (恢复观察轮)

> 时间: 2026-08-05 09:00 BJT (01:00 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 flash via NVCF)
> 状态: **恢复观察轮 (无参数修改)** — NVCFPexecRemoteDisconnected 远程瞬断持续主导 (>85% 失败),
>   且再次复现**模型特异性** (同容器同 key 同出口 glm5_2_nv 99.5%) → NVCF deepseek-v4-flash
>   function 级劣化, 无本容器可解参数
> Fallback: hm4104 持续 fallback 到 dsv4f0731_ms (primary 502/超时触发, 30min 502=7)

## 1. 背景 (改前必有数据)

R1021/R1022/R1023 已连续记录同一 RemoteDisconnected 风暴并判定模型特异性 NOP。本轮 (间隔
~10min) 为**同一风暴第 3 轮延续**, 数据完全复现 R1023 结论。

### 30min 窗口 — nv_requests (当前, tier_model=dsv4f0731_nv)
- 总量 13, 200=6, 502=7, **SR=46.2%** (采集脚本时刻 15 请求 9/15=60%; 窗口漂移后 46.2%)
- Avg/P50/P95: 70695ms / 67132ms / 114441ms
- 429: 0 (key_cycle_429s 全 0, 非 429 主导)

### 1h tier_attempts 失败细分 (per-attempt 层)
- **NVCFPexecRemoteDisconnected: 30 (绝对主导, >85%)**
- empty_200: 3, 529_nv_overloaded: 2, pexec_429: 1
- 成功标记: pexec_success=182 (主要是 glm5_2_nv)

### ⭐ 关键证据 — 模型特异性复现 (同容器同窗 1h)
| tier | total | ok | SR |
|---|---|---|---|
| glm5_2_nv    | 183 | 182 | **99.5%** |
| dsv4f0731_nv |  35 |   0 | 0.0% (per-attempt 层) |

- 同一容器、同一 5 组 NVU_KEY、同一 5 个 mihomo 出口 (7894/7895/7896/7897/7904)
- glm5_2_nv 同链路 99.5% 成功 → 故障隔离到 deepseek-v4-flash 的具体 NVCF function,
  非网络/key/出口/本容器参数问题
- 请求层 dsv4f0731_nv 31 请求 20 成功 (SR 64.5% 1h) — 部分请求经 fallback / tier 重试恢复

### per-key 均匀劣化 (非单 key 问题)
| key | ok | total | SR |
|---|---|---|---|
| 0 | 0 | 5 | 0 |
| 1 | 0 | 6 | 0 |
| 2 | 0 | 8 | 0 |
| 3 | 0 | 9 | 0 |
| 4 | 0 | 7 | 0 |

- 5 key 全部均匀失败 (RemoteDisconnected 30 次均匀分布) → 确认非某 key/某出口劣化,
  而是 NVCF function 全局性问题

### 6h 逐小时 trend (nv_tier_attempts, dsv4f0731_nv)
| hour (UTC) | RemoteDisconnected | total |
|---|---|---|
| 19:00 | 15 | 202 |
| 20:00 | 15 | 135 |
| 21:00 | 28 | 38 |
| 22:00 | 33 | 39 |
| 23:00 | 32 | 38 |
| 00:00 | 32 | 37 |

- 19-20h 为 529 过载阶段 (202/135 attempts), 21h 后转向 RemoteDisconnected 主导 (28-33/hr)
- RemoteDisconnected 持续高位 (28-33/hr), 风暴未缓解

### 24h all_tiers_exhausted (请求层 502)
- 24h 内 101 次 (R1023 采集时刻 94, 持续累积)

### hm4104 fallback 日志 (最近 5min)
- PRIMARY-FAIL-STREAM: nv_gw 流式 502 after 69622ms → 切 fallback
- PRIMARY-BREAKER-SKIP-STREAM: primary 跳过 (circuit OPEN) → 直走 fallback
- 表明 primary dsv4f0731_nv 当前断连多, hm4104 已大量 fallback 到 ms_gw

## 2. 决策: 无参数修改 (恢复观察轮)

**依据:**
1. **模型特异性第 3 次复现** — glm5_2_nv 同容器同 key 同出口 99.5% 成功, 仅
   deepseek-v4-flash function 失败。这不是 mihomo/网络/出口/key 问题 (否则所有模型都挂)。
2. **远程 TLS-EOF 非任何容器参数可消除** — up/downstream timeout、key cooldown、budget、
   fast-break 均无法把 NVCF 侧 reset 连接变成成功。
3. **5 key 均匀失败** — 无单 key 劣化, 排除 key 级参数 (cooldown/429 管理) 可优化空间。
4. **改前必有数据**: 无单一参数有数据支撑可提升 SR。glm5_2_nv 99.5% 已把变量隔离干净。
   改任何 cooldown/timeout 只会徒增归因噪声。

## 3. 当前状态 (30min 主指标)

- 30min SR: **46.2%** (6/13), 与 R1023 77.8% 相比回落 (风暴自然波动, 采集时刻 60%)
- Avg/P50/P95: 70695ms / 67132ms / 114441ms
- 错误分布 (per-attempt 1h): NVCFPexecRemoteDisconnected=30, empty_200=3, 529_nv_overloaded=2
- 请求层: all_tiers_exhausted (502) 30min=7, 24h=101
- 429: 0 (非 429 主导, key_cycle_429s 全 0)
- upstream: pexec 主导, integrate 0 (NV_KEY_INTEGRATE_KEYS 空)
- fallback: hm4104 大量 fallback 到 ms_gw (circuit OPEN + 502)

## 4. 上次修改效果 (R1023 观察轮)

- 无参数修改, 无参数效果可评
- SR 77.8% → 46.2% (30min 窗口), 为风暴自然波动, 非任何参数效应
- 模型特异性证据持续成立 (glm5_2_nv 99.5%), 5 key 均匀劣化确认

## 5. 下一步建议

1. **若 RemoteDisconnected 持续 >60% 且仅 dsv4f0731_nv 受影响**: 确认是 NVCF
   deepseek-v4-flash function 上游劣化, 无容器参数可解。
2. **若持续恶化**: 评估架构层缓解 — 备用 NVCF function_id / 切换到 peer 的 function /
   或依赖 hm4104→ms_gw fallback (当前最稳路径)。
3. **下一轮触发条件**: SR≥95% 且 RemoteDisconnected 消失 → NOP; 若出现**单 key** 劣化
   (非均匀跨 key) → 才考虑 key 级参数; 若 storm 持续 → 维持观察, 等待 NVCF function 恢复。

## 验证清单
- [x] /health 未改动 (无参数修改, 无需重启)
- [x] 数据完整: 30min SR/延迟/错误分布/fallback/per-key 均已采集
- [x] 决策数据驱动: 模型特异性 (glm5_2_nv 99.5% vs dsv4f0731_nv 0%) 证实 function 级劣化 → NOP