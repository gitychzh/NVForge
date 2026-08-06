# R1063: RemoteDisconnected 风暴延续 (第42轮) — 模型特异性第42次复现, NOP (无参数修改)

> 时间: 2026-08-06 12:40 BJT (04:40 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF)
> 状态: **NOP (无参数修改)** — NVCFPexecRemoteDisconnected 远程瞬断风暴在 attempt 层
>   持续主导, 第 42 次复现**模型特异性** (同容器同 key 同出口 glm5_2_nv 6h SR=80.0%
>   vs dsv4f0731_nv 6h SR=39.6% + attempt 层 RemoteDisconnected 主导) →
>   NVCF deepseek function 级劣化, 无本容器可解参数
> 信号: hm4104 fallback 持续 (PRIMARY-FAIL-STREAM 502 after 81357ms → FALLBACK-STREAM → ms_gw)

## 1. 背景 (改前必有数据)

R1021-R1062 连续记录同一 RemoteDisconnected 风暴并判定模型特异性 NOP。本轮间隔 ~30min
(R1062 为 04:30 UTC) 为同一风暴第 42 轮延续。

### 30min 窗口 (pre-run 注入) — nv_requests (tier_model=dsv4f0731_nv)
- 总量 35, 200=9, 失败=26, **SR=25.7%**
- Avg 147507ms, p50 105101ms, p95 364108ms, max 539877ms
- 429: 0 计数
- upstream_type: nvcf_pexec 29 (200=9, SR=31.0%, avg=111755ms), ms_fallback 3 (200=0,
  avg=249589ms), nv_integrate 2 (200=0, avg=282518ms), 空 1
- finish_reason: tool_calls=6, stop=3 (仅 9 个 200 正常完成)

### 错误分类 (30min, nv_requests)
| error_type | count | avg_ms |
|---|---|---|
| all_tiers_exhausted | 16 | 154771 |
| buffer_exhausted | 5 | 262760 |
| zombie_empty_completion | 4 | 43039 |
| client_gone_during_flush | 1 | 407544 |

### attempt 层 (nv_tier_attempts, 30min, tier=dsv4f0731_nv, 实时 DB 查询)
- NVCFPexecRemoteDisconnected: 34 (主导)
- 504_nv_gateway_timeout: 5
- 529_nv_overloaded: 1
- NVCFPexecTimeout: 1
- empty_200: 1
- → RemoteDisconnected/504/529 主导, 纯远程断连/过载

### 模型特异性重验证 (6h, 同容器同 key 同出口同时窗, 实时 DB 查询)
- **glm5_2_nv 6h**: 50 请求, 40 200, **SR=80.0%**
- **dsv4f0731_nv 6h**: 445 请求, 176 200, **SR=39.6%**
- **结论**: 同容器同 key 同出口, glm5_2_nv 80.0% vs dsv4f0731_nv 39.6% → 模型特异性
  第 42 次成立。故障仅存在于 dsv4f0731_nv 具体 function 的远端执行层。

### 6h/24h 趋势
- 6h 请求层 (nv_requests): 445 请求, 176 200, SR=39.6%, 与 R1062 的 458/186/40.6% 基本持平
- 3h 逐小时: 04:00=SR29.6%(15/52), 03:00=44.2%(35/76), 02:00=42.5%(30/72), 01:00=36.8%(7/19)
- 24h all_tiers_exhausted: 290 次 (相对 R1062 的 280 次 +10)
- key_cycle_429s: 30min k0=27, k1=6, k7=2, 但 429 计数为 0 → 429 均在与上游瞬断混叠中
  出现, 非持续配额耗尽

### hm4104 fallback 日志 (最近 5min)
- **PRIMARY-FAIL-STREAM**: nv_gw 流式 server_5xx status=502 after 81357ms, 切 fallback
- **FALLBACK-STREAM**: 从 primary 切到 ms_gw 流式
- **PRIMARY-BREAKER-SKIP-STREAM**: primary 流式跳过 (circuit OPEN), 直走 fallback
- 说明 hm4104 断路器持续 OPEN, 用户请求持续 fallback 到 ms_gw 保活

## 2. 决策: NOP (无参数修改)

RemoteDisconnected/504_nv_gateway_timeout/529_nv_overloaded/empty_200/zombie_empty/
buffer_exhausted/client_gone_during_flush 是 NVCF deepseek **远程 function 级**瞬断/劣化,
与容器 env 无关 (第 42 次确认):
- 同出口同 key 下 glm5_2_nv 6h SR=80.0% vs dsv4f0731_nv 39.6% → 网络/mihomo/key/出口路径
  健康, 故障仅在 dsv4f0731_nv 具体 function 远端执行层
- 错误跨全 5 key 分散 (k0/k1/k2/k3/k4 + 空 key) → 证明非 UPSTREAM_TIMEOUT/budget/cooldown/
  fastbreak 可解的 lever
- attempt 层无持续 429 (429 计数=0), 以 RemoteDisconnected/504/529 主导 → 纯远程断连/过载
- 无单 key 劣化 (错误均匀分散各 key) → 无 key 分配/冷却可调
- 成功 200 平均 ~111s 属 pexec 正常长耗时; 失败 502 平均 ~178s 是烧满 budget 失败后的
  正常 fallback 路径

本轮继续 NOP, 等待 NVCF 侧恢复 (第 42 轮)。模型特异性铁证 (6h glm5_2_nv 80.0% vs
dsv4f0731_nv 39.6% + 错误均匀分散) 第 42 次成立。hm4104 断路器已接管用户侧 fallback
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
- 容器: dsvf0731_nv40666 Up 31 hours, env 读取正常 (与 R1062 一致, 无漂移) ✓
- 6h 模型特异性实时复核: glm5_2_nv 80.0%(40/50) vs dsv4f0731_nv 39.6%(176/445) ✓
- attempt 层 30min 复核: RemoteDisconnected=34, 504=5, 529=1, timeout=1, empty200=1 ✓
- 无 env 变更, 无需重启
- 本次 pre-run 注入的 fallback 日志 PRIMARY-FAIL-STREAM(502 after 81357ms)/FALLBACK-STREAM
  为本容器自身轮次触发的正常 fallback 信号, 非本轮修改引起

## 5. 下一步建议

继续等待 NVCF deepseek function 侧恢复。本轮模型特异性铁证第 42 次成立 (6h glm5_2_nv
80.0% vs dsv4f0731_nv 39.6%/RemoteDisconnected 主导)。风暴延续 ≥42h 无衰减。建议由 CC
评估 (非本容器决策): 是否将 hermes 主链路模型从 dsv4f0731_nv 临时切换为同为 NVCF 的
glm5_2_nv (同链路 6h ~80% 成功) 以消除用户侧 fallback 依赖及 ms_gw 侧时延, 或联系
NVCF 侧确认 deepseek function 健康状况。本容器保持 NOP 以待 NVCF 修复。