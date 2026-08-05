# R1033: RemoteDisconnected 风暴延续 (第12轮) — 模型特异性劣化持续, 无参数修改 (恢复观察轮)

> 时间: 2026-08-05 12:08 BJT (04:08 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF)
> 状态: **恢复观察轮 (无参数修改)** — NVCFPexecRemoteDisconnected 远程瞬断持续绝对主导,
>   且第 12 次复现**模型特异性** (同容器同 key 同出口 glm5_2_nv 91.5% 成功) → NVCF
>   deepseek function 级劣化, 无本容器可解参数
> Fallback: hm4104 持续 fallback 到 dsv4f0731_ms (primary 502/RemoteDisconnected 触发)

## 1. 背景 (改前必有数据)

R1021-R1032 已连续记录同一 RemoteDisconnected 风暴并判定模型特异性 NOP。本轮 (间隔 ~20min)
为**同一风暴第 12 轮延续**, 数据完全复现 R1032 结论。

### 30min 窗口 — nv_requests (采集脚本, tier_model=dsv4f0731_nv)
- 总量 14, 200=10, 失败=4, **SR=71.4%** (窗口内业务流量少, 波动大)
- Avg 61831ms / P50 57515ms / P95 135824ms / Max 167432ms
- 429: 0 (key_cycle_429s 0=12/1=2, 非 429 主导)
- upstream_type: nvcf_pexec 14/200=10 (全 pexec, integrate 0)
- 错误分类: all_tiers_exhausted=4 (avg 110815ms)
- finish_reason: tool_calls=7, stop=3

### 1h tier_attempts 失败细分 (per-attempt 层, dsv4f0731_nv)
- **NVCFPexecRemoteDisconnected: 24 (绝对主导, avg ~47s, 烧 90s 预算)**
- empty_200: 5, 529_nv_overloaded: 1

### ⭐ 关键证据 — 模型特异性第 12 次复现 (同容器同窗 1h, 请求层)
| tier_model | total | ok | SR |
|---|---|---|---|
| glm5_2_nv    | 129 | 118 | **91.5%** |
| dsv4f0731_nv |  31 |  20 | **64.5%** |

- 同一容器、同一 5 组 NVU_KEY、同一 5 个 mihomo 出口 (7894/7895/7896/7897/7904)
- glm5_2_nv 同链路 118/129=91.5% 成功 → 故障隔离到 deepseek 的具体 NVCF function
- 证据第 12 次成立, 变量隔离彻底干净

### per-key 均匀劣化 (非单 key 问题)
- 30min per-key: k0=4 all_tiers_exhausted (全部 key 烧尽后), k1/k3/k4 各含 empty_200
- 连接错误 (RemoteDisconnected) 遍布 k0/k1/k2/k3/k4 多 key (1h: 各 key 均有) → 非单 key/proxy 问题
- key_cycle_429s 低, 非 429 主导

### 6h 趋势 (请求层)
- 6h 累积: 198 请求 123 成功 (62.1%)
- 3h 逐小时 SR: 01:00=40.0%, 02:00=50.0%, 03:00=52.0%, 04:00=66.7%
- 24h all_tiers_exhausted 累积 132 → 风暴持续未缓解

## 2. 决策: NOP (无参数修改)

RemoteDisconnected 是 NVCF deepseek **远程 function 级**瞬断, 与容器 env 无关:
- 同出口同 key 下 glm5_2_nv 118/129=91.5% 成功 → 网络/mihomo/key/出口路径全部健康
- 故障仅存在于 dsv4f0731_nv 具体 function 的远端执行层
- 调 FASTBREAK / cooldown / budget 均无 lever (键已因远端断连而烧尽, 非本地策略问题)

本轮继续 NOP, 等待 NVCF 侧恢复 (第 12 轮)。

## 3. 修改

无。参数保持: UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_DSV4F0731_NV=180,
KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90, NVU_KEYMGR_429_BASE/MAX=120, NVU_EMPTY_200_FASTBREAK=3,
NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_KEY_INTEGRATE_KEYS=(empty, 全 pexec)。

## 4. 验证

- /health: status=ok, nv_num_keys=5, nvcf_pexec_models 含 dsv4f0731_nv, port=40666 ✓
- 容器: dsvf0731_nv40666 Up 7 hours ✓
- 无 env 变更, 无需重启

## 5. 下一步建议

继续等待 NVCF deepseek function 侧恢复。若风暴延续至第 15+ 轮且 SR 持续 <70%,
可考虑由 CC 评估: 是否将 dsv4f0731_nv 的 fallback 目标从 dsv4f0731_ms 临时切换为
同容器 glm5_2_nv (同链路 91.5% 成功) 以保 hermes 主链路可用 — 但这是 CC 侧决策,
本容器不做此改动。