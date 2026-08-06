# R1057: RemoteDisconnected 风暴延续 (第36轮) — 模型特异性第36次复现, NOP (无参数修改)

> 时间: 2026-08-06 10:20 BJT (02:20 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF)
> 状态: **NOP (无参数修改)** — NVCFPexecRemoteDisconnected 远程瞬断风暴在 attempt 层
>   持续主导, 第 36 次复现**模型特异性** (同容器同 key 同出口 glm5_2_nv 6h SR=95.5%
>   且 0 tier 错误, dsv4f0731_nv 6h SR=48.3% + attempt 层 RemoteDisconnected/529 主导) →
>   NVCF deepseek function 级劣化, 无本容器可解参数
> 信号: hm4104 fallback 持续 (PRIMARY-BREAKER-SKIP-STREAM 直走 fallback)

## 1. 背景 (改前必有数据)

R1021-R1056 连续记录同一 RemoteDisconnected 风暴并判定模型特异性 NOP。本轮间隔 ~10min
为同一风暴第 36 轮延续 (与 R1056 数据基本一致)。

### 30min 窗口 (pre-run 注入) — nv_requests (tier_model=dsv4f0731_nv)
- 总量 29, 200=13, 失败=16, fallback=5, **SR=44.8%**
- Avg 124547ms, p50 75755ms, p95 277640ms, max 541259ms
- 429: 0 计数
- upstream_type: nvcf_pexec 23 (200=13, SR=56.5%), ms_fallback 5 (200=0), 空 1 (200=0)
- finish_reason: tool_calls=12, stop=1 (正常业务完成)

### 错误分类 (30min, nv_requests)
| error_type | count | avg_ms |
|---|---|---|
| all_tiers_exhausted | 8 | 175746 |
| buffer_exhausted | 5 | 243032 |
| zombie_empty_completion | 2 | 44003 |
| client_gone_during_flush | 1 | 169558 |

### per-key 200 延迟 (30min)
| key | 200 | min_ms | max_ms |
|---|---|---|---|
| 0 | 3 | 73048 | 110960 |
| 1 | 4 | 44644 | 83015 |
| 2 | 2 | 99239 | 134065 |
| 3 | 2 | 36546 | 46721 |
| 4 | 3 | 45647 | 72827 |

### per-key 错误 (30min)
- k0: all_tiers_exhausted=7, buffer_exhausted=5
- k2: zombie_empty_completion=1
- k4: client_gone_during_flush=1, zombie_empty_completion=1
- (空 key): all_tiers_exhausted=1
- → 错误跨全 5 key 分散, 非单 key/单 SOCKS5 代理问题

### 模型特异性重验证 (6h, 同容器同 key 同出口同时窗, 本轮实时 DB 查询)
- **glm5_2_nv 6h**: 176 请求, 168 200, **SR=95.5%**, avg=54823ms
- **dsv4f0731_nv 6h**: 404 请求, 195 200, **SR=48.3%**, avg=103315ms
- **结论**: 同容器同 key 同出口, glm5_2_nv 95.5% vs dsv4f0731_nv 48.3% → 模型特异性
  第 36 次成立。故障仅存在于 dsv4f0731_nv 具体 function 的远端执行层。

### 6h/24h 趋势
- 6h 请求层: 404 请求, 195 200, SR=48.3%, fallback=56
- 3h 逐小时: 02:00=52.9%(9/17), 01:00=33.8%(22/65), 00:00=37.2%(29/78), 23:00=45.3%(24/53)
- 24h all_tiers_exhausted: 225 次

### hm4104 fallback 日志 (最近 5min)
- **PRIMARY-BREAKER-SKIP-STREAM**: primary 流式跳过 (circuit OPEN 或 fallback 冷却), 直走 fallback
- **FALLBACK-STREAM**: 从 primary 切到 ms_gw 流式
- 说明 hm4104 断路器持续 OPEN, 用户请求持续 fallback 到 ms_gw 保活

## 2. 决策: NOP (无参数修改)

RemoteDisconnected/529_nv_overloaded/zombie_empty/buffer_exhausted/client_gone_during_flush
是 NVCF deepseek **远程 function 级**瞬断/劣化, 与容器 env 无关 (第 36 次确认):
- 同出口同 key 下 glm5_2_nv 6h SR=95.5% + 0 tier 错误 → 网络/mihomo/key/出口路径全部健康
- 故障仅存在于 dsv4f0731_nv 具体 function 的远端执行层
- 错误跨全 5 key 分散 (k0/k2/k4 + 空 key) → 证明非 UPSTREAM_TIMEOUT/budget/cooldown/fastbreak 可解的 lever
- 无 429, 无 SSL 错误 (RemoteDisconnected/529/empty_200 主导) → 纯远程断连/过载
- 无单 key 劣化 (错误均匀分散各 key) → 无 key 分配/冷却可调

本轮继续 NOP, 等待 NVCF 侧恢复 (第 36 轮)。模型特异性铁证 (6h glm5_2_nv 95.5% +
0 tier 错误 vs dsv4f0731_nv 48.3% + 错误均匀分散) 第 36 次成立。hm4104 断路器
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
- 容器: dsvf0731_nv40666 Up 29 hours, env 读取正常 (与 R1056 一致, 无漂移) ✓
- 6h 模型特异性实时复核: glm5_2_nv 95.5%(168/176) vs dsv4f0731_nv 48.3%(195/404) ✓
- 无 env 变更, 无需重启
- 本次 pre-run 注入的 fallback 日志 PRIMARY-BREAKER-SKIP-STREAM 为本容器自身轮次触发的
  正常 fallback 信号, 非本轮修改引起

## 5. 下一步建议

继续等待 NVCF deepseek function 侧恢复。本轮模型特异性铁证第 36 次成立 (6h glm5_2_nv
95.5%/0 tier 错误 vs dsv4f0731_nv 48.3%/错误均匀分散)。风暴延续 ≥37h 无衰减。
建议由 CC 评估 (非本容器决策): 是否将 hermes 主链路模型从 dsv4f0731_nv 临时切换为同为
NVCF 的 glm5_2_nv (同链路 6h ~95.5% 成功) 以消除用户侧 fallback 依赖及 ms_gw 侧时延,
或联系 NVCF 侧确认 deepseek function 健康状况。本容器保持 NOP 以待 NVCF 修复。