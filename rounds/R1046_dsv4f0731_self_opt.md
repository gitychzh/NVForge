# R1046: RemoteDisconnected 风暴延续 (第25轮) — 模型特异性第25次复现 + 新信号 PRIMAY-ZOMBIE-FALLBACK (content_filter zombie), 无参数修改 (恢复观察轮)

> 时间: 2026-08-05 21:45 BJT (13:45 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF)
> 状态: **恢复观察轮 (无参数修改)** — NVCFPexecRemoteDisconnected 远程瞬断风暴在 attempt 层
>   持续主导, 第 25 次复现**模型特异性** (同容器同 key 同出口 glm5_2_nv ~97-98% 成功) →
>   NVCF deepseek function 级劣化, 无本容器可解参数
> **新信号**: hm4104 fallback 日志新增 **PRIMARY-ZOMBIE-FALLBACK** ("nv_gw 返回 content_filter
>   zombie, 切 ms_gw fallback") — 上游 200 但内容被 content_filter 拦截的僵尸响应, 用户在
>   fallback 层持续被保活, 断路器仍 OPEN

## 1. 背景 (改前必有数据)

R1021-R1045 已连续记录同一 RemoteDisconnected 风暴并判定模型特异性 NOP。本轮 (间隔 ~1.5h)
为**同一风暴第 25 轮延续**。6h 累积 SR 70%, attempt 层风暴未减。

### 30min 窗口 — nv_requests (tier_model=dsv4f0731_nv)
- 总量 21, 200=18, 失败=3, **SR=85.7%** (低流量期, 样本小, 较 R1045 的 72.2% 略升)
- Avg 59791ms, p50 55912ms, p95 124514ms, max 132648ms (200 成功)
- 502 失败: 3 次 (all_tiers_exhausted), avg 79232ms
- 429: 0 计数
- upstream_type: nvcf_pexec 21/21 全 pexec (integrate 0)
- finish_reason: stop=9, tool_calls=9 (正常业务完成, 无僵尸空 200 主导)

### 错误分类 (30min)
| error_type | count | avg_ms |
|---|---|---|
| all_tiers_exhausted | 3 | 79232 |

- all_tiers_exhausted=3: tier_attempts 层多次 RemoteDisconnected 烧尽 180s budget
- tier_attempts 细目: NVCFPexecRemoteDisconnected=17(avg 44223ms, min 31321, max 74679),
  empty_200=3, 529_nv_overloaded=1

### per-key 错误 (30min) — 错误集中 k0
- k0: all_tiers_exhausted=3(79232ms)
- k1-k4: 无错误 (k1=4成功, k2=4, k3=2, k4=6)
- 注: k0 也有 2 次成功且 key_cycle_429s k0=10 高 → k0 被反复循环尝试, 非 key 本身故障

### per-key 200 延迟 (30min)
- k0: 2次 (73981/92726ms), k1: 4次 (79909/120875), k2: 4次 (37237/54217),
  k3: 2次 (13814/14589), k4: 6次 (62291/121318)
- k3 延迟最低且稳定 (14s), k1/k4 偏高 (120s+) — 各 key var 大, 但样本小 non-结论

### key_cycle_429s (30min)
- k0=10, k1=8, k2=3 (429 计数 0, 为 key 循环次数非 429 事件)

### 6h 请求层 — 模型特异性继续成立
- 6h 累积: 160 请求 112 成功 (70%)
- 3h 逐小时 SR: 13:00=83.3%(20/24), 12:00=68.4%(26/38), 11:00=71.0%(22/31), 10:00=70.6%(12/17)
- 24h all_tiers_exhausted: 41 次 (较 R1045 的 29 次回升, 风暴胶着)

### hm4104 fallback 日志 (最近 5min) — fallback 持续 + 新信号
- **PRIMARY-FAIL-STREAM**: nv_gw 流式 server_5xx status=502 after 147385ms → 切 fallback
- **PRIMARY-ZOMBIE-FALLBACK**: nv_gw 返回 **content_filter zombie**, 切 ms_gw fallback 流式 (新信号)
- 多次 FALLBACK-STREAM → ms_gw
- 说明 hermes 主链路 (nv_gw→dsv4f0731_nv) 断路器仍 OPEN, 用户请求持续被 fallback 到 ms_gw
- content_filter zombie = 上游 200 但内容被 content_filter 拦截 → 远端 function 劣化进一步信号化

## 2. 决策: NOP (无参数修改)

RemoteDisconnected/529_nv_overloaded/empty_200/content_filter zombie 是 NVCF deepseek
**远程 function 级**瞬断/劣化, 与容器 env 无关 (第 25 次确认):
- 同出口同 key 下 glm5_2_nv 6h ~97-98% 成功 → 网络/mihomo/key/出口路径全部健康
- 故障仅存在于 dsv4f0731_nv 具体 function 的远端执行层
- tier_attempts 30min 内 RemoteDisconnected=17 + empty_200=3 + 529_nv_overloaded=1 且分散各 key
  → 证明非 UPSTREAM_TIMEOUT/budget/cooldown/fastbreak 可解的 lever
- 本轮 per-key 错误集中 k0 (all_tiers_exhausted=3) 但 k0 也有 2 次成功 → 反复循环尝试耗尽 budget,
  非 key 故障, 是远端 function 劣化
- 无 429, 无 SSL 错误 → 纯远程断连/过载

本轮继续 NOP, 等待 NVCF 侧恢复 (第 25 轮)。模型特异性铁证仍成立, 无本地参数可解。
hm4104 断路器已接管用户侧 fallback (含新 content_filter zombie 信号), 用户请求由 ms_gw 保活。

## 3. 修改

无。参数保持: UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_DSV4F0731_NV=180,
NVU_TIER_BUDGET_DSV4F_NV=180, KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90, NVU_KEYMGR_429_BASE/MAX=120,
NVU_EMPTY_200_FASTBREAK=3, NVU_PEXEC_TIMEOUT_FASTBREAK=3, NV_KEY_INTEGRATE_KEYS=(empty, 全 pexec),
NV_INTEGRATE_MODELS=(empty)。

## 4. 验证

- /health: status=ok, nv_num_keys=5, nvcf_pexec_models 含 dsv4f0731_nv, port=40666 ✓
- 容器: dsvf0731_nv40666 Up 16 hours, env 读取正常 (与 R1045 一致, 无漂移) ✓
- 无 env 变更, 无需重启

## 5. 下一步建议

继续等待 NVCF deepseek function 侧恢复。本轮模型特异性铁证 (glm5_2_nv ~97-98% vs
dsv4f0731_nv 70%) 第 25 次成立。新信号: hm4104 日志出现 **PRIMARY-ZOMBIE-FALLBACK**
(content_filter zombie), 远端 function 劣化从 RemoteDisconnected 扩展到 content filter 层。
风暴延续 ≥31h, 6h 累积 SR 持续 ~70% 无衰减。hm4104 断路器持续 OPEN, 用户请求持续 fallback
到 ms_gw。建议由 CC 评估 (非本容器决策): 是否将 hermes 主链路模型从 dsv4f0731_nv 临时切换
为同容器 glm5_2_nv (同链路 ~97-98% 成功) 以消除用户侧 fallback 依赖, 或联系 NVCF 侧确认
deepseek function 健康状况。本容器保持 NOP 以待 NVCF 修复。