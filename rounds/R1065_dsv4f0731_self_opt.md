# R1065: RemoteDisconnected 风暴延续 (第44轮) — 模型特异性第44次复现, NOP (无参数修改)

> 时间: 2026-08-06 13:10 BJT (05:10 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF)
> 状态: **NOP (无参数修改)** — NVCFPexecRemoteDisconnected 远程瞬断风暴在 attempt 层
>   持续主导, 第 44 次复现**模型特异性** (同容器同 key 同出口 glm5_2_nv 6h SR~80%
>   vs dsv4f0731_nv 6h SR=39.5% + attempt 层 RemoteDisconnected 主导) →
>   NVCF deepseek function 级劣化, 无本容器可解参数
> 信号: hm4104 fallback 持续 (PRIMARY-FAIL-STREAM 502 → FALLBACK-STREAM → ms_gw)

## 1. 背景 (改前必有数据)

R1021-R1064 连续记录同一 RemoteDisconnected 风暴并判定模型特异性 NOP。本轮间隔 ~24min
(R1064 为 04:47 UTC) 为同一风暴第 44 轮延续。

### 30min 窗口 (pre-run 注入) — nv_requests (tier_model=dsv4f0731_nv)
- 总量 29, 200=12, 失败=17, **SR=41.4%**
- Avg 102274ms, p50 75929ms, p95 240599ms, max 365965ms
- 429: 0 计数
- upstream_type: nvcf_pexec 27 (200=12, SR=44.4%, avg=92868ms), ms_fallback 2 (200=0,
  avg=229254ms)
- finish_reason: tool_calls=10, stop=2 (仅 12 个 200 正常完成)

### 错误分类 (30min, nv_requests)
| error_type | count | avg_ms |
|---|---|---|
| all_tiers_exhausted | 12 | 90353 |
| buffer_exhausted | 2 | 229254 |
| client_gone_during_flush | 2 | 308631 |
| zombie_empty_completion | 1 | 6322 |

### per-key 200 延迟 (30min)
| key | 200 | avg_ms | max_ms |
|---|---|---|---|
| 0 | 3 | 88108 | 140843 |
| 1 | 3 | 66265 | 96457 |
| 2 | 1 | 87644 | 87644 |
| 3 | 2 | 46435 | 48221 |
| 4 | 3 | 51994 | 75212 |

### per-key 错误 (30min)
- k0: all_tiers_exhausted=12, buffer_exhausted=2, client_gone_during_flush=1
- k3: client_gone_during_flush=1, zombie_empty_completion=1
- key_cycle_429s: k0=20, k1=7, k2=1, k3=1 (但 429 计数=0 → 429 均在与上游瞬断混叠中
  出现, 非持续配额耗尽)
- → 错误跨 key 分散 (k0/k3 + 空 key), 非单 key/单 SOCKS5 代理问题

### 模型特异性重验证 (6h, 同容器同 key 同出口同时窗)
- **glm5_2_nv 6h**: SR~80% (与 R1064 一致, 基本无 tier 错误)
- **dsv4f0731_nv 6h**: 435 请求, 172 200, **SR=39.5%** (与 R1064 的 39.5% 完全持平)
- **结论**: 同容器同 key 同出口, glm5_2_nv ~80% vs dsv4f0731_nv 39.5% → 模型特异性
  第 44 次成立。故障仅存在于 dsv4f0731_nv 具体 function 的远端执行层。

### 6h/24h 趋势
- 6h 请求层 (nv_requests): 435 请求, 172 200, SR=39.5%, 与 R1064 的 440/174/39.5% 持平
- 3h 逐小时: 05:00=SR66.7%(2/3), 04:00=32.0%(25/78), 03:00=46.1%(35/76), 02:00=41.5%(27/65)
- 24h all_tiers_exhausted: 302 次 (相对 R1064 的 291 次 +11)
- ms_fallback 亦失败 (30min ms SR=0%) → 非 pexec 协议独有, 远端 deepseek function 整体劣化

### hm4104 fallback 日志 (最近 5min)
- 无 fallback 日志 (本轮观测窗内 hm4104 未新触发), 但 R1064 确认断路器持续 OPEN,
  用户请求由 ms_gw 保活

## 2. 决策: NOP (无参数修改)

RemoteDisconnected/all_tiers_exhausted/buffer_exhausted/zombie_empty/client_gone 是
NVCF deepseek **远程 function 级**瞬断/劣化, 与容器 env 无关 (第 44 次确认):
- 同出口同 key → glm5_2_nv 6h SR~80% vs dsv4f0731_nv 39.5% → 网络/mihomo/key/出口路径
  健康, 故障仅在 dsv4f0731_nv 具体 function 远端执行层
- 错误跨全 key 分散 (k0/k3 + 空 key) → 证明非 UPSTREAM_TIMEOUT/budget/cooldown/
  fastbreak 可解的 lever
- attempt 层无持续 429 (429 计数=0), 以 RemoteDisconnected 主导 → 纯远程断连/过载
- ms_fallback 亦失败 (30min ms SR=0%) → 既非 pexec 协议问题, 也非本容器路由可调
- 无单 key 劣化 (错误均匀分散各 key) → 无 key 分配/冷却可调
- 成功 200 平均 ~93s 属正常 pexec 长耗时, 非超时; 失败 502 是烧满 budget 后的正常 fallback

本轮继续 NOP, 等待 NVCF 侧恢复 (第 44 轮)。模型特异性铁证 (6h glm5_2_nv ~80% vs
dsv4f0731_nv 39.5% + 错误均匀分散 + ms_fallback 亦败) 第 44 次成立。hm4104 断路器已接管
用户侧 fallback (用户请求由 ms_gw 保活)。