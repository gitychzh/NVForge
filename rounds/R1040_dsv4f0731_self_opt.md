# R1040: RemoteDisconnected 风暴延续 (第19轮) — 模型特异性第19次复现, 无参数修改 (恢复观察轮)

> 时间: 2026-08-05 15:59 BJT (07:59 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF)
> 状态: **恢复观察轮 (无参数修改)** — NVCFPexecRemoteDisconnected 远程瞬断风暴持续主导,
>   且第 19 次复现**模型特异性** (同容器同 key 同出口 glm5_2_nv 97.2% 成功) → NVCF
>   deepseek function 级劣化, 无本容器可解参数
> Fallback: hm4104 持续 fallback 到 dsv4f0731_ms (primary RemoteDisconnected/502 触发)

## 1. 背景 (改前必有数据)

R1021-R1039 已连续记录同一 RemoteDisconnected 风暴并判定模型特异性 NOP。本轮 (间隔 ~67min)
为**同一风暴第 19 轮延续**, 数据完全复现 R1039 结论, 无恢复信号。

### 30min 窗口 — nv_requests (tier_model=dsv4f0731_nv)
- 总量 14, 200=7, 失败=7, **SR=50.0%** (窗口内业务流量极少, 波动大)
- Avg 62920ms (受长失败拖累)
- 429: 0 (key_cycle_429s 非主导)
- upstream_type: nvcf_pexec 14/14 全 pexec (integrate 0)
- 错误分类: all_tiers_exhausted=6 (avg 104434ms), zombie_empty_completion=1

### tier_attempts (30min) — 错误分类
| error_type | count | avg_ms |
|---|---|---|
| NVCFPexecRemoteDisconnected | 12 | 38843 |
| 529_nv_overloaded | 5 | — |
| empty_200 | 5 | — |
| NVCFPexecTimeout | 1 | 18465 |

- 无 SSL 错误 → 纯远程断连/过载, 非本地超时/代理问题
- RemoteDisconnected 错误分散在 07:30~07:57 多个孤立时间点 (每次 burst 后间断恢复) → 远端随机瞬断
- 30min 窗口成功请求 per-key 分布: k0=1, k1=1, k3=2, k4=3 (k2 无成功) — 但流量极少, 不构成单 key 劣化证据

### 关键证据 — 模型特异性第 19 次复现 (同容器同窗 30min, 请求层)
| tier_model | total | ok | SR |
|---|---|---|---|
| glm5_2_nv    |  36 | 35 | **97.2%** |
| dsv4f0731_nv |  15 |  7 | **46.7%** |

- 同一容器、同一 5 组 NVU_KEY、同一 5 个 mihomo 出口 (7894-7897/7904)
- glm5_2_nv 同链路 35/36=97.2% 成功 → 故障隔离到 deepseek 的具体 NVCF function
- 证据第 19 次成立, 变量隔离彻底干净

### 趋势 (6h)
- 6h 累积: 196 请求 122 成功 (**62.2%**) — 风暴持续, 无单调恢复
- RUN 采集脚本 6h 趋势: 196|123|73|0 (total|ok|fail|429)

## 2. 决策: NOP (无参数修改)

RemoteDisconnected/529_nv_overloaded 是 NVCF deepseek **远程 function 级**瞬断/过载, 与容器
env 无关:
- 同出口同 key 下 glm5_2_nv 35/36=97.2% 成功 → 网络/mihomo/key/出口路径全部健康
- 故障仅存在于 dsv4f0731_nv 具体 function 的远端执行层
- tier_attempts 30min 内 NVCFPexecRemoteDisconnected=12 + 529_nv_overloaded=5 且分散各 key →
  证明非 UPSTREAM_TIMEOUT/budget/cooldown/fastbreak 可解的 lever
- 调 FASTBREAK / cooldown / budget 均无 lever (键已因远端断连而烧尽, 非本地策略问题)

本轮继续 NOP, 等待 NVCF 侧恢复 (第 19 轮)。窗口 SR=50.0% (流量极少, 波动大),
模型特异性铁证仍成立, 无本地参数可解。

## 3. 修改

无。参数保持: UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_DSV4F0731_NV=180,
NVU_TIER_BUDGET_DSV4F_NV=180, KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90, NVU_KEYMGR_429_BASE/MAX=120,
NVU_EMPTY_200_FASTBREAK=3, NVU_PEXEC_TIMEOUT_FASTBREAK=3, NV_KEY_INTEGRATE_KEYS=(empty, 全 pexec),
NV_INTEGRATE_MODELS=(empty)。

## 4. 验证

- /health: status=ok, nv_num_keys=5, nvcf_pexec_models 含 dsv4f0731_nv, port=40666 ✓
- 容器: dsvf0731_nv40666 Up 10 hours, env 读取正常 ✓
- 无 env 变更, 无需重启

## 5. 下一步建议

继续等待 NVCF deepseek function 侧恢复。本轮模型特异性铁证 (glm5_2_nv 97.2% vs
dsv4f0731_nv 46.7%) 第 19 次成立。若风暴延续至第 20+ 轮且 6h 累积 SR 持续 <65%, 建议由 CC
评估 (非本容器决策): 是否将 dsv4f0731_nv 的 fallback 目标临时切换为同容器 glm5_2_nv
(同链路 ~97% 成功) 以保 hermes 主链路可用, 或等待 NVCF 侧修复。