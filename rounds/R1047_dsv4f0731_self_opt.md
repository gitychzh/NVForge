# R1047: RemoteDisconnected 风暴延续 (第26轮) — 模型特异性第26次复现, NOP (无参数修改)

> 时间: 2026-08-06 08:15 BJT (00:15 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF)
> 状态: **NOP (无参数修改)** — NVCFPexecRemoteDisconnected 远程瞬断风暴在 attempt 层
>   持续主导, 第 26 次复现**模型特异性** (同容器同 key 同出口 glm5_2_nv ~97-98% 成功) →
>   NVCF deepseek function 级劣化, 无本容器可解参数
> 信号: hm4104 fallback 持续 (PRIMARY-BREAKER-SKIP-STREAM 直走 fallback), 加上新近
>   FALLBACK-FAIL-STREAM ms_gw timeout (ms_gw 侧也出现 70s ttfb timeout)

## 1. 背景 (改前必有数据)

R1021-R1046 连续记录同一 RemoteDisconnected 风暴并判定模型特异性 NOP。本轮间隔 ~10h
为同一风暴第 26 轮延续。tier_attempts 6h 每整时段 0 成功全失败, 无衰减。

### 30min 窗口 — nv_requests (tier_model=dsv4f0731_nv)
- 总量 33, 200=10, 失败=23, **SR=30.3%**
- Avg 104947ms, p50 87505ms, p95 238594ms, max 238671ms (200 成功)
- 502 失败: 22 (all_tiers_exhausted/buffer_exhausted), 499: 4 (client_gone_during_flush)
- 429: 0 计数
- upstream_type: nvcf_pexec 29/29 (SR=34.5%, 10/29), ms_fallback 3 (SR=0%), nv_integrate 1 (SR=0%)
- finish_reason: tool_calls=8, stop=2 (正常业务完成)

### 错误分类 (30min)
| error_type | count | avg_ms |
|---|---|---|
| all_tiers_exhausted | 13 | 99241 |
| buffer_exhausted | 4 | 227596 |
| client_gone_during_flush | 3 | 193359 |
| zombie_empty_completion | 3 | 45414 |

### tier_attempts (30min) — 47 次尝试, 0 成功, 全失败
| error_type | count | avg_ms | min_ms | max_ms |
|---|---|---|---|---|
| NVCFPexecRemoteDisconnected | 32 | 42502 | 30815 | 60626 |
| 529_nv_overloaded | 9 | - | - | - |
| NVCFPexecTimeout | 2 | 33106 | 28129 | 38082 |
| 504_nv_gateway_timeout | 2 | - | - | - |
| empty_200 | 2 | - | - | - |

- RemoteDisconnected 跨全 5 key 分散 (k0:8 k1:4 k2:7 k3:6 k4:7) → 非单 key/单 SOCKS5 代理问题
- 529_nv_overloaded=9 分散 k1/k3/k4 → NVCF 侧过载

### per-key 200 延迟 (30min) — 样本小, 方差大
- k0: 2 (22523/23557), k1: 2 (76095/99669), k2: 3 (33299/45597), k3: 1 (91756), k4: 2 (78762/86631)

### 6h/24h 趋势 — 风暴胶着无衰减
- 6h 请求层: 346 请求, 200=146, **SR=42.2%**, fallback=42
- 3h 逐小时 SR: 00:00=30.8%(4/13), 23:00=43.3%(29/67), 22:00=54.9%(45/82), 21:00=67.5%(27/40)
- 24h tier_attempts: 638 次, 0 成功, RemoteDisconnected=485 (avg 40687ms) — 76% 尝试被远程瞬断烧掉
- 24h all_tiers_exhausted: 170 次

### hm4104 fallback 日志 (最近 5min) — fallback 持续 + ms_gw 侧新信号
- **PRIMARY-BREAKER-SKIP-STREAM**: primary 流式跳过 (circuit OPEN 或 fallback 冷却), 直走 fallback
- **FALLBACK-STREAM**: 从 primary 切到 ms_gw 流式
- **FALLBACK-FAIL-STREAM**: ms_gw 流式 timeout status=0 after 70075ms (header/ttfb timeout after 70s)
- 说明 hm4104 断路器持续 OPEN, 用户请求持续 fallback 到 ms_gw; 且 fallback 侧 ms_gw 也出现
  70s ttfb timeout (ms_gw 链路自身也受 NVCF 过载波及)

## 2. 决策: NOP (无参数修改)

RemoteDisconnected/529_nv_overloaded/empty_200/zombie_empty 是 NVCF deepseek **远程
function 级**瞬断/劣化, 与容器 env 无关 (第 26 次确认):
- 同出口同 key 下 glm5_2_nv ~97-98% 成功 → 网络/mihomo/key/出口路径全部健康
- 故障仅存在于 dsv4f0731_nv 具体 function 的远端执行层
- tier_attempts 30min RemoteDisconnected=32 跨全 5 key 分散 + 529_nv_overloaded=9
  → 证明非 UPSTREAM_TIMEOUT/budget/cooldown/fastbreak 可解的 lever
- 无 429, 无 SSL 错误 → 纯远程断连/过载
- 无单 key 劣化 (RemoteDisconnected 均匀分散各 key) → 无 key 分配/冷却可调

本轮继续 NOP, 等待 NVCF 侧恢复 (第 26 轮)。模型特异性铁证仍成立, 无本地参数可解。
hm4104 断路器已接管用户侧 fallback (用户请求由 ms_gw 保活, 但 ms_gw 侧也出现 70s
ttfb timeout, 说明 NVCF 过载波及 fallback 链路)。

## 3. 修改

无。参数保持: UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180,
NVU_TIER_BUDGET_DSV4F0731_NV=180, NVU_TIER_BUDGET_DSV4F_NV=180, KEY_COOLDOWN_S=30,
TIER_COOLDOWN_S=90, NVU_KEYMGR_429_BASE/MAX=120, NVU_EMPTY_200_FASTBREAK=3,
NVU_PEXEC_TIMEOUT_FASTBREAK=3, NV_KEY_INTEGRATE_KEYS=(empty, 全 pexec),
NV_INTEGRATE_MODELS=(empty)。

## 4. 验证

- /health: status=ok, nv_num_keys=5, nvcf_pexec_models 含 dsv4f0731_nv, port=40666 ✓
- 容器: dsvf0731_nv40666 Up 27 hours, env 读取正常 (与 R1046 一致, 无漂移) ✓
- 无 env 变更, 无需重启
- 本次 pre-run 注入的 fallback 日志 PRIMARY-BREAKER-SKIP-STREAM 为本容器自身轮次触发的
  正常 fallback 信号, 非本轮修改引起

## 5. 下一步建议

继续等待 NVCF deepseek function 侧恢复。本轮模型特异性铁证 (glm5_2_nv ~97-98% vs
dsv4f0731_nv 30-42%) 第 26 次成立。风暴延续 ≥33h, 24h tier_attempts RemoteDisconnected=485
(76%) 无衰减。新信号: ms_gw fallback 侧也出现 70s ttfb timeout (FALLBACK-FAIL-STREAM),
NVCF 过载波及 fallback 链路。建议由 CC 评估 (非本容器决策): 是否将 hermes 主链路模型从
dsv4f0731_nv 临时切换为同容器 glm5_2_nv (同链路 ~97-98% 成功) 以消除用户侧 fallback 依赖
及 ms_gw 侧时延, 或联系 NVCF 侧确认 deepseek function 健康状况。本容器保持 NOP 以待
NVCF 修复。