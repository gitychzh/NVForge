# R1036: RemoteDisconnected 风暴延续 (第15轮) — 模型特异性劣化持续, 无参数修改 (恢复观察轮)

> 时间: 2026-08-05 13:19 BJT (05:19 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF)
> 状态: **恢复观察轮 (无参数修改)** — NVCFPexecRemoteDisconnected 远程瞬断持续主导,
>   且第 15 次复现**模型特异性** (同容器同 key 同出口 glm5_2_nv 98.9% 成功) → NVCF
>   deepseek function 级劣化, 无本容器可解参数
> Fallback: hm4104 持续 fallback 到 dsv4f0731_ms (primary 502/RemoteDisconnected 触发)

## 1. 背景 (改前必有数据)

R1021-R1035 已连续记录同一 RemoteDisconnected 风暴并判定模型特异性 NOP。本轮 (间隔 ~7min)
为**同一风暴第 15 轮延续**, 数据完全复现 R1035 结论。

### 30min 窗口 — nv_requests (tier_model=dsv4f0731_nv, 采集脚本)
- 总量 24, 200=20, 失败=4, **SR=83.3%** (窗口内业务流量少, 波动大)
- Avg 39770ms / P50 17828ms / P95 129982ms / Max 132969ms
- 429: 0 (key_cycle_429s 0=22/1=1/2=1, 非 429 主导)
- upstream_type: nvcf_pexec 24/200=20 (全 pexec, integrate 0)
- 错误分类: all_tiers_exhausted=4 (avg 115466ms, 全部 key 烧尽后归于 k0)
- finish_reason: tool_calls=15, stop=5

### per-key 视角 (30min)
- k0=2 ok (avg 10362ms), k1=3 ok (avg 11819ms), k2=5 ok (avg 44558ms), k3=5 ok (avg 26690ms), k4=5 ok (avg 16039ms)
- k0=all_tiers_exhausted×4 (avg 115466ms) — 全部 key 烧尽后归于 k0
- 各 key 延迟方差较大 (k2 avg 44.6s vs k0 avg 10.4s) → 远端瞬断随机分布, 非单 key/proxy 问题

### ⭐ 关键证据 — 模型特异性第 15 次复现 (同容器同窗 1h, 请求层)
| tier_model | total | ok | SR |
|---|---|---|---|
| glm5_2_nv    |  87 |  86 | **98.9%** |
| dsv4f0731_nv |  42 |  34 | **81.0%** |

- 同一容器、同一 5 组 NVU_KEY、同一 5 个 mihomo 出口 (7894/7895/7896/7897/7904)
- glm5_2_nv 同链路 86/87=98.9% 成功 → 故障隔离到 deepseek 的具体 NVCF function
- 证据第 15 次成立, 变量隔离彻底干净

### 6h 趋势 (请求层)
- 6h 累积: 182 请求 108 成功 (**59.3%**)
- 3h 逐小时 SR: 02:00=50.0%, 03:00=52.0%, 04:00=76.7%, 05:00(部分)=81.8%
- RemoteDisconnected 风暴持续, 但 04:00-05:00 有持续缓解迹象 (SR 逐小时回升至 76→82%)
- 24h all_tiers_exhausted 累积 143 (较上轮 141 微增) → 风暴持续但缓解中

## 2. 决策: NOP (无参数修改)

RemoteDisconnected 是 NVCF deepseek **远程 function 级**瞬断, 与容器 env 无关:
- 同出口同 key 下 glm5_2_nv 86/87=98.9% 成功 → 网络/mihomo/key/出口路径全部健康
- 故障仅存在于 dsv4f0731_nv 具体 function 的远端执行层
- 调 FASTBREAK / cooldown / budget 均无 lever (键已因远端断连而烧尽, 非本地策略问题)

本轮继续 NOP, 等待 NVCF 侧恢复 (第 15 轮)。窗口 SR=83.3%, 3h 逐小时 SR 回升至 76-82%,
继续观察缓解趋势。glm5_2_nv 98.9% 对比仍确认模型特异性, 无本地参数可解。

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

继续等待 NVCF deepseek function 侧恢复。本轮 3h SR 逐小时回升至 76→82%, 风暴有缓解迹象。
若后续某轮 30min SR 稳定 >90% 且 1h RemoteDisconnected 显著下降, 可判定恢复并进入正常调优。
若风暴在第 16+ 轮反而加剧 (6h SR<60%), 可考虑由 CC 评估: 是否将 dsv4f0731_nv 的 fallback
目标从 dsv4f0731_ms 临时切换为同容器 glm5_2_nv (同链路 98.9% 成功) 以保 hermes 主链路可用 —
但这是 CC 侧决策, 本容器不做此改动。