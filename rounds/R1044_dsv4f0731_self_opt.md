# R1044: RemoteDisconnected 风暴延续 (第23轮) — 模型特异性第23次复现 + hm4104 fallback 触发, 无参数修改 (恢复观察轮)

> 时间: 2026-08-05 19:35 BJT (11:35 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF)
> 状态: **恢复观察轮 (无参数修改)** — NVCFPexecRemoteDisconnected 远程瞬断风暴在 attempt 层
>   持续主导, 第 23 次复现**模型特异性** (同容器同 key 同出口 glm5_2_nv 97.5% 成功) →
>   NVCF deepseek function 级劣化, 无本容器可解参数
> **新信号**: 本轮 hm4104 fallback 开始触发 (10 次 exhausted-tier 502, 用户侧有感知),
>   较 R1043 的 "无 fallback" 恶化 — 但 fallback 目标由 hm4104 适配器接管 (本容器
>   NVU_MS_FALLBACK_ENABLED=0), 非本容器可解

## 1. 背景 (改前必有数据)

R1021-R1043 已连续记录同一 RemoteDisconnected 风暴并判定模型特异性 NOP。本轮 (间隔 ~20min)
为**同一风暴第 23 轮延续**。请求层 SR 表面 76.7%, 但 attempt 层风暴未减。

### 30min 窗口 — nv_requests (tier_model=dsv4f0731_nv)
- 总量 18, 200=15, 失败=3, **SR=83.3%** (低流量期, 样本小)
- Avg 70096ms, p50 63972ms, p95 156415ms (200 成功)
- 502 失败: 3 次, avg 132775ms (all_tiers_exhausted)
- 429: 0 计数 (key_cycle_429s 非主导)
- upstream_type: nvcf_pexec 18/18 全 pexec (integrate 0)
- finish_reason: tool_calls=14, stop=1 (无僵尸空 200 主导)

### tier_attempts (30min) — 风暴仍在 attempt 层持续, 分散各 key
| nv_key_idx | error_type | count | avg_ms |
|---|---|---|---|
| 0 | NVCFPexecRemoteDisconnected | 5 | 34584 |
| 0 | empty_200 | 1 | - |
| 1 | empty_200 | 4 | - |
| 1 | NVCFPexecTimeout | 1 | 45173 |
| 2 | NVCFPexecRemoteDisconnected | 5 | 44543 |
| 3 | NVCFPexecRemoteDisconnected | 3 | 34712 |
| 3 | 529_nv_overloaded | 1 | - |
| 4 | NVCFPexecRemoteDisconnected | 2 | 81105 |

- RemoteDisconnected 30min 15 次, 分散全部 5 key (k0=5,k1=0,k2=5,k3=3,k4=2) + empty_200 5 次
- 无 SSL 错误 → 纯远程断连/过载, 非本地超时/代理问题

### key_cycle_429s (30min)
- k0=11, k1=3, k2=4 — 注意 k0 高 (11), 但 429 计数为 0, 说明这是 key 循环次数而非 429 事件

### 6h 请求层 — 模型特异性第 23 次复现
| tier_model | total | ok | SR |
|---|---|---|---|
| glm5_2_nv    | 278 | 271 | **97.5%** |
| dsv4f0731_nv |  88 |  59 | **67.0%** |
| (empty tier)  |  10 |   0 | 0.0% (exhausted-tier 502) |
| glm5_2_ms     |   7 |   6 | 85.7% (hm4104 fallback 目标) |

- 同一容器、同一 5 组 NVU_KEY、同一 5 个 mihomo 出口
- glm5_2_nv 同链路 271/278=97.5% 成功 → 网络/mihomo/key/出口路径全部健康
- 故障隔离到 deepseek 具体 NVCF function 的远端执行层, 证据第 23 次成立

### hm4104 fallback 日志 (最近 5min) — 新信号: 用户侧 fallback 已触发
- **PRIMARY-FAIL-STREAM**: nv_gw 流式 server_5xx status=502 after 180089ms → 切 fallback
- **PRIMARY-BREAKER-SKIP-STREAM**: primary 流式跳过 (circuit OPEN) → 直走 fallback
- 多次 FALLBACK-STREAM → ms_gw
- 说明 hermes 主链路 (nv_gw→dsv4f0731_nv) 已触发断路器, 用户请求被 fallback 到 ms_gw
  的 dsv4f0731_ms。较 R1043 "无 fallback" 恶化, 是风暴持续的用户面体现。

### 趋势
- 3h 逐小时 SR: 08:00=50%(2), 09:00=70%(30), 10:00=62.9%(35), 11:00=71.4%(21)
- 6h 累积: 88 请求 59 成功 (**67.0%**)
- 24h all_tiers_exhausted: 22 次

## 2. 决策: NOP (无参数修改)

RemoteDisconnected/529_nv_overloaded/empty_200 是 NVCF deepseek **远程 function 级**瞬断/过载,
与容器 env 无关 (第 23 次确认):
- 同出口同 key 下 glm5_2_nv 6h 97.5% 成功 → 网络/mihomo/key/出口路径全部健康
- 故障仅存在于 dsv4f0731_nv 具体 function (52e1ddb6...) 的远端执行层
- tier_attempts 30min 内 RemoteDisconnected=15 + empty_200=5 且分散全部 5 key → 证明非
  UPSTREAM_TIMEOUT/budget/cooldown/fastbreak 可解的 lever
- error_detail 显示全是 nvcf_pexec 的 RemoteDisconnected/empty_200/Timeout, 无 429/SSL

本轮继续 NOP, 等待 NVCF 侧恢复 (第 23 轮)。模型特异性铁证仍成立, 无本地参数可解。
hm4104 断路器已接管用户侧 fallback, 用户虽有 502 感知但 hermes 主链路通过 fallback 保活。

## 3. 修改

无。参数保持: UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_DSV4F0731_NV=180,
NVU_TIER_BUDGET_DSV4F_NV=180, KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90, NVU_KEYMGR_429_BASE/MAX=120,
NVU_EMPTY_200_FASTBREAK=3, NVU_PEXEC_TIMEOUT_FASTBREAK=3, NV_KEY_INTEGRATE_KEYS=(empty, 全 pexec),
NV_INTEGRATE_MODELS=(empty)。

## 4. 验证

- /health: status=ok, nv_num_keys=5, nvcf_pexec_models 含 dsv4f0731_nv, port=40666 ✓
- 容器: dsvf0731_nv40666 Up 14 hours, env 读取正常 ✓
- 无 env 变更, 无需重启

## 5. 下一步建议

继续等待 NVCF deepseek function 侧恢复。本轮模型特异性铁证 (glm5_2_nv 97.5% vs
dsv4f0731_nv 67.0%) 第 23 次成立。新信号: hm4104 fallback/断路器已开始触发 (用户侧 502
感知), 风暴进入用户面影响阶段。建议由 CC 评估 (非本容器决策): 是否将 hermes 主链路
模型从 dsv4f0731_nv 临时切换为同容器 glm5_2_nv (同链路 ~97.5% 成功) 以消除用户侧 502,
或联系 NVCF 侧确认 deepseek function (52e1ddb6...) 健康状况。本容器保持 NOP 以待 NVCF 修复。