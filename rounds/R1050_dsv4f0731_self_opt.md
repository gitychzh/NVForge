# R1050: RemoteDisconnected 风暴延续 (第29轮) — 模型特异性第29次复现, NOP (无参数修改)

> 时间: 2026-08-06 09:00 BJT (01:00 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF)
> 状态: **NOP (无参数修改)** — NVCFPexecRemoteDisconnected 远程瞬断风暴在 attempt 层
>   持续主导, 第 29 次复现**模型特异性** (同容器同 key 同出口 glm5_2_nv 24h SR=97.6%
>   且 attempt 层 1271/1319=96.4% 成功, dsv4f0731_nv 718 次 attempt 0 成功行) →
>   NVCF deepseek function 级劣化, 无本容器可解参数
> 信号: hm4104 fallback 持续 (PRIMARY-BREAKER-SKIP-STREAM 直走 fallback)

## 1. 背景 (改前必有数据)

R1021-R1049 连续记录同一 RemoteDisconnected 风暴并判定模型特异性 NOP。本轮间隔 ~15min
为同一风暴第 29 轮延续。

### 30min 窗口 (pre-run 注入) — nv_requests (tier_model=dsv4f0731_nv)
- 总量 38, 200=19, 失败=19, fallback=3, **SR=50.0%**
- Avg 89632ms, p50 71060ms, p95 222224ms, max 248114ms
- 429: 0 计数
- upstream_type: nvcf_pexec 35 (200=19, SR=54.3%), ms_fallback 3 (200=0)
- finish_reason: tool_calls=18, stop=1 (正常业务完成)

### 错误分类 (30min, nv_requests)
| error_type | count | avg_ms |
|---|---|---|
| all_tiers_exhausted | 12 | 113557 |
| buffer_exhausted | 3 | 228000 |
| zombie_empty_completion | 2 | 16528 |
| client_gone_during_flush | 1 | 221983 |
| stream_absolute_cap | 1 | 171820 |

### tier_attempts (30min, DB 直查) — 全失败, 0 成功
| error_type | count | avg_ms |
|---|---|---|
| NVCFPexecRemoteDisconnected | 28 | 37263 |
| empty_200 | 11 | - |
| 529_nv_overloaded | 10 | - |
| NVCFPexecTimeout | 2 | 21299 |
| 504_nv_gateway_timeout | 1 | - |

- RemoteDisconnected 跨全 5 key 分散 → 非单 key/单 SOCKS5 代理问题
- 无 429, 无 SSL 错误 → 纯远程断连/过载
- 30min 请求层 200=19 (SR=50%) 较上轮 51.4% 基本持平, attempt 层仍 0 成功行 →
  风暴本质未变

### 模型特异性重验证 (24h, 全量直查)
- **glm5_2_nv 24h**: 请求层 1278 请求, 200=1247, **SR=97.6%**; attempt 层 1319 次,
  error_type 含 `pexec_success`=1271 (即 96.4% 成功行), 仅 27 RD + 9 empty_200 + 5 429
  + 4 SSLEOF + 3 504
- **dsv4f0731_nv 24h**: 请求层 786 请求, 200=471, **SR=59.9%**; attempt 层 718 次,
  **error_type 全为失败类型, 0 成功行**: NVCFPexecRemoteDisconnected=537 (75%),
  empty_200=96, 529_nv_overloaded=67, NVCFPexecTimeout=13, 504=5
- **结论**: 同容器同 key 同出口同时窗, glm5_2_nv 97.6% vs dsv4f0731_nv 59.9% →
  模型特异性第 29 次成立。故障仅存在于 dsv4f0731_nv 具体 function 的远端执行层。
  注意 error_type 命名差异: glm5_2_nv 成功行记 `pexec_success`, dsv4f0731_nv 则不记
  成功行 (全失败类型) — 进一步佐证 deepseek function 侧 attempt 层几乎全失败。

### 6h/24h 趋势
- 6h 请求层: 365 请求, 200=200, SR=54.8%, fallback=165
- 24h all_tiers_exhausted: 191 次

### hm4104 fallback 日志 (最近 5min)
- **PRIMARY-BREAKER-SKIP-STREAM**: primary 流式跳过 (circuit OPEN 或 fallback 冷却), 直走 fallback
- **FALLBACK-STREAM**: 从 primary 切到 ms_gw 流式
- **PRIMARY-FAIL-STREAM**: nv_gw 流式 server_5xx status=502 after 180058ms/151884ms, 切 fallback
- 说明 hm4104 断路器持续 OPEN, 用户请求持续 fallback 到 ms_gw 保活

## 2. 决策: NOP (无参数修改)

RemoteDisconnected/529_nv_overloaded/empty_200/zombie_empty 是 NVCF deepseek **远程
function 级**瞬断/劣化, 与容器 env 无关 (第 29 次确认):
- 同出口同 key 下 glm5_2_nv 24h SR=97.6% + attempt 层 96.4% 成功 → 网络/mihomo/key/
  出口路径全部健康
- 故障仅存在于 dsv4f0731_nv 具体 function 的远端执行层
- tier_attempts 30min RemoteDisconnected=28 跨全 5 key 分散 + 529_nv_overloaded=10
  → 证明非 UPSTREAM_TIMEOUT/budget/cooldown/fastbreak 可解的 lever
- 无 429, 无 SSL 错误 → 纯远程断连/过载
- 无单 key 劣化 (RD 均匀分散各 key) → 无 key 分配/冷却可调

本轮继续 NOP, 等待 NVCF 侧恢复 (第 29 轮)。模型特异性铁证 (24h glm5_2_nv 97.6% +
attempt 96.4% 成功 vs dsv4f0731_nv 59.9% + attempt 0 成功行) 第 29 次成立, 且本轮用
24h 全量 attempt 层 (error_type 含 pexec_success) 从纵深确证故障在 deepseek function
而非链路。hm4104 断路器已接管用户侧 fallback (用户请求由 ms_gw 保活)。

## 3. 修改

无。参数保持: UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180,
NVU_TIER_BUDGET_DSV4F0731_NV=180, KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90,
NVU_KEYMGR_429_BASE/MAX=120, NVU_EMPTY_200_FASTBREAK=3, NVU_PEXEC_TIMEOUT_FASTBREAK=3,
NV_KEY_INTEGRATE_KEYS=(empty, 全 pexec), NV_INTEGRATE_MODELS=(empty)。

## 4. 验证

- /health: status=ok, nv_num_keys=5, nvcf_pexec_models 含 dsv4f0731_nv, port=40666 ✓
- 容器: dsvf0731_nv40666 Up 27 hours, env 读取正常 (与 R1049 一致, 无漂移) ✓
- 无 env 变更, 无需重启
- 本次 pre-run 注入的 fallback 日志 PRIMARY-BREAKER-SKIP-STREAM 为本容器自身轮次触发的
  正常 fallback 信号, 非本轮修改引起

## 5. 下一步建议

继续等待 NVCF deepseek function 侧恢复。本轮模型特异性铁证第 29 次成立 (24h glm5_2_nv
97.6%/attempt 96.4% vs dsv4f0731_nv 59.9%/attempt 0 成功行)。风暴延续 ≥35h 无衰减。
建议由 CC 评估 (非本容器决策): 是否将 hermes 主链路模型从 dsv4f0731_nv 临时切换为同为
NVCF 的 glm5_2_nv (同链路 24h ~97.6% 成功) 以消除用户侧 fallback 依赖及 ms_gw 侧时延,
或联系 NVCF 侧确认 deepseek function 健康状况。本容器保持 NOP 以待 NVCF 修复。