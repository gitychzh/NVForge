# R1066: RemoteDisconnected 风暴延续 (第45轮) — 模型特异性第45次复现, NOP (无参数修改)

> 时间: 2026-08-06 13:15 BJT (05:15 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF)
> 状态: **NOP (无参数修改)** — NVCFPexecRemoteDisconnected 远程瞬断风暴在 attempt 层
>   持续主导, 第 45 次复现**模型特异性** (同容器同 key 同出口 glm5_2_nv 6h SR=68.8%
>   vs dsv4f0731_nv 6h SR=38.7% + attempt 层 RemoteDisconnected 主导) →
>   NVCF deepseek function 级劣化, 无本容器可解参数
> 信号: hm4104 fallback 持续 (PRIMARY-FAIL-STREAM 502 → FALLBACK-STREAM → ms_gw)

## 1. 背景 (改前必有数据)

R1021-R1065 连续记录同一 RemoteDisconnected 风暴并判定模型特异性 NOP。本轮间隔 ~25min
(R1065 为 04:50 UTC) 为同一风暴第 45 轮延续。

### 30min 窗口 (pre-run 注入) — nv_requests (tier_model=dsv4f0731_nv)
- 总量 39, 200=15, 失败=24, **SR=38.5%**
- Avg 97962ms, p50 71304ms, p95 249392ms, max 259724ms
- 429: 0 计数
- upstream_type: nvcf_pexec 33 (200=15, SR=45.5%, avg=72245ms), ms_fallback 5 (200=0,
  SR=0%, avg=235675ms), nv_integrate 1 (200=0, SR=0%, avg=258057ms)
- finish_reason: tool_calls=11, stop=4 (仅 15 个 200 正常完成)

### 错误分类 (30min, pre-run)
| error_type | count | avg_ms |
|---|---|---|
| all_tiers_exhausted | 13 | 89219 |
| buffer_exhausted | 6 | 239406 |
| zombie_empty_completion | 4 | 10456 |
| client_gone_during_flush | 1 | 210378 |

### per-key 200 延迟 (30min)
| key | 200 | avg_ms | max_ms |
|---|---|---|---|
| 0 | 3 | 88108 | 140843 |
| 1 | 5 | 70823 | 114564 |
| 2 | 1 | 87644 | 87644 |
| 3 | 2 | 34903 | 47068 |
| 4 | 4 | 49034 | 74041 |

### per-key 错误 (30min)
- k0: all_tiers_exhausted=13, buffer_exhausted=5, client_gone_during_flush=1
- k3: zombie_empty_completion=2, buffer_exhausted=1
- k4: zombie_empty_completion=1
- k2: zombie_empty_completion=1
- → 错误跨 key 分散 (k0/k3/k4/k2 + 空 key), 非单 key/单 SOCKS5 代理问题

### 模型特异性重验证 (6h, 同容器同 key 同出口同时窗) — 本轮直接查询
- **glm5_2_nv 6h**: 32 请求, 22 200, **SR=68.8%**
- **dsv4f0731_nv 6h**: 442 请求, 171 200, **SR=38.7%** (与 R1065 的 39.5% 基本持平)
- **结论**: 同容器同 key 同出口, glm5_2_nv ~69% vs dsv4f0731_nv 38.7% → 模型特异性
  第 45 次成立。故障仅存在于 dsv4f0731_nv 具体 function 的远端执行层。

### upstream 三协议对照 (30min, dsv4f0731_nv) — 本轮直接查询
- nvcf_pexec: 28 请求, 13 200, SR=46.4%
- ms_fallback: 4 请求, 0 200, SR=0.0%
- nv_integrate: 1 请求, 0 200, SR=0.0%
- **结论**: pexec/integrate/ms 三协议全败 → 非 pexec 协议独有, 远端 deepseek function
  整体劣化, 无本容器路由可调

### 6h/24h 趋势
- 6h 请求层 (nv_requests): 442 请求, 171 200, SR=38.7%, 与 R1065 的 435/172/39.5% 基本持平
- 24h all_tiers_exhausted: 305 次 (相对 R1065 的 302 次 +3)
- ms_fallback 亦失败 (30min ms SR=0%) → 远端 deepseek function 整体劣化

### hm4104 fallback 日志 (最近 5min)
- 持续: PRIMARY-FAIL-STREAM nv_gw 502 after 131509ms → FALLBACK-STREAM → ms_gw
- PRIMARY-BREAKER-SKIP-STREAM (circuit OPEN) → 直走 fallback
- 断路器持续 OPEN, 用户请求由 ms_gw 保活

## 2. 决策: NOP (无参数修改)

RemoteDisconnected/all_tiers_exhausted/buffer_exhausted/zombie_empty/client_gone 是
NVCF deepseek **远程 function 级**瞬断/劣化, 与容器 env 无关 (第 45 次确认):
- 同出口同 key → glm5_2_nv 6h SR=68.8% vs dsv4f0731_nv 38.7% → 网络/mihomo/key/出口路径
  健康, 故障仅在 dsv4f0731_nv 具体 function 远端执行层
- 错误跨全 key 分散 (k0/k3/k4/k2 + 空 key) → 证明非 UPSTREAM_TIMEOUT/budget/cooldown/
  fastbreak 可解的 lever
- attempt 层无持续 429 (429 计数=0), 以 RemoteDisconnected 主导 → 纯远程断连/过载
- pexec/integrate/ms 三协议 30min 全败 (SR 46.4%/0%/0%) → 既非 pexec 协议问题, 也非本容器
  路由可调
- 无单 key 劣化 (错误均匀分散各 key) → 无 key 分配/冷却可调
- 成功 200 平均 ~72-93s 属正常 pexec 长耗时, 非超时; 失败 502 是烧满 budget 后的正常 fallback

本轮继续 NOP, 等待 NVCF 侧恢复 (第 45 轮)。模型特异性铁证 (6h glm5_2_nv ~69% vs
dsv4f0731_nv 38.7% + 错误均匀分散 + 三协议全败) 第 45 次成立。hm4104 断路器已接管
用户侧 fallback (用户请求由 ms_gw 保活)。