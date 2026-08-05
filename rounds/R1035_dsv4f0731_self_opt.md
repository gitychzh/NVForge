# R1035: RemoteDisconnected 风暴延续 (第14轮) — 模型特异性劣化持续, 无参数修改 (恢复观察轮)

> 时间: 2026-08-05 13:12 BJT (05:12 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF)
> 状态: **恢复观察轮 (无参数修改)** — NVCFPexecRemoteDisconnected 远程瞬断持续主导,
>   且第 14 次复现**模型特异性** (同容器同 key 同出口 glm5_2_nv 99.1% 成功) → NVCF
>   deepseek function 级劣化, 无本容器可解参数
> Fallback: hm4104 持续 fallback 到 dsv4f0731_ms (primary 502/RemoteDisconnected 触发)

## 1. 背景 (改前必有数据)

R1021-R1034 已连续记录同一 RemoteDisconnected 风暴并判定模型特异性 NOP。本轮 (间隔 ~47min)
为**同一风暴第 14 轮延续**, 数据完全复现 R1034 结论。

### 30min 窗口 — nv_requests (tier_model=dsv4f0731_nv, 采集脚本)
- 总量 26, 200=23, 失败=3, **SR=88.5%** (窗口内业务流量少, 波动大; 较上轮 63.2% 回升)
- Avg 36809ms / P50 22047ms / P95 117941ms / Max 127963ms
- 429: 0 (key_cycle_429s 0=22/1=3/2=1, 非 429 主导)
- upstream_type: nvcf_pexec 26/200=23 (全 pexec, integrate 0)
- 错误分类: all_tiers_exhausted=3 (avg 102224ms, 全部 key 烧尽后归于 k0)
- finish_reason: tool_calls=19, stop=4

### per-key 视角 (30min)
- k0=5 ok (avg 22557ms), k1=4 ok (avg 16033ms), k2=3 ok (avg 63640ms), k3=6 ok (avg 23855ms), k4=5 ok (avg 27878ms)
- k0=all_tiers_exhausted×3 (avg 102224ms) — 全部 key 烧尽后归于 k0
- 各 key 延迟方差较大 (k2 avg 63.6s vs k1 avg 16.0s) → 远端瞬断随机分布, 非单 key/proxy 问题

### 1h tier_attempts 失败细分 (per-attempt 层, dsv4f0731_nv)
- **NVCFPexecRemoteDisconnected: 26 (绝对主导, avg ~45.5s, 烧预算)**
- empty_200: 2
- 429_nv: 0 (non-429 主导, 与上轮一致)

### per-key 失败分布 (1h, dsv4f0731_nv)
- k0=7×RemoteDisconnected, k1=5×RD+1×empty_200, k2=5×RD, k3=2×RD+1×empty_200, k4=7×RD
- RemoteDisconnected 遍布全部 5 key → 非单 key/proxy/出口问题

### ⭐ 关键证据 — 模型特异性第 14 次复现 (同容器同窗 1h, 请求层)
| tier_model | total | ok | SR |
|---|---|---|---|
| glm5_2_nv    | 106 | 105 | **99.1%** |
| dsv4f0731_nv |  42 |  33 | **78.6%** |

- 同一容器、同一 5 组 NVU_KEY、同一 5 个 mihomo 出口 (7894/7895/7896/7897/7904)
- glm5_2_nv 同链路 105/106=99.1% 成功 → 故障隔离到 deepseek 的具体 NVCF function
- 证据第 14 次成立, 变量隔离彻底干净

### 6h 趋势 (请求层)
- 6h 累积: 180 请求 105 成功 (**58.3%**)
- 3h 逐小时 SR: 02:00=52.2%, 03:00=52.0%, 04:00=76.7%, 05:00(部分)=80.0%
- RemoteDisconnected 逐小时计数: 23:00=22, 00:00=31, 01:00=33, 02:00=26, 03:00=21, 04:00=29, 05:00(部分)=6
- 风暴持续, 但 04:00-05:00 有轻微缓解迹象 (SR 回升至 76-80%)
- 24h all_tiers_exhausted 累积 141 → 风暴持续未根治

## 2. 决策: NOP (无参数修改)

RemoteDisconnected 是 NVCF deepseek **远程 function 级**瞬断, 与容器 env 无关:
- 同出口同 key 下 glm5_2_nv 105/106=99.1% 成功 → 网络/mihomo/key/出口路径全部健康
- 故障仅存在于 dsv4f0731_nv 具体 function 的远端执行层
- 调 FASTBREAK / cooldown / budget 均无 lever (键已因远端断连而烧尽, 非本地策略问题)

本轮继续 NOP, 等待 NVCF 侧恢复 (第 14 轮)。窗口 SR=88.5% 较上轮回升, 但 6h 累积 SR 仍 58.3%,
未达到触发参数调整的数据门槛 (需模型侧恢复, 非本地可解)。

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

继续等待 NVCF deepseek function 侧恢复。本轮 30min SR=88.5% 与 glm5_2_nv 99.1% 对比仍显示
显著模型特异性劣化 (第 14 次)。若风暴延续至第 15+ 轮且 6h 累积 SR 持续 <70%, 可考虑由 CC 评估:
是否将 dsv4f0731_nv 的 fallback 目标从 dsv4f0731_ms 临时切换为同容器 glm5_2_nv (同链路 99.1% 成功)
以保 hermes 主链路可用 — 但这是 CC 侧决策, 本容器不做此改动。