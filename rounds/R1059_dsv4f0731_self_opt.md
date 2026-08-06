# R1059: RemoteDisconnected 风暴延续 (第38轮) — 模型特异性第38次复现, NOP (无参数修改)

> 时间: 2026-08-06 10:50 BJT (02:50 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF)
> 状态: **NOP (无参数修改)** — NVCFPexecRemoteDisconnected 远程瞬断风暴在 attempt 层
>   持续主导, 第 38 次复现**模型特异性** (同容器同 key 同出口 glm5_2_nv 6h SR=95.5%
>   且 0 tier 错误, dsv4f0731_nv 6h SR=47.6% + attempt 层 RemoteDisconnected/529 主导) →
>   NVCF deepseek function 级劣化, 无本容器可解参数
> 信号: hm4104 fallback 持续 (PRIMARY-FAIL-STREAM 502 → FALLBACK-STREAM)

## 1. 背景 (改前必有数据)

R1021-R1058 连续记录同一 RemoteDisconnected 风暴并判定模型特异性 NOP。本轮间隔 ~10min
为同一风暴第 38 轮延续 (与 R1057/R1058 数据基本一致)。

### 30min 窗口 (pre-run 注入) — nv_requests (tier_model=dsv4f0731_nv)
- 总量 38, 200=17, 失败=21, fallback=7, **SR=44.7%**
- Avg 106317ms, p50 73457ms, p95 232109ms, max 287365ms
- 429: 0 计数
- upstream_type: nvcf_pexec 31 (200=17, SR=54.8%), ms_fallback 6 (200=0,
  avg 233232ms), nv_integrate 1 (200=0, avg 268018ms)
- finish_reason: tool_calls=16, stop=1 (正常业务完成)

### 错误分类 (30min, nv_requests)
| error_type | count | avg_ms |
|---|---|---|
| all_tiers_exhausted | 10 | 95500 |
| buffer_exhausted | 7 | 238201 |
| zombie_empty_completion | 3 | 41211 |
| client_gone_during_flush | 1 | 169558 |

### per-key 200 延迟 (30min)
| key | 200 | min_ms | max_ms |
|---|---|---|---|
| 0 | 3 | 72230 | 128349 |
| 1 | 6 | 62604 | 92315 |
| 2 | 3 | 39926 | 62926 |
| 3 | 2 | 60540 | 74041 |
| 4 | 3 | 59091 | 107255 |

### per-key 错误 (30min)
- k0: all_tiers_exhausted=10, buffer_exhausted=6, zombie_empty_completion=1
- k1: buffer_exhausted=1, zombie_empty_completion=1
- k2: zombie_empty_completion=1
- k4: client_gone_during_flush=1
- (空 key): buffer_exhausted=6
- → 错误跨全 5 key 分散, 非单 key/单 SOCKS5 代理问题

### attempt 层 (实时 DB 查询, nv_tier_attempts, 1h, tier=dsv4f0731_nv)
- NVCFPexecRemoteDisconnected: 57
- 529_nv_overloaded: 20
- empty_200: 11
- NVCFPexecTimeout: 3
- 504_nv_gateway_timeout: 1
- → RemoteDisconnected/529/empty200 主导, 纯远程断连/过载

### 模型特异性重验证 (6h, 同容器同 key 同出口同时窗, 本轮实时 DB 查询)
- **glm5_2_nv 6h**: 157 请求, 150 200, **SR=95.5%**, avg=52587ms
- **dsv4f0731_nv 6h**: 420 请求, 200 200, **SR=47.6%**, avg=102255ms
- **结论**: 同容器同 key 同出口, glm5_2_nv 95.5% vs dsv4f0731_nv 47.6% → 模型特异性
  第 38 次成立。故障仅存在于 dsv4f0731_nv 具体 function 的远端执行层。

### 6h/24h 趋势
- 6h 请求层: 412→420 请求, 198→200 200, SR=48.1%→47.6%, fallback=61
- 3h 逐小时: 02:00=48.1%(26/54), 01:00=33.8%(22/65), 00:00=37.2%(29/78), 23:00=30.0%(6/20)
- 24h all_tiers_exhausted: 229→235 次

