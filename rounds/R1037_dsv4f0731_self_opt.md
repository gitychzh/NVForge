# R1037: RemoteDisconnected 风暴延续 (第16轮) — 模型特异性劣化持续, 无参数修改 (恢复观察轮)

> 时间: 2026-08-05 13:35 BJT (05:35 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF)
> 状态: **恢复观察轮 (无参数修改)** — NVCFPexecRemoteDisconnected 远程瞬断持续主导,
>   且第 16 次复现**模型特异性** (同容器同 key 同出口 glm5_2_nv 98.9% 成功) → NVCF
>   deepseek function 级劣化, 无本容器可解参数
> Fallback: hm4104 持续 fallback 到 dsv4f0731_ms (primary 502/RemoteDisconnected 触发)

## 1. 背景 (改前必有数据)

R1021-R1036 已连续记录同一 RemoteDisconnected 风暴并判定模型特异性 NOP。本轮 (间隔 ~16min)
为**同一风暴第 16 轮延续**, 数据完全复现 R1036 结论。

### 30min 窗口 — nv_requests (tier_model=dsv4f0731_nv, 采集脚本)
- 总量 12, 200=7, 失败=5, **SR=58.3%** (窗口内业务流量极少, 波动大)
- Avg 85208ms / P50 112164ms / P95 154613ms / Max 174955ms
- 429: 0 (key_cycle_429s 0=10/1=1/2=1, 非 429 主导)
- upstream_type: nvcf_pexec 12/200=7 (全 pexec, integrate 0)
- 错误分类: all_tiers_exhausted=5 (avg 133435ms, 全部 key 烧尽后归于 k0)
- finish_reason: tool_calls=3, stop=4

### per-key 视角 (30min)
- k1=1 ok (avg 121490ms), k2=3 ok (avg 51086ms), k3=1 ok (avg 35910ms), k4=2 ok (avg 22332ms)
- k0=all_tiers_exhausted×5 (avg 133435ms) — 全部 key 烧尽后归于 k0
- 各 key 延迟方差较大 → 远端瞬断随机分布, 非单 key/proxy 问题

### ⭐ 关键证据 — 模型特异性第 16 次复现 (同容器同窗 1h, 请求层)
| tier_model | total | ok | SR |
|---|---|---|---|
| glm5_2_nv    |  93 |  92 | **98.9%** |
| dsv4f0731_nv |  39 |  29 | **74.4%** |

- 同一容器、同一 5 组 NVU_KEY、同一 5 个 mihomo 出口 (7894/7895/7896/7897/7904)
- glm5_2_nv 同链路 92/93=98.9% 成功 → 故障隔离到 deepseek 的具体 NVCF function
- 证据第 16 次成立, 变量隔离彻底干净

### 6h 趋势 (请求层)
- 6h 累积: 177 请求 104 成功 (**58.8%**)
- 3h 逐小时 SR: 02:00=54.5%, 03:00=52.0%, 04:00=76.7%, 05:00(部分)=66.7%
- 24h all_tiers_exhausted 累积 146 (较上轮 143 微增) → 风暴持续未根治

## 2. 决策: NOP (无参数修改)

RemoteDisconnected 是 NVCF deepseek **远程 function 级**瞬断, 与容器 env 无关:
- 同出口同 key 下 glm5_2_nv 92/93=98.9% 成功 → 网络/mihomo/key/出口路径全部健康
- 故障仅存在于 dsv4f0731_nv 具体 function 的远端执行层
- 调 FASTBREAK / cooldown / budget 均无 lever (键已因远端断连而烧尽, 非本地策略问题)

本轮继续 NOP, 等待 NVCF 侧恢复 (第 16 轮)。窗口 SR=58.3% (流量极少, 波动大), 6h 累积 58.8%,
模型特异性铁证仍成立, 无本地参数可解。

## 3. 修改

无。参数保持: UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_DSV4F0731_NV=180,
NVU_TIER_BUDGET_DSV4F_NV=180, KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90, NVU_KEYMGR_429_BASE/MAX=120,
NVU_EMPTY_200_FASTBREAK=3, NVU_PEXEC_TIMEOUT_FASTBREAK=3, NV_KEY_INTEGRATE_KEYS=(empty, 全 pexec),
NV_INTEGRATE_MODELS=(empty)。

## 4. 验证

- /health: status=ok, nv_num_keys=5, nvcf_pexec_models 含 dsv4f0731_nv, port=40666 ✓
- 容器: dsvf0731_nv40666 Up 8 hours, env 读取正常 ✓
- 无 env 变更, 无需重启

## 5. 下一步建议

继续等待 NVCF deepseek function 侧恢复。本轮 1h 模型特异性铁证 (glm5_2_nv 98.9% vs
dsv4f0731_nv 74.4%) 第 16 次成立。若风暴延续至第 17+ 轮且 6h 累积 SR 持续 <70%, 可考虑由 CC 评估:
是否将 dsv4f0731_nv 的 fallback 目标从 dsv4f0731_ms 临时切换为同容器 glm5_2_nv (同链路 98.9% 成功)
以保 hermes 主链路可用 — 但这是 CC 侧决策, 本容器不做此改动。