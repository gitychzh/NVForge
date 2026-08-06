# R1051: RemoteDisconnected 风暴延续 (第30轮) — 模型特异性第30次复现, NOP (无参数修改)

> 时间: 2026-08-06 09:14 BJT (01:14 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF)
> 状态: **NOP (无参数修改)** — NVCFPexecRemoteDisconnected 远程瞬断风暴在 attempt 层
>   持续主导, 第 30 次复现**模型特异性** (同容器同 key 同出口 glm5_2_nv 24h SR=97.6%
>   且 0 tier 错误, dsv4f0731_nv 24h SR=59.4% + attempt 层全失败) →
>   NVCF deepseek function 级劣化, 无本容器可解参数
> 信号: hm4104 fallback 持续 (PRIMARY-BREAKER-SKIP-STREAM 直走 fallback)

## 1. 背景 (改前必有数据)

R1021-R1050 连续记录同一 RemoteDisconnected 风暴并判定模型特异性 NOP。本轮间隔 ~15min
为同一风暴第 30 轮延续。

### 30min 窗口 (pre-run 注入) — nv_requests (tier_model=dsv4f0731_nv)
- 总量 32, 200=8, 失败=24, fallback=3, **SR=25.0%**
- Avg 135776ms, p50 91803ms, p95 411223ms, max 633821ms
- 429: 0 计数
- upstream_type: nvcf_pexec 27 (200=8, SR=29.6%), ms_fallback 3 (200=0), 其他 2 (200=0)
- finish_reason: tool_calls=8, stop=1 (正常业务完成)

### 错误分类 (30min, nv_requests)
| error_type | count | avg_ms |
|---|---|---|
| all_tiers_exhausted | 16 | 175940 |
| buffer_exhausted | 3 | 219021 |
| stream_absolute_cap | 2 | 161756 |
| zombie_empty_completion | 2 | 21808 |
| client_gone_during_flush | 1 | 123396 |

### tier_attempts (30min, DB 直查) — 全失败, 0 成功
| error_type | count | avg_ms |
|---|---|---|
| NVCFPexecRemoteDisconnected | 39 | 41183 |
| 529_nv_overloaded | 11 | - |
| 504_nv_gateway_timeout | 1 | - |
| empty_200 | 1 | - |

- RemoteDisconnected 跨全 5 key 分散 (per-key 错误: k0=14, k3=2, k2=1, k4=1 的
  all_tiers_exhausted/buffer/stream 等) → 非单 key/单 SOCKS5 代理问题
- 无 429, 无 SSL 错误 → 纯远程断连/过载
- 30min 请求层 SR=25.0% 较上轮 51.4% 回落 (窗口噪声, 24h 仍 59.4%), attempt 层
  仍 0 成功行 → 风暴本质未变

### 模型特异性重验证 (24h, 全量直查)
- **glm5_2_nv 24h**: 1280 请求, 200=1249, **SR=97.6%**; 同容器同 key 同出口
- **dsv4f0731_nv 24h**: 807 请求, 200=479, **SR=59.4%**; attempt 层 0 成功行,
  RemoteDisconnected 主导
- **结论**: 同容器同 key 同出口同时窗, glm5_2_nv 97.6% vs dsv4f0731_nv 59.4% →
  模型特异性第 30 次成立。故障仅存在于 dsv4f0731_nv 具体 function 的远端执行层。

### 6h/24h 趋势
- 6h 请求层: 380 请求, 200=203, SR=53.4%, fallback=47
- 3h 逐小时 SR: 01:00=33.3%(4/12), 00:00=37.2%(29/78), 23:00=43.3%(29/67), 22:00=55.6%(40/72)
- 24h all_tiers_exhausted: 202 次

### hm4104 fallback 日志 (最近 5min)
- **PRIMARY-BREAKER-SKIP-STREAM**: primary 流式跳过 (circuit OPEN 或 fallback 冷却), 直走 fallback
- **FALLBACK-STREAM**: 从 primary 切到 ms_gw 流式
- **PRIMARY-FAIL-STREAM**: nv_gw 流式 server_5xx status=502 after 75185ms/110336ms, 切 fallback
- 说明 hm4104 断路器持续 OPEN, 用户请求持续 fallback 到 ms_gw 保活

## 2. 决策: NOP (无参数修改)

RemoteDisconnected/529_nv_overloaded/empty_200/zombie_empty 是 NVCF deepseek **远程
function 级**瞬断/劣化, 与容器 env 无关 (第 30 次确认):
- 同出口同 key 下 glm5_2_nv 24h SR=97.6% + 0 tier 错误 → 网络/mihomo/key/出口路径全部健康
- 故障仅存在于 dsv4f0731_nv 具体 function 的远端执行层
- tier_attempts 30min RemoteDisconnected=39 跨全 5 key 分散 + 529_nv_overloaded=11
  → 证明非 UPSTREAM_TIMEOUT/budget/cooldown/fastbreak 可解的 lever
- 无 429, 无 SSL 错误 → 纯远程断连/过载
- 无单 key 劣化 (错误均匀分散各 key) → 无 key 分配/冷却可调

本轮继续 NOP, 等待 NVCF 侧恢复 (第 30 轮)。模型特异性铁证 (24h glm5_2_nv 97.6% +
0 tier 错误 vs dsv4f0731_nv 59.4% + attempt 0 成功行) 第 30 次成立。hm4104 断路器
已接管用户侧 fallback (用户请求由 ms_gw 保活)。

## 3. 修改

无。参数保持: UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180,
NVU_TIER_BUDGET_DSV4F0731_NV=180, KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90,
NVU_KEYMGR_429_BASE/MAX=120, NVU_EMPTY_200_FASTBREAK=3, NVU_PEXEC_TIMEOUT_FASTBREAK=3,
NV_KEY_INTEGRATE_KEYS=(empty, 全 pexec), NV_INTEGRATE_MODELS=(empty)。

## 4. 验证

- /health: status=ok, nv_num_keys=5, nvcf_pexec_models 含 dsv4f0731_nv, port=40666 ✓
- 容器: dsvf0731_nv40666 Up 28 hours, env 读取正常 (与 R1050 一致, 无漂移) ✓
- 无 env 变更, 无需重启
- 本次 pre-run 注入的 fallback 日志 PRIMARY-BREAKER-SKIP-STREAM 为本容器自身轮次触发的
  正常 fallback 信号, 非本轮修改引起

## 5. 下一步建议

继续等待 NVCF deepseek function 侧恢复。本轮模型特异性铁证第 30 次成立 (24h glm5_2_nv
97.6%/0 tier 错误 vs dsv4f0731_nv 59.4%/attempt 0 成功行)。风暴延续 ≥36h 无衰减。
建议由 CC 评估 (非本容器决策): 是否将 hermes 主链路模型从 dsv4f0731_nv 临时切换为同为
NVCF 的 glm5_2_nv (同链路 24h ~97.6% 成功) 以消除用户侧 fallback 依赖及 ms_gw 侧时延,
或联系 NVCF 侧确认 deepseek function 健康状况。本容器保持 NOP 以待 NVCF 修复。