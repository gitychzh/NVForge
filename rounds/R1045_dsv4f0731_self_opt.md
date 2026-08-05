# R1045: RemoteDisconnected 风暴延续 (第24轮) — 模型特异性第24次复现, 无参数修改 (恢复观察轮)

> 时间: 2026-08-05 20:20 BJT (12:20 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF)
> 状态: **恢复观察轮 (无参数修改)** — NVCFPexecRemoteDisconnected 远程瞬断风暴在 attempt 层
>   持续主导, 第 24 次复现**模型特异性** (同容器同 key 同出口 glm5_2_nv 97.9% 成功) →
>   NVCF deepseek function 级劣化, 无本容器可解参数
> **新信号**: 本轮错误分类新增 zombie_empty_completion=1 (上游 200 但无内容), 且 hm4104
>   fallback 仍持续触发 (断路器 OPEN → 用户请求被 fallback 到 ms_gw)

## 1. 背景 (改前必有数据)

R1021-R1044 已连续记录同一 RemoteDisconnected 风暴并判定模型特异性 NOP。本轮 (间隔 ~45min)
为**同一风暴第 24 轮延续**。请求层 SR 72.2%, attempt 层风暴未减。

### 30min 窗口 — nv_requests (tier_model=dsv4f0731_nv)
- 总量 18, 200=13, 失败=5, **SR=72.2%** (低流量期, 样本小)
- Avg 51038ms, p50 58202ms, p95 99870ms, max 101783ms (200 成功)
- 502 失败: 5 次 (all_tiers_exhausted)
- 429: 0 计数
- upstream_type: nvcf_pexec 18/18 全 pexec (integrate 0)
- finish_reason: stop=7, tool_calls=6 (正常业务完成)

### 错误分类 (30min)
| error_type | count | avg_ms |
|---|---|---|
| all_tiers_exhausted | 4 | 88453 |
| zombie_empty_completion | 1 | 3954 |

- all_tiers_exhausted=4: tier_attempts 层多次 RemoteDisconnected 烧尽 180s budget
- **zombie_empty_completion=1**: 新增劣化信号 (报告 200 但无实际内容), 集中在 k0

### per-key 错误 (30min) — 全部集中在 k0
- k0: all_tiers_exhausted=4(88453ms), zombie_empty_completion=1(3954ms)
- k1-k4: 无错误 (k1=4成功, k2=2, k3=2, k4=3)

### key_cycle_429s (30min)
- k0=12, k1=6 (429 计数 0, 为 key 循环次数非 429 事件)

### 6h 请求层 — 模型特异性第 24 次复现
| tier_model | total | ok | SR |
|---|---|---|---|
| glm5_2_nv    | 334 | 327 | **97.9%** |
| dsv4f0731_nv | 114 |  78 | **68.4%** |
| (empty tier)  |  10 |   0 | 0.0% (exhausted-tier 502) |
| glm5_2_ms     |   7 |   6 | 85.7% (hm4104 fallback 目标) |
| dsv4p_nv      |   2 |   0 | 0.0% |

- 同一容器、同一 5 组 NVU_KEY、同一 5 个 mihomo 出口
- glm5_2_nv 同链路 327/334=97.9% 成功 → 网络/mihomo/key/出口路径全部健康
- 故障隔离到 deepseek 具体 NVCF function 的远端执行层, 证据第 24 次成立

### hm4104 fallback 日志 (最近 5min) — fallback 持续触发
- **PRIMARY-FAIL-STREAM**: nv_gw 流式 server_5xx status=502 after 102267ms → 切 fallback
- **PRIMARY-BREAKER-SKIP-STREAM**: primary 流式跳过 (circuit OPEN) → 直走 fallback
- 多次 FALLBACK-STREAM → ms_gw
- 说明 hermes 主链路 (nv_gw→dsv4f0731_nv) 断路器已 OPEN, 用户请求持续被 fallback 到 ms_gw

### 趋势
- 6h 累积: 114 请求 78 成功 (**68.4%**) — 与 R1044 的 67.0% 基本持平, 无恢复
- 3h 逐小时 SR: 12:00=72.7%(11), 11:00=71.0%(31), 10:00=64.7%(34), 09:00=76.2%(21)
- 24h all_tiers_exhausted: 29 次 (较 R1042 的 181 次大幅下降, 但 R1044 为 22 次, 回升)

## 2. 决策: NOP (无参数修改)

RemoteDisconnected/529_nv_overloaded/empty_200/zombie_empty_completion 是 NVCF deepseek
**远程 function 级**瞬断/过载, 与容器 env 无关 (第 24 次确认):
- 同出口同 key 下 glm5_2_nv 6h 97.9% 成功 → 网络/mihomo/key/出口路径全部健康
- 故障仅存在于 dsv4f0731_nv 具体 function 的远端执行层
- tier_attempts 层 RemoteDisconnected 持续 + lineup 劣化信号 (empty_200/zombie_empty_completion)
  分散各 key → 证明非 UPSTREAM_TIMEOUT/budget/cooldown/fastbreak 可解的 lever
- 本轮 per-key 错误集中 k0 (all_tiers_exhausted=4) 但 k0 也有 2 次成功, 且 key_cycle_429s
  k0=12 高 → k0 被反复循环尝试, 非 key 本身故障, 是远端 function 劣化

本轮继续 NOP, 等待 NVCF 侧恢复 (第 24 轮)。模型特异性铁证仍成立, 无本地参数可解。
hm4104 断路器已接管用户侧 fallback, 用户请求由 ms_gw 保活。

## 3. 修改

无。参数保持: UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_DSV4F0731_NV=180,
NVU_TIER_BUDGET_DSV4F_NV=180, KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90, NVU_KEYMGR_429_BASE/MAX=120,
NVU_EMPTY_200_FASTBREAK=3, NVU_PEXEC_TIMEOUT_FASTBREAK=3, NV_KEY_INTEGRATE_KEYS=(empty, 全 pexec),
NV_INTEGRATE_MODELS=(empty)。

## 4. 验证

- /health: status=ok, nv_num_keys=5, nvcf_pexec_models 含 dsv4f0731_nv, port=40666 ✓
- 容器: dsvf0731_nv40666 Up 15 hours, env 读取正常 (与 R1044 一致, 无漂移) ✓
- 无 env 变更, 无需重启

## 5. 下一步建议

继续等待 NVCF deepseek function 侧恢复。本轮模型特异性铁证 (glm5_2_nv 97.9% vs
dsv4f0731_nv 68.4%) 第 24 次成立。风暴延续 ≥30h, 6h 累积 SR 持续 ~68% 无衰减, 且本轮新增
zombie_empty_completion 劣化信号 (200 但无内容)。hm4104 断路器已 OPEN, 用户请求持续 fallback
到 ms_gw。建议由 CC 评估 (非本容器决策): 是否将 hermes 主链路模型从 dsv4f0731_nv 临时切换
为同容器 glm5_2_nv (同链路 ~97.9% 成功) 以消除用户侧 fallback 依赖, 或联系 NVCF 侧确认
deepseek function 健康状况。本容器保持 NOP 以待 NVCF 修复。