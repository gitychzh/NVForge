# R1041: RemoteDisconnected 风暴延续 (第20轮) — 模型特异性第20次复现, 无参数修改 (恢复观察轮)

> 时间: 2026-08-05 16:37 BJT (08:37 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF)
> 状态: **恢复观察轮 (无参数修改)** — NVCFPexecRemoteDisconnected 远程瞬断风暴持续主导,
>   且第 20 次复现**模型特异性** (同容器同 key 同出口 glm5_2_nv 97.8% 成功) → NVCF
>   deepseek function 级劣化, 无本容器可解参数
> Fallback: hm4104 最近 5min 无 fallback 日志 (窗口内恢复)

## 1. 背景 (改前必有数据)

R1021-R1040 已连续记录同一 RemoteDisconnected 风暴并判定模型特异性 NOP。本轮 (间隔 ~38min)
为**同一风暴第 20 轮延续**, 数据复现 R1040 结论, 无恢复信号。

### 30min 窗口 — nv_requests (tier_model=dsv4f0731_nv)
- 总量 14, 200=13, 失败=1, **SR=92.9%** (窗口内业务流量极少, 波动大)
- Avg 63878ms (受 1 次 173s 长失败拖累)
- 429: 0 (key_cycle_429s 非主导)
- upstream_type: nvcf_pexec 14/14 全 pexec (integrate 0)
- 错误分类: all_tiers_exhausted=1 (avg 180035ms, 完整烧尽 180s budget)
- 唯一失败 all_tiers_exhausted → tier_attempts 层 12 次 RemoteDisconnected 烧尽全部 key

### tier_attempts (30min) — 错误分类
| error_type | count | avg_ms |
|---|---|---|
| pexec_success | 90 | 13666 |
| NVCFPexecRemoteDisconnected | 12 | 50125 |
| 529_nv_overloaded | 4 | — |
| empty_200 | 2 | — |
| NVCFPexecTimeout | 1 | 23118 |

- **RemoteDisconnected 风暴仍在 attempt 层持续 (12次/30min)**, 只是被重试吸收, 请求层 SR 回升
- 无 SSL 错误 → 纯远程断连/过载, 非本地超时/代理问题
- 错误分散在各 key → 远端随机瞬断

### 关键证据 — 模型特异性第 20 次复现 (同容器同窗 30min, 请求层)
| tier_model | total | ok | SR |
|---|---|---|---|
| glm5_2_nv    |  92 |  90 | **97.8%** |
| dsv4f0731_nv |  17 |  14 | **82.4%** |

- 同一容器、同一 5 组 NVU_KEY、同一 5 个 mihomo 出口
- glm5_2_nv 同链路 90/92=97.8% 成功 → 故障隔离到 deepseek 的具体 NVCF function
- 证据第 20 次成立, 变量隔离彻底干净

### 趋势 (6h)
- 6h 累积: 195 请求 128 成功 (**65.6%**) — 风暴持续, 无单调恢复
- 24h ATE: all_tiers_exhausted=174 次
- 逐小时 SR: 08:00=87.5%, 07:00=54.8%, 06:00=62.2%, 05:00=75.0% — 随机波动, 无恢复趋势
- 最近 10min 窗口: 34/32=94.1% (窗口性恢复)

## 2. 决策: NOP (无参数修改)

RemoteDisconnected/529_nv_overloaded 是 NVCF deepseek **远程 function 级**瞬断/过载, 与容器
env 无关 (第 20 次确认):
- 同出口同 key 下 glm5_2_nv 90/92=97.8% 成功 → 网络/mihomo/key/出口路径全部健康
- 故障仅存在于 dsv4f0731_nv 具体 function 的远端执行层
- tier_attempts 30min 内 NVCFPexecRemoteDisconnected=12 且分散各 key → 证明非
  UPSTREAM_TIMEOUT/budget/cooldown/fastbreak 可解的 lever
- 窗口 SR 波动 (46.7%→53.3%→92.9%) 为低流量噪声, 非真实恢复 — 6h 累积仍 65.6%

本轮继续 NOP, 等待 NVCF 侧恢复 (第 20 轮)。模型特异性铁证仍成立, 无本地参数可解。

## 3. 修改

无。参数保持: UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_DSV4F0731_NV=180,
NVU_TIER_BUDGET_DSV4F_NV=180, KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90, NVU_KEYMGR_429_BASE/MAX=120,
NVU_EMPTY_200_FASTBREAK=3, NVU_PEXEC_TIMEOUT_FASTBREAK=3, NV_KEY_INTEGRATE_KEYS=(empty, 全 pexec),
NV_INTEGRATE_MODELS=(empty)。

## 4. 验证

- /health: status=ok, nv_num_keys=5, nvcf_pexec_models 含 dsv4f0731_nv, port=40666 ✓
- 容器: dsvf0731_nv40666 Up 11 hours, env 读取正常 ✓
- 无 env 变更, 无需重启

## 5. 下一步建议

继续等待 NVCF deepseek function 侧恢复。本轮模型特异性铁证 (glm5_2_nv 97.8% vs
dsv4f0731_nv 82.4%) 第 20 次成立。风暴已延续 20 轮 (≥24h), 6h 累积 SR 持续 ~65%, 无衰减
迹象。建议由 CC 评估 (非本容器决策): 是否将 dsv4f0731_nv 的 fallback 目标临时切换为同容器
glm5_2_nv (同链路 ~98% 成功) 以保 hermes 主链路可用, 或联系 NVCF 侧确认 deepseek function
健康状况。本容器保持 NOP 以待 NVCF 修复。