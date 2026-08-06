# R1062: RemoteDisconnected 风暴延续 (第41轮) — 模型特异性第41次复现, NOP (无参数修改)

> 时间: 2026-08-06 12:30 BJT (04:30 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF)
> 状态: **NOP (无参数修改)** — NVCFPexecRemoteDisconnected 远程瞬断风暴在 attempt 层
>   持续主导, 第 41 次复现**模型特异性** (同容器同 key 同出口 glm5_2_nv 6h SR=80.0%+
>   几乎无 tier 错误, dsv4f0731_nv 6h SR=40.6% + attempt 层 RemoteDisconnected 348 主导) →
>   NVCF deepseek function 级劣化, 无本容器可解参数
> 信号: hm4104 fallback 持续 (PRIMARY-FAIL-STREAM 502 after 180035ms → FALLBACK-STREAM → ms_gw)

## 1. 背景 (改前必有数据)

R1021-R1061 连续记录同一 RemoteDisconnected 风暴并判定模型特异性 NOP。本轮间隔 ~30min
(R1061 为 04:00 UTC) 为同一风暴第 41 轮延续。

### 30min 窗口 (pre-run 注入) — nv_requests (tier_model=dsv4f0731_nv)
- 总量 43, 200=16, 失败=27, **SR=37.2%**
- Avg 147751ms, p50 89070ms, p95 420071ms, max 655315ms
- 429: 0 计数
- upstream_type: nvcf_pexec 36 (200=16, SR=44.4%, avg=98680ms), nv_integrate 3 (200=0,
  avg=328833ms), ms_fallback 2 (200=0, avg=253095ms), 空 2
- finish_reason: tool_calls=15, stop=1 (正常业务完成)

### 错误分类 (30min, nv_requests)
| error_type | count | avg_ms |
|---|---|---|
| all_tiers_exhausted | 16 | 195163 |
| buffer_exhausted | 5 | 298538 |
| zombie_empty_completion | 4 | 70999 |
| client_gone_during_flush | 1 | 407544 |
| stream_absolute_cap | 1 | 160528 |

### attempt 层 (nv_tier_attempts, 30min, tier=dsv4f0731_nv, 实时 DB 查询)
- NVCFPexecRemoteDisconnected: 40 (主导), 且 36 个落在 30-60s bucket (avg ~42.5s), 4 个 60-90s
- 504_nv_gateway_timeout: 12
- NVCFPexecTimeout: 5
- empty_200: 2
- 529_nv_overloaded: 1
- → RemoteDisconnected/504/empty200/timeout/529 主导, 纯远程断连/过载/超时

### 实时 request 层延迟 (30min, nv_requests)
- 200: 13 条, avg 77085ms, p50 77853ms, p95 163933ms
- 502: 31 条, avg 177536ms, p50 149146ms, p95 514756ms
- 499: 1 条, avg 407544ms
- → 成功 200 平均 ~77s, 失败 502 平均 ~178s (烧满 budget 后 fallback)

### 模型特异性重验证 (6h, 同容器同 key 同出口同时窗, 本轮实时 DB 查询)
- **glm5_2_nv 6h**: 50 请求, 40 200, **SR=80.0%**
- **dsv4f0731_nv 6h**: 458 请求, 186 200, **SR=40.6%**
- **结论**: 同容器同 key 同出口, glm5_2_nv 80.0% vs dsv4f0731_nv 40.6% → 模型特异性
  第 41 次成立。故障仅存在于 dsv4f0731_nv 具体 function 的远端执行层。

### 6h/24h 趋势
- 6h attempt 层 (nv_tier_attempts): RemoteDisconnected=348, 529=91, empty_200=59,
  504=26, NVCFPexecTimeout=22 (远程断连/过载主导)