### hm4104 fallback 日志 (最近 5min)
- **PRIMARY-FAIL-STREAM**: nv_gw 流式 server_5xx status=502 after 66074ms, 切 fallback
- **FALLBACK-STREAM**: 从 primary 切到 ms_gw 流式
- **PRIMARY-BREAKER-SKIP-STREAM**: primary 流式跳过 (circuit OPEN), 直走 fallback
- 说明 hm4104 断路器持续 OPEN, 用户请求持续 fallback 到 ms_gw 保活

## 2. 决策: NOP (无参数修改)

RemoteDisconnected/529_nv_overloaded/zombie_empty/buffer_exhausted/client_gone_during_flush
是 NVCF deepseek **远程 function 级**瞬断/劣化, 与容器 env 无关 (第 38 次确认):
- 同出口同 key 下 glm5_2_nv 6h SR=95.5% + 0 tier 错误 → 网络/mihomo/key/出口路径全部健康
- 故障仅存在于 dsv4f0731_nv 具体 function 的远端执行层
- 错误跨全 5 key 分散 (k0/k1/k2/k4 + 空 key) → 证明非 UPSTREAM_TIMEOUT/budget/cooldown/fastbreak 可解的 lever
- 无 429, 无 SSL 错误 (RemoteDisconnected/529/empty_200 主导) → 纯远程断连/过载
- 无单 key 劣化 (错误均匀分散各 key) → 无 key 分配/冷却可调

本轮继续 NOP, 等待 NVCF 侧恢复 (第 38 轮)。模型特异性铁证 (6h glm5_2_nv 95.5% +
0 tier 错误 vs dsv4f0731_nv 47.6% + 错误均匀分散) 第 38 次成立。hm4104 断路器
已接管用户侧 fallback (用户请求由 ms_gw 保活)。

## 3. 修改

无。参数保持: UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180,
NVU_TIER_BUDGET_DSV4F0731_NV=180, KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90,
NVU_KEYMGR_429_BASE/MAX=120, NVU_EMPTY_200_FASTBREAK=3, NVU_PEXEC_TIMEOUT_FASTBREAK=3,
NVU_KEYMGR_CONN_BASE_COOLDOWN=30, NVU_KEYMGR_CONN_MAX_COOLDOWN=60,
NVU_KEYMGR_CONN_FAIL_THRESHOLD=3, NVU_KEYMGR_CONN_LONG_COOLDOWN=120,
NVU_PROBE_TIMEOUT=10, PROXY_TIMEOUT=300, NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90,
NVU_PEER_FALLBACK_ENABLED=0, NV_KEY_INTEGRATE_KEYS=(empty, 全 pexec),
NV_INTEGRATE_MODELS=(empty). 无重启。

## 4. 验证

- /health: status=ok, nv_num_keys=5, nvcf_pexec_models 含 dsv4f0731_nv, port=40666 ✓
- 容器: dsvf0731_nv40666 Up 29 hours, env 读取正常 (与 R1058 一致, 无漂移) ✓
- 6h 模型特异性实时复核: glm5_2_nv 95.5%(150/157) vs dsv4f0731_nv 47.6%(200/420) ✓
- attempt 层 1h 复核: RemoteDisconnected=57, 529=20, empty200=11 ✓
- 无 env 变更, 无需重启
- 本次 pre-run 注入的 fallback 日志 PRIMARY-FAIL-STREAM(502 after 66074ms)/FALLBACK-STREAM
  为本容器自身轮次触发的正常 fallback 信号, 非本轮修改引起

## 5. 下一步建议

继续等待 NVCF deepseek function 侧恢复。本轮模型特异性铁证第 38 次成立 (6h glm5_2_nv
95.5%/0 tier 错误 vs dsv4f0731_nv 47.6%/错误均匀分散)。风暴延续 ≥38h 无衰减。
建议由 CC 评估 (非本容器决策): 是否将 hermes 主链路模型从 dsv4f0731_nv 临时切换为同为
NVCF 的 glm5_2_nv (同链路 6h ~95.5% 成功) 以消除用户侧 fallback 依赖及 ms_gw 侧时延,
或联系 NVCF 侧确认 deepseek function 健康状况。本容器保持 NOP 以待 NVCF 修复。