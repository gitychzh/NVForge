# R1039: RemoteDisconnected 风暴延续 (第18轮) — 模型特异性持续, 间歇性恢复, 无参数修改 (恢复观察轮)

> 时间: 2026-08-05 14:52 BJT (06:52 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF)
> 状态: **恢复观察轮 (无参数修改)** — NVCFPexecRemoteDisconnected 远程瞬断风暴持续主导,
>   且第 18 次复现**模型特异性** (同容器同 key 同出口 glm5_2_nv 100% 成功) → NVCF
>   deepseek function 级劣化, 无本容器可解参数
> Fallback: hm4104 持续 fallback 到 dsv4f0731_ms (primary 502/RemoteDisconnected 触发)

## 1. 背景 (改前必有数据)

R1021-R1038 已连续记录同一 RemoteDisconnected 风暴并判定模型特异性 NOP。本轮 (间隔 ~28min)
为**同一风暴第 18 轮延续**, 数据完全复现 R1038 结论, 但出现**间歇性窗口性恢复**信号。

### 30min 窗口 — nv_requests (tier_model=dsv4f0731_nv)
- 总量 15, 200=8, 失败=7, **SR=53.3%** (窗口内业务流量极少, 波动大)
- Avg 77104ms (受 2 次 158s 长失败拖累)
- 429: 0 (key_cycle_429s 非主导)
- upstream_type: nvcf_pexec 全 pexec (integrate 0)
- 错误分类: all_tiers_exhausted=5 (avg 88s), zombie_empty_completion=1

### tier_attempts (30min) — 错误分类
| error_type | count | avg_ms |
|---|---|---|
| NVCFPexecRemoteDisconnected | 16 | 45936 |
| 529_nv_overloaded | 2 | — |
| empty_200 | 2 | — |

- 无 NVCFPexecTimeout, 无 SSL 错误 → 纯远程断连, 非本地超时/代理问题
- 错误均匀分布在全部 5 个 key (k0=3,k1=4+1empty,k2=3+1 529,k3=3,k4=2) → 远端随机瞬断, 非单 key/proxy

### 关键证据 — 模型特异性第 18 次复现 (同容器同窗 30min, 请求层)
| tier_model | total | ok | SR |
|---|---|---|---|
| glm5_2_nv    |  45 |  45 | **100.0%** |
| dsv4f0731_nv |  15 |   8 | **53.3%** |

- 同一容器、同一 5 组 NVU_KEY、同一 5 个 mihomo 出口 (7894/7895/7896/7897/7904)
- glm5_2_nv 同链路 45/45=100% 成功 → 故障隔离到 deepseek 的具体 NVCF function
- 证据第 18 次成立, 变量隔离彻底干净

### 间歇性恢复信号 (窗口内)
- 失败事件集中在 3 个孤立时间点: ~06:36 (3 attempts), ~06:41 (2 attempts), ~06:47 (2 attempts)
- 每次 burst 后链路恢复并连续服务后续请求:
  - 06:42-06:45 连续 8 个 200 成功
  - 最近 5min (06:45-06:50): 7/8 = **87.5%**
- 但 15min 窗口仅 69.2% → 恢复是间歇性/窗口性的, 风暴未根治

### 趋势 (24h)
- 24h 累积: 514 请求 344 成功 (**66.9%**), avg 49s
- 逐小时 SR 波动: 54.3%~84.2% 随机波动, 无单调恢复趋势
- RemoteDisconnected ATE 逐小时: 最近 7h 稳定在 21~33/hour (06:00=26) → **风暴强度未衰减**

## 2. 决策: NOP (无参数修改)

RemoteDisconnected 是 NVCF deepseek **远程 function 级**瞬断, 与容器 env 无关:
- 同出口同 key 下 glm5_2_nv 45/45=100% 成功 → 网络/mihomo/key/出口路径全部健康
- 故障仅存在于 dsv4f0731_nv 具体 function 的远端执行层
- tier_attempts 30min 内 NVCFPexecRemoteDisconnected=16 且均匀分布全 key, 无任何本地超时/SSL 错误 →
  证明非 UPSTREAM_TIMEOUT/budget/cooldown/fastbreak 可解的 lever
- 调 FASTBREAK / cooldown / budget 均无 lever (键已因远端断连而烧尽, 非本地策略问题)

本轮继续 NOP, 等待 NVCF 侧恢复 (第 18 轮)。窗口 SR=53.3% (流量极少, 波动大), 但出现
间歇性窗口恢复 (最近 5min 87.5%), 模型特异性铁证仍成立, 无本地参数可解。

## 3. 修改

无。参数保持: UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_DSV4F0731_NV=180,
NVU_TIER_BUDGET_DSV4F_NV=180, KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90, NVU_KEYMGR_429_BASE/MAX=120,
NVU_EMPTY_200_FASTBREAK=3, NVU_PEXEC_TIMEOUT_FASTBREAK=3, NV_KEY_INTEGRATE_KEYS=(empty, 全 pexec),
NV_INTEGRATE_MODELS=(empty)。

## 4. 验证

- /health: status=ok, nv_num_keys=5, nvcf_pexec_models 含 dsv4f0731_nv, port=40666 ✓
- 容器: dsvf0731_nv40666 Up 9 hours, env 读取正常 ✓
- 无 env 变更, 无需重启

## 5. 下一步建议

继续等待 NVCF deepseek function 侧恢复。本轮模型特异性铁证 (glm5_2_nv 100% vs
dsv4f0731_nv 53.3%) 第 18 次成立。注意到窗口内出现间歇性恢复信号 (最近 5min 87.5%) —
若后续轮次恢复信号增强 (30min SR 连续 ≥80%), 可考虑降级为"NOP + 轻度监控"观察轮。
若风暴延续至第 19+ 轮且 6h 累积 SR 持续 <70%, 可考虑由 CC 评估: 是否将 dsv4f0731_nv 的
fallback 目标从 dsv4f0731_ms 临时切换为同容器 glm5_2_nv (同链路 100% 成功) 以保 hermes
主链路可用 — 但这是 CC 侧决策, 本容器不做此改动。