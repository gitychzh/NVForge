# R1042: RemoteDisconnected 风暴延续 (第21轮) — 模型特异性第21次复现, 无参数修改 (恢复观察轮)

> 时间: 2026-08-05 17:12 BJT (09:12 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF)
> 状态: **恢复观察轮 (无参数修改)** — NVCFPexecRemoteDisconnected 远程瞬断风暴持续主导,
>   且第 21 次复现**模型特异性** (同容器同 key 同出口 glm5_2_nv 94.1% 成功) → NVCF
>   deepseek function 级劣化, 无本容器可解参数
> Fallback: hm4104 最近 5min 有 fallback 日志 (PRIMARY-FAIL-STREAM 502 → ms_gw)

## 1. 背景 (改前必有数据)

R1021-R1041 已连续记录同一 RemoteDisconnected 风暴并判定模型特异性 NOP。本轮 (间隔 ~35min)
为**同一风暴第 21 轮延续**, 数据复现 R1041 结论, 无恢复信号。

### 30min 窗口 — nv_requests (tier_model=dsv4f0731_nv)
- 总量 11, 200=5, 失败=6, **SR=45.5%** (窗口内业务流量极少, 波动大)
- Avg 88701ms (受 6 次 all_tiers_exhausted 长失败拖累), 失败 avg 103488ms
- 429: 0 (key_cycle_429s 非主导)
- upstream_type: nvcf_pexec 11/11 全 pexec (integrate 0)
- 错误分类: all_tiers_exhausted=6 (全部烧尽 180s budget)
- 6 次失败全为 all_tiers_exhausted → tier_attempts 层多次 RemoteDisconnected 烧尽 key

### tier_attempts (30min) — 错误分类
| error_type | count |
|---|---|
| pexec_success | 50 |
| NVCFPexecRemoteDisconnected | 12 |
| empty_200 | 4 |
| NVCFPexecTimeout | 1 |

- **RemoteDisconnected 风暴仍在 attempt 层持续 (12次/30min)**, 只是部分被重试吸收
- 本次新增 empty_200=4 (上游返回 200 但无内容, 劣化信号)
- 无 SSL 错误 → 纯远程断连/过载, 非本地超时/代理问题
- 错误分散在各 key → 远端随机瞬断

### 关键证据 — 模型特异性第 21 次复现 (同容器同窗 30min, 请求层)
| tier_model | total | ok | SR |
|---|---|---|---|
| glm5_2_nv    |  51 |  48 | **94.1%** |
| dsv4f0731_nv |  12 |   6 | **50.0%** |

- 同一容器、同一 5 组 NVU_KEY、同一 5 个 mihomo 出口
- glm5_2_nv 同链路 48/51=94.1% 成功 → 故障隔离到 deepseek 的具体 NVCF function
- 证据第 21 次成立, 变量隔离彻底干净

### Fallback 日志 (hm4104, 最近 5min)
- `PRIMARY-FAIL-STREAM`: nv_gw 流式 server_5xx status=502 after 96299ms, 切 fallback
- `FALLBACK-STREAM`: 从 primary 切到 ms_gw 流式
- → hermes 主链路 (dsv4f0731_nv) 确实失败, 已由 hm4104 自动 fallback 到 ms_gw, 用户零感知

### 趋势 (6h)
- 6h 累积: 194 请求 129 成功 (**66.5%**) — 风暴持续, 无单调恢复
- 24h ATE: all_tiers_exhausted=181 次
- 逐小时 SR: 09:00=50%, 08:00=73.1%, 07:00=54.8%, 06:00=64.5% — 随机波动, 无恢复趋势

## 2. 决策: NOP (无参数修改)

RemoteDisconnected/529_nv_overloaded/empty_200 是 NVCF deepseek **远程 function 级**瞬断/过载,
与容器 env 无关 (第 21 次确认):
- 同出口同 key 下 glm5_2_nv 48/51=94.1% 成功 → 网络/mihomo/key/出口路径全部健康
- 故障仅存在于 dsv4f0731_nv 具体 function 的远端执行层
- tier_attempts 30min 内 NVCFPexecRemoteDisconnected=12 + empty_200=4 且分散各 key → 证明非
  UPSTREAM_TIMEOUT/budget/cooldown/fastbreak 可解的 lever
- 窗口 SR 波动 (50%↔92.9%) 为低流量噪声, 非真实恢复 — 6h 累积仍 66.5%

本轮继续 NOP, 等待 NVCF 侧恢复 (第 21 轮)。模型特异性铁证仍成立, 无本地参数可解。

## 3. 修改

无。参数保持: UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_DSV4F0731_NV=180,
NVU_TIER_BUDGET_DSV4F_NV=180, KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90, NVU_KEYMGR_429_BASE/MAX=120,
NVU_EMPTY_200_FASTBREAK=3, NVU_PEXEC_TIMEOUT_FASTBREAK=3, NV_KEY_INTEGRATE_KEYS=(empty, 全 pexec),
NV_INTEGRATE_MODELS=(empty)。

## 4. 验证

- /health: status=ok, nv_num_keys=5, nvcf_pexec_models 含 dsv4f0731_nv, port=40666 ✓
- 容器: dsvf0731_nv40666 Up 12 hours, env 读取正常 ✓
- 无 env 变更, 无需重启

## 5. 下一步建议

继续等待 NVCF deepseek function 侧恢复。本轮模型特异性铁证 (glm5_2_nv 94.1% vs
dsv4f0731_nv 50%) 第 21 次成立。风暴已延续 21 轮 (≥24h), 6h 累积 SR 持续 ~66%, 无衰减
迹象, 且本轮新增 empty_200 劣化信号。hm4104 已确认 fallback 到 ms_gw (用户零感知)。
建议由 CC 评估 (非本容器决策): 是否将 dsv4f0731_nv 的 fallback 目标临时切换为同容器
glm5_2_nv (同链路 ~94% 成功) 以保 hermes 主链路可用, 或联系 NVCF 侧确认 deepseek function
健康状况。本容器保持 NOP 以待 NVCF 修复。