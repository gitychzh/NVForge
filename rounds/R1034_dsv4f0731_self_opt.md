# R1034: RemoteDisconnected 风暴延续 (第13轮) — 模型特异性劣化持续, 无参数修改 (恢复观察轮)

> 时间: 2026-08-05 12:25 BJT (04:25 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF)
> 状态: **恢复观察轮 (无参数修改)** — NVCFPexecRemoteDisconnected 远程瞬断持续主导,
>   且第 13 次复现**模型特异性** (同容器同 key 同出口 glm5_2_nv 93.1% 成功) → NVCF
>   deepseek function 级劣化, 无本容器可解参数
> Fallback: hm4104 持续 fallback 到 dsv4f0731_ms (primary 502 触发)

## 1. 背景 (改前必有数据)

R1021-R1033 已连续记录同一 RemoteDisconnected 风暴并判定模型特异性 NOP。本轮 (间隔 ~17min)
为**同一风暴第 13 轮延续**, 数据完全复现 R1033 结论。

### 30min 窗口 — nv_requests (tier_model=dsv4f0731_nv, 采集脚本)
- 总量 19, 200=12, 失败=7, **SR=63.2%** (窗口内业务流量少, 波动大)
- Avg 62088ms / P50 62148ms / P95 115316ms / Max 120830ms
- 429: 0 (key_cycle_429s 0=14/1=5, 非 429 主导)
- upstream_type: nvcf_pexec 19/200=12 (全 pexec, integrate 0)
- 错误分类: all_tiers_exhausted=7 (avg 89678ms)
- finish_reason: tool_calls=10, stop=2

### per-key 视角 (30min)
- k0=5 ok (avg 39971ms), k1=2 ok, k2=2 ok (avg 87545ms), k3=2 ok, k4=1 ok
- k0=all_tiers_exhausted×7 (avg 89678ms) — 全部 key 烧尽后归于 k0
- 无单 key 连接错误集中 → 非单 key/proxy 问题

### 1h tier_attempts 失败细分 (per-attempt 层, dsv4f0731_nv)
- **NVCFPexecRemoteDisconnected: 25 (绝对主导, avg ~44.5s, 烧预算)**
- empty_200: 5, 529_nv_overloaded: 1

### ⭐ 关键证据 — 模型特异性第 13 次复现 (同容器同窗 1h, 请求层)
| tier_model | total | ok | SR |
|---|---|---|---|
| glm5_2_nv    | 144 | 134 | **93.1%** |
| dsv4f0731_nv |  31 |  19 | **61.3%** |

- 同一容器、同一 5 组 NVU_KEY、同一 5 个 mihomo 出口 (7894/7895/7896/7897/7904)
- glm5_2_nv 同链路 134/144=93.1% 成功 → 故障隔离到 deepseek 的具体 NVCF function
- 证据第 13 次成立, 变量隔离彻底干净

### 6h 趋势 (请求层)
- 6h 累积: 199 请求 122 成功 (**61.3%**)
- 3h 逐小时 SR: 01:00=47.1%, 02:00=50.0%, 03:00=52.0%, 04:00=61.5%
- 24h all_tiers_exhausted 累积 136 → 风暴持续未缓解

## 2. 决策: NOP (无参数修改)

RemoteDisconnected 是 NVCF deepseek **远程 function 级**瞬断, 与容器 env 无关:
- 同出口同 key 下 glm5_2_nv 134/144=93.1% 成功 → 网络/mihomo/key/出口路径全部健康
- 故障仅存在于 dsv4f0731_nv 具体 function 的远端执行层
- 调 FASTBREAK / cooldown / budget 均无 lever (键已因远端断连而烧尽, 非本地策略问题)

本轮继续 NOP, 等待 NVCF 侧恢复 (第 13 轮)。

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
同容器 glm5_2_nv (同链路 93.1% 成功) 以保 hermes 主链路可用 — 但这是 CC 侧决策,
本容器不做此改动。