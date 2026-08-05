# R1043: RemoteDisconnected 风暴延续 (第22轮) — 模型特异性第22次复现, 无参数修改 (恢复观察轮)

> 时间: 2026-08-05 19:16 BJT (11:16 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF)
> 状态: **恢复观察轮 (无参数修改)** — NVCFPexecRemoteDisconnected 远程瞬断风暴在 attempt 层
>   持续主导, 第 22 次复现**模型特异性** (同容器同 key 同出口 glm5_2_nv 97.4% 成功) →
>   NVCF deepseek function 级劣化, 无本容器可解参数
> Fallback: hm4104 无 fallback 日志 (最近 5min), 用户零感知

## 1. 背景 (改前必有数据)

R1021-R1042 已连续记录同一 RemoteDisconnected 风暴并判定模型特异性 NOP。本轮 (间隔 ~2h)
为**同一风暴第 22 轮延续**。请求层 SR 表面回升 (78.9%), 但 attempt 层风暴未减。

### 30min 窗口 — nv_requests (tier_model=dsv4f0731_nv)
- 总量 19, 200=15, 失败=4, **SR=78.9%** (较 R1042 的 45.5% 表面回升)
- Avg 57560ms, p50 45512ms, p95 119502ms (200 成功)
- 502 失败: 4 次, avg 138278ms
- 429: 0 (key_cycle_429s 非主导)
- upstream_type: nvcf_pexec 19/19 全 pexec (integrate 0)
- finish_reason: tool_calls=13, stop=2 (无僵尸空 200)

### tier_attempts (30min) — 风暴仍在 attempt 层持续
| error_type | count | avg_ms |
|---|---|---|
| NVCFPexecRemoteDisconnected | 12 | 40138 |
| empty_200 | 5 | - |
| 529_nv_overloaded | 1 | - |

- **RemoteDisconnected 在 attempt 层未减 (12次/30min, avg 40s)**, 分散在各 key (k0=5, k2=3,
  k3=2, k1=1, k4=1)
- 请求层 SR 回升纯靠下游重试吸收, 非功能层恢复
- 无 SSL 错误 → 纯远程断连/过载, 非本地超时/代理问题

### 6h attempt 层 — 风暴持续
| error_type | count | avg_ms |
|---|---|---|
| NVCFPexecRemoteDisconnected | 62 | 43223 |
| empty_200 | 14 | - |
| 529_nv_overloaded | 3 | - |
| NVCFPexecTimeout | 3 | 53150 |

### 关键证据 — 模型特异性第 22 次复现 (同容器同窗 3h, 请求层)
| tier_model | total | ok | SR |
|---|---|---|---|
| glm5_2_nv    | 272 | 265 | **97.4%** |
| dsv4f0731_nv |  86 |  59 | **68.6%** |

- 同一容器、同一 5 组 NVU_KEY、同一 5 个 mihomo 出口
- glm5_2_nv 同链路 265/272=97.4% 成功 → 网络/mihomo/key/出口路径全部健康
- 故障隔离到 deepseek 具体 NVCF function 的远端执行层, 证据第 22 次成立

### Fallback 日志 (hm4104, 最近 5min)
- 无 fallback 日志 → 最近 5min hermes 主链路未触发 fallback (低流量期)

### 趋势
- 3h 逐小时 SR: 08:00=50%(2), 09:00=70%(30), 10:00=62.9%(35), 11:00=78.9%(19)
- 3h 累积: 86 请求 59 成功 (**68.6%**) — 与 R1042 的 6h 66.5% 基本持平, 无单调恢复
- 24h 非 200 失败: 27 次

## 2. 决策: NOP (无参数修改)

RemoteDisconnected/529_nv_overloaded/empty_200 是 NVCF deepseek **远程 function 级**瞬断/过载,
与容器 env 无关 (第 22 次确认):
- 同出口同 key 下 glm5_2_nv 3h 97.4% 成功 → 网络/mihomo/key/出口路径全部健康
- 故障仅存在于 dsv4f0731_nv 具体 function 的远端执行层
- tier_attempts 30min 内 NVCFPexecRemoteDisconnected=12 + empty_200=5 且分散各 key → 证明非
  UPSTREAM_TIMEOUT/budget/cooldown/fastbreak 可解的 lever
- 请求层 SR 表面回升 (45.5%→78.9%) 为低流量噪声 + 重试吸收, 非真实恢复 — attempt 层
  RemoteDisconnected 计数未减 (12/30min)

本轮继续 NOP, 等待 NVCF 侧恢复 (第 22 轮)。模型特异性铁证仍成立, 无本地参数可解。

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

继续等待 NVCF deepseek function 侧恢复。本轮模型特异性铁证 (glm5_2_nv 97.4% vs
dsv4f0731_nv 68.6%) 第 22 次成立。风暴已延续 22 轮 (≥30h), attempt 层 RemoteDisconnected
计数无衰减 (12/30min), 且 empty_200/529_nv_overloaded 劣化信号持续。请求层 SR 的 78.9%
是重试吸收的假象。建议由 CC 评估 (非本容器决策): 是否将 dsv4f0731_nv 的 fallback 目标
临时切换为同容器 glm5_2_nv (同链路 ~97% 成功) 以保 hermes 主链路可用, 或联系 NVCF 侧
确认 deepseek function 健康状况。本容器保持 NOP 以待 NVCF 修复。