# R1027: RemoteDisconnected 风暴延续 (第6轮) — 模型特异性劣化持续, 无参数修改 (恢复观察轮)

> 时间: 2026-08-05 10:05 BJT (02:05 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 flash via NVCF)
> 状态: **恢复观察轮 (无参数修改)** — NVCFPexecRemoteDisconnected 远程瞬断持续绝对主导,
>   且第 6 次复现**模型特异性** (同容器同 key 同出口 glm5_2_nv 100% 成功) → NVCF
>   deepseek-v4-flash function 级劣化, 无本容器可解参数
> Fallback: hm4104 持续 fallback 到 dsv4f0731_ms (primary 502/RemoteDisconnected 触发)

## 1. 背景 (改前必有数据)

R1021-R1026 已连续记录同一 RemoteDisconnected 风暴并判定模型特异性 NOP。本轮 (间隔 ~15min)
为**同一风暴第 6 轮延续**, 数据完全复现 R1026 结论。

### 30min 窗口 — nv_requests (采集脚本, tier_model=dsv4f0731_nv)
- 总量 13, 200=7, 502=6, **SR=53.8%** (窗口内业务流量少, 波动大)
- Avg/P50/P95: 64698ms / 67065ms / 129805ms
- 429: 0 (key_cycle_429s 0:10/1:2/3:1, 非 429 主导)
- upstream_type: nvcf_pexec 13/200=7 (全 pexec, integrate 0)

### 1h tier_attempts 失败细分 (per-attempt 层, dsv4f0731_nv)
- **NVCFPexecRemoteDisconnected: 33 (绝对主导)**
- empty_200: 3, 529_nv_overloaded: 2
- 成功标记: 0 (per-attempt 层 dsv4f0731_nv 无成功; 请求层成功经 tier 重试/恢复)

### ⭐ 关键证据 — 模型特异性第 6 次复现 (同容器同窗 1h, 请求层)
| tier_model | total | ok | SR |
|---|---|---|---|
| glm5_2_nv    | 141 | 141 | **100%** |
| dsv4f0731_nv |  24 |  10 | **41.7%** |

- 同一容器、同一 5 组 NVU_KEY、同一 5 个 mihomo 出口 (7894/7895/7896/7897/7904)
- glm5_2_nv 同链路 100% 成功 (per-attempt 全 pexec_success) → 故障隔离到
  deepseek-v4-flash 的具体 NVCF function, 非网络/key/出口/本容器参数问题
- 证据第 6 次成立, 变量隔离彻底干净

### per-key 均匀劣化 (非单 key 问题)
- tier_attempts 层 RemoteDisconnected 均匀分布 5 key (0:4, 1:4, 2:5, 3:2, 4:2)
- 每次失败烧尽 5 key → all_tiers_exhausted (请求层 30min=6)
- key_cycle_429s 低 (0:10/1:2/3:1), 非 429 主导

### 6h 逐小时 trend (请求层, 采集脚本)
- 6h 累积: 223 请求 144 成功 (64.6%)
- 3h 逐小时: 01:00 SR=38.1%, 00:00 SR=62.5%, 23:00 SR=53.1%, 02:00(当前) SR=100% (1/1)
- SR 持续低位波动, 风暴未缓解

### 24h all_tiers_exhausted
- 24h 内 109 次 (R1026 采集时刻 106, 持续累积)

### hm4104 fallback 日志 (最近 5min)
- PRIMARY-FAIL-STREAM: nv_gw 流式 502 after 67073ms → 切 fallback
- FALLBACK-STREAM: 从 primary 切到 ms_gw 流式
- 表明 primary dsv4f0731_nv 断连多, hm4104 已 fallback 到 ms_gw

## 2. 决策: 无参数修改 (恢复观察轮)

**依据:**
1. **模型特异性第 6 次复现** — glm5_2_nv 同容器同 key 同出口 141/141=100% 成功, 仅
   deepseek-v4-flash function 失败。这不是 mihomo/网络/出口/key 问题 (否则所有模型都挂)。
2. **远程 TLS-EOF 非任何容器参数可消除** — up/downstream timeout、key cooldown、budget、
   fast-break 均无法把 NVCF 侧 reset 连接变成成功。
3. **5 key 均匀失败** — 无单 key 劣化, 排除 key 级参数 (cooldown/429 管理) 可优化空间。
4. **改前必有数据**: 无单一参数有数据支撑可提升 SR。glm5_2_nv 100% 已把变量隔离干净。
   改任何 cooldown/timeout 只会徒增归因噪声。

## 3. 当前状态 (30min 主指标)

- 30min SR: **53.8%** (7/13), 较 R1026 50.0% 微升 (窗口波动, 非参数效应)
- Avg/P50/P95: 64698ms / 67065ms / 129805ms
- 错误分布 (per-attempt 1h): NVCFPexecRemoteDisconnected=33, empty_200=3, 529_nv_overloaded=2
- 请求层: all_tiers_exhausted (502) 30min=6, 24h=109
- 429: 0 (非 429 主导, key_cycle_429s 0:10/1:2/3:1)
- upstream: pexec 13/200=7, integrate 0 (NV_KEY_INTEGRATE_KEYS 空)
- fallback: hm4104 fallback 到 ms_gw (502 触发)

## 4. 上次修改效果 (R1026 观察轮)

- 无参数修改, 无参数效果可评
- SR 50.0% → 53.8% (30min 窗口), 为风暴自然波动, 非任何参数效应
- 模型特异性证据第 6 次成立 (glm5_2_nv 100%), 5 key 均匀劣化确认

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
- [x] 决策数据驱动: 模型特异性 (glm5_2_nv 141/141=100% vs dsv4f0731_nv 10/24=41.7%) 证实
      function 级劣化 → NOP