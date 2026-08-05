# R1022: RemoteDisconnected 风暴延续 — 模型特异性劣化（deepseek-v4-flash function 级）无参数修改 (恢复观察轮)

> 时间: 2026-08-05 08:05 BJT (00:05 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 flash via NVCF)
> 状态: **恢复观察轮 (无参数修改)** — RemoteDisconnected 远程瞬断持续主导, 且证实为**模型特异性**
>   (同容器同 key 同出口 glm5_2_nv/dsv4p_nv 100% 成功) → NVCF function 级劣化, 无本容器可解参数
> Fallback: hm4104 持续 fallback 到 dsv4f0731_ms (primary 502/超时触发)

## 1. 背景 (改前必有数据)

R1021 已记录同一 RemoteDisconnected 风暴 (23:55 UTC) 并判定 NOP。本轮 (00:05 UTC,
间隔 ~10min) 为**同一风暴延续**, 关键新发现: 劣化为**模型特异性**。

### 30min 窗口 — nv_requests (tier_model=dsv4f0731_nv)
- 总量 17, 200=8, 502=9, **SR=47.0%** (与 R1021 同窗一致)
- Avg/P50/P95: 61246ms / 62138ms / 142393ms
- fallback_occurred: 17/17 均未本容器 fallback (R753 无跨模型 fallback), 上层 hm4104 转 ms_gw

### 30min tier_attempts 失败细分 (per-attempt 层)
- **NVCFPexecRemoteDisconnected: 16 (绝对主导)**
- empty_200: 2
- 529_nv_overloaded: 1
- 请求层 all_tiers_exhausted: 7 (每请求烧尽 5 key)

### ⭐ 关键证据 — 模型特异性 (同容器同窗)
| tier_model | total | ok | SR |
|---|---|---|---|
| glm5_2_nv   | 78   | 78 | **100%** |
| dsv4p_nv    | 30   | 30 | **100%** |
| dsv4f0731_nv | 18  | 9  | **50%** |

- 同一容器、同一 5 组 NVU_KEY、同一 5 个 mihomo 出口 (7894/7895/7896/7897/7904)
- egress_ip 全 NULL 无法做出口级分层, 但 glm5_2_nv/dsv4p_nv 同链路 100% 成功
- **结论: 故障隔离到 deepseek-v4-flash 的具体 NVCF function (`52e1ddb6-c74...`),
  非网络/key/出口/本容器参数问题**

### 容器日志交叉验证 (08:07-08:10)
- k1 首试成功 (08:07:40→08:08:07), k2 首试成功 (08:08:11→08:08:27)
- k3 → 529 (08:08:33), k4 → conn error (35s), k5 → conn error (74s) → 2 连续 → fast-break
- single tier 烧 109983ms → NV-ALL-TIERS-FAIL → NV-PEER-FB skip (dsv4f0731_nv in peer-fb skip list)
- 同窗口内同 key 有成功也有失败 → 间歇性瞬断, 非持续死锁

## 2. 决策: 无参数修改 (恢复观察轮)

**依据:**
1. **模型特异性已证实** — glm5_2_nv/dsv4p_nv 同容器同 key 同出口 100% 成功, 仅
   deepseek-v4-flash function 失败。这不是 mihomo/网络/出口问题 (否则所有模型都挂)。
2. **远程 TLS-EOF 非任何容器参数可消除** — up/downstream timeout、key cooldown、
   budget、fast-break 均无法把 NVCF 侧 reset 连接变成成功。CONN_ERR_FAST_BREAK=2 已在爆发时
   省 budget。
3. **function 级劣化无法在容器侧缓解** — 除非冗余替代 function/upstream, 但那是架构层,
   超出自优化参数范围, 且 R1017 已 revert integrate lane。
4. **改前必有数据**: 无单一参数有数据支撑可提升 SR。改任何 cooldown/timeout 只会徒增
   归因噪声。

## 3. 当前状态 (30min 主指标)

- 30min SR: **47.0%** (8/17), 与 R1021 持平 (风暴持续)
- Avg/P50/P95: 61246ms / 62138ms / 142393ms
- 错误分布: NVCFPexecRemoteDisconnected=16, empty_200=2, 529_nv_overloaded=1 (per-attempt)
- 请求层: all_tiers_exhausted=7, zombie_empty_completion=1
- 429: 0 (非 429 主导)
- upstream: pexec 17/200=8, integrate 0
- fallback: hm4104 持续 fallback 到 ms_gw (primary 502/超时触发)

## 4. 上次修改效果 (R1021 观察轮)

- 无参数修改, 无参数效果可评
- 新增关键发现: 劣化**模型特异性** — 仅 deepseek-v4-flash function 受影响,
  glm5_2_nv/dsv4p_nv 同环境 100% 成功 → 隔离到 function 级, 非网络/出口

## 5. 下一步建议

1. **若 RemoteDisconnected 持续 >70% 且仅 dsv4f0731_nv 受影响**: 确认是 NVCF
   deepseek-v4-flash function 上游劣化, 无容器参数可解。
2. **若持续恶化**: 评估架构层缓解 — 备用 NVCF function_id / 切换到 peer 的 function /
   或依赖 hm4104→ms_gw fallback (当前最稳路径)。
3. **下一轮触发条件**: SR≥95% 且 RemoteDisconnected 消失 → NOP; 若出现**单 key** 劣化
   (非均匀跨 key) → 才考虑 key 级参数; 若 storm 持续 → 维持观察, 等待 NVCF function 恢复。

## 验证清单
- [x] /health 未改动 (无参数修改, 无需重启)
- [x] 数据完整: 30min SR/延迟/错误分布/fallback 均已采集
- [x] 决策数据驱动: 模型特异性 (glm5_2_nv/dsv4p_nv 100% vs dsv4f0731_nv 50%)
  证实 function 级劣化 → NOP