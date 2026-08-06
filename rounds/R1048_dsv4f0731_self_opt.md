# R1048: RemoteDisconnected 风暴延续 (第27轮) — 模型特异性第27次复现, NOP (无参数修改)

> 时间: 2026-08-06 08:30 BJT (00:30 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF)
> 状态: **NOP (无参数修改)** — NVCFPexecRemoteDisconnected 远程瞬断风暴在 attempt 层
>   持续主导, 第 27 次复现**模型特异性** (同容器同 key 同出口 glm5_2_nv 24h SR=90.3% 且
>   tier_attempts 0 错误) → NVCF deepseek function 级劣化, 无本容器可解参数
> 信号: hm4104 fallback 持续 (PRIMARY-BREAKER-SKIP-STREAM 直走 fallback)

## 1. 背景 (改前必有数据)

R1021-R1047 连续记录同一 RemoteDisconnected 风暴并判定模型特异性 NOP。本轮间隔 ~15min
为同一风暴第 27 轮延续。

### 30min 窗口 (pre-run 注入) — nv_requests (tier_model=dsv4f0731_nv)
- 总量 30, 200=8, 失败=22, fallback=3, **SR=26.7%**
- Avg 113608ms, p50 86911ms, p95 241784ms, max 247713ms
- 429: 0 计数
- upstream_type: nvcf_pexec 27 请求 (200=8, SR=29.6%), ms_fallback 2 (SR=0%), nv_integrate 1 (SR=0%)
- finish_reason: tool_calls=7, stop=1

### 错误分类 (30min, nv_requests)
| error_type | count | avg_ms |
|---|---|---|
| all_tiers_exhausted | 15 | 103853 |
| buffer_exhausted | 3 | 244018 |
| client_gone_during_flush | 3 | 189718 |
| zombie_empty_completion | 1 | 52414 |

### tier_attempts (30min) — 全部 key 分散失败
| error_type | count |
|---|---|
| NVCFPexecRemoteDisconnected | 31 |
| 529_nv_overloaded | 14 |
| empty_200 | 5 |
| 504_nv_gateway_timeout | 2 |
| NVCFPexecTimeout | 2 |

- RemoteDisconnected 跨全 5 key 分散 (k0:8 k1:4 k2:7 k3:6 k4:7) → 非单 key/单 SOCKS5 代理问题
- 无 429, 无 SSL 错误 → 纯远程断连/过载

### 模型特异性重验证 (本轮关键, 排除窗口噪声)
- glm5_2_nv 24h: SR=90.3% (1255/1390), tier_attempts **1319 次 0 错误**
- dsv4f0731_nv 24h: SR=67.1% (464/691), tier_attempts RemoteDisconnected=505 (76%), 529=62, 0 ok
- dsv4p_nv 24h: SR=0.0% (0/64, 低流量)
- 30min 窗口 glm5_2_nv 曾现 13.3% (2/15) → 小样本噪声, 被 24h 90.3% + 0 tier 错误证伪
- **结论**: 同容器同 key 同出口下 glm5_2_nv 稳定成功, 故障仅存在于 dsv4f0731_nv 具体
  function 的远端执行层 → 模型特异性第 27 次成立

### 6h/24h 趋势
- 6h 请求层: 346 请求, 200=193, SR=55.8%, fallback=43
- 24h all_tiers_exhausted: 178 次

### hm4104 fallback 日志 (最近 5min)
- **PRIMARY-BREAKER-SKIP-STREAM**: primary 流式跳过 (circuit OPEN 或 fallback 冷却), 直走 fallback
- **FALLBACK-STREAM**: 从 primary 切到 ms_gw 流式
- **PRIMARY-FAIL-STREAM**: nv_gw 流式 server_5xx status=502 after 76931ms, 切 fallback
- 说明 hm4104 断路器持续 OPEN, 用户请求持续 fallback 到 ms_gw 保活

## 2. 决策: NOP (无参数修改)

RemoteDisconnected/529_nv_overloaded/empty_200/zombie_empty 是 NVCF deepseek **远程
function 级**瞬断/劣化, 与容器 env 无关 (第 27 次确认):
- 同出口同 key 下 glm5_2_nv 24h SR 90.3% + 1319 次 tier_attempts 0 错误 → 网络/mihomo/
  key/出口路径全部健康
- 故障仅存在于 dsv4f0731_nv 具体 function 的远端执行层
- tier_attempts 30min RemoteDisconnected=31 跨全 5 key 分散 + 529_nv_overloaded=14
  → 证明非 UPSTREAM_TIMEOUT/budget/cooldown/fastbreak 可解的 lever
- 无 429, 无 SSL 错误 → 纯远程断连/过载
- 无单 key 劣化 (RemoteDisconnected 均匀分散各 key) → 无 key 分配/冷却可调

本轮继续 NOP, 等待 NVCF 侧恢复 (第 27 轮)。模型特异性铁证 (24h glm5_2_nv 90.3% vs
dsv4f0731_nv 67.1%) 第 27 次成立, 且本轮用 24h 而非 30min 窗口排除了 glm5_2_nv 小样本
噪声干扰。hm4104 断路器已接管用户侧 fallback (用户请求由 ms_gw 保活)。

## 3. 修改

无。参数保持: UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180,
NVU_TIER_BUDGET_DSV4F0731_NV=180, NVU_TIER_BUDGET_DSV4F_NV=180, KEY_COOLDOWN_S=30,
TIER_COOLDOWN_S=90, NVU_KEYMGR_429_BASE/MAX=120, NVU_EMPTY_200_FASTBREAK=3,
NVU_PEXEC_TIMEOUT_FASTBREAK=3, NV_KEY_INTEGRATE_KEYS=(empty, 全 pexec),
NV_INTEGRATE_MODELS=(empty)。

## 4. 验证

- /health: status=ok, nv_num_keys=5, nvcf_pexec_models 含 dsv4f0731_nv, port=40666 ✓
- 容器: dsvf0731_nv40666 Up 27 hours, env 读取正常 (与 R1047 一致, 无漂移) ✓
- 无 env 变更, 无需重启
- 本次 pre-run 注入的 fallback 日志 PRIMARY-BREAKER-SKIP-STREAM 为本容器自身轮次触发的
  正常 fallback 信号, 非本轮修改引起

## 5. 下一步建议

继续等待 NVCF deepseek function 侧恢复。本轮模型特异性铁证第 27 次成立 (24h glm5_2_nv
90.3% + 0 tier 错误 vs dsv4f0731_nv 67.1% + 505 RemoteDisconnected)。风暴延续 ≥33h 无衰减。
建议由 CC 评估 (非本容器决策): 是否将 hermes 主链路模型从 dsv4f0731_nv 临时切换为同为
NVCF 的 glm5_2_nv (同链路 24h ~90% 成功) 以消除用户侧 fallback 依赖及 ms_gw 侧时延, 或
联系 NVCF 侧确认 deepseek function 健康状况。本容器保持 NOP 以待 NVCF 修复。