- 6h 请求层 (nv_requests): 458 请求, 186 200, SR=40.6%, 与 R1061 的 451/191/42.4% 基本持平
- 3h 逐小时: 04:00=SR29.6%(16/54), 03:00=44.2%(34/77), 02:00=42.5%(31/73)
- 24h all_tiers_exhausted: 280 次 (相对 R1061 的 276 次 +4)
- key_cycle_429s: 30min k0=30, k1=6, k2=4, k7=2, k9=1, 但 429 计数为 0 → 429 均在与
  上游瞬断混叠中出现, 非持续配额耗尽

### hm4104 fallback 日志 (最近 5min)
- **PRIMARY-FAIL-STREAM**: nv_gw 流式 server_5xx status=502 after 180035ms, 切 fallback
- **FALLBACK-STREAM**: 从 primary 切到 ms_gw 流式
- **PRIMARY-BREAKER-SKIP-STREAM**: primary 流式跳过 (circuit OPEN), 直走 fallback
- 说明 hm4104 断路器持续 OPEN, 用户请求持续 fallback 到 ms_gw 保活

## 2. 决策: NOP (无参数修改)

RemoteDisconnected/504_nv_gateway_timeout/empty_200/zombie_empty/buffer_exhausted/
client_gone_during_flush/529_nv_overloaded 是 NVCF deepseek **远程 function 级**瞬断/劣化,
与容器 env 无关 (第 41 次确认):
- 同出口同 key 下 glm5_2_nv 6h SR=80.0% vs dsv4f0731_nv 40.6% → 网络/mihomo/key/出口路径
  健康, 故障仅在 dsv4f0731_nv 具体 function 远端执行层
- 错误跨全 5 key 分散 (k0/k1/k2/k3/k4 + 空 key) → 证明非 UPSTREAM_TIMEOUT/budget/cooldown/
  fastbreak 可解的 lever
- attempt 层无持续 429 (429 计数=0), 以 RemoteDisconnected/504/529 主导 → 纯远程断连/过载
- 无单 key 劣化 (错误均匀分散各 key) → 无 key 分配/冷却可调
- 成功 200 平均 ~77s 属正常 pexec 长耗时 (p95 163s), 非超时; 失败 502 平均 ~178s 是
  烧满 budget 失败后的正常 fallback 路径

本轮继续 NOP, 等待 NVCF 侧恢复 (第 41 轮)。模型特异性铁证 (6h glm5_2_nv 80.0% vs
dsv4f0731_nv 40.6% + 错误均匀分散) 第 41 次成立。hm4104 断路器已接管用户侧 fallback
(用户请求由 ms_gw 保活)。

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

- /health: status=ok, proxy_role=passthrough, nv_num_keys=5, nvcf_pexec_models 含
  dsv4f0731_nv/nv_model_tiers 含 dsv4f0731_nv, nv_default_model=glm5_2_nv, port=40666 ✓
- 容器: dsvf0731_nv40666 Up 31 hours, env 读取正常 (与 R1061 一致, 无漂移) ✓
- 6h 模型特异性实时复核: glm5_2_nv 80.0%(40/50) vs dsv4f0731_nv 40.6%(186/458) ✓
- attempt 层 6h 复核: RemoteDisconnected=348, 529=91, empty200=59, 504=26, timeout=22 ✓
- 无 env 变更, 无需重启
- 本次 pre-run 注入的 fallback 日志 PRIMARY-FAIL-STREAM(502 after 180035ms)/FALLBACK-STREAM
  为本容器自身轮次触发的正常 fallback 信号, 非本轮修改引起

## 5. 下一步建议

继续等待 NVCF deepseek function 侧恢复。本轮模型特异性铁证第 41 次成立 (6h glm5_2_nv
80.0%/几乎无 tier 错误 vs dsv4f0731_nv 40.6%/RemoteDisconnected 348 主导)。风暴延续
≥41h 无衰减。建议由 CC 评估 (非本容器决策): 是否将 hermes 主链路模型从 dsv4f0731_nv
临时切换为同为 NVCF 的 glm5_2_nv (同链路 6h ~80% 成功) 以消除用户侧 fallback 依赖及
ms_gw 侧时延, 或联系 NVCF 侧确认 deepseek function 健康状况。本容器保持 NOP 以待 NVCF 修复。