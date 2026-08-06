# R1061: RemoteDisconnected 风暴延续 (第40轮) — 模型特异性第40次复现, NOP (无参数修改)

> 时间: 2026-08-06 12:00 BJT (04:00 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF)
> 状态: **NOP (无参数修改)** — NVCFPexecRemoteDisconnected 远程瞬断风暴在 attempt 层
>   持续主导, 第 40 次复现**模型特异性** (同容器同 key 同出口 glm5_2_nv 6h SR=88.0%
>   且 0 tier 错误, dsv4f0731_nv 6h SR=42.4% + attempt 层 RemoteDisconnected/504 主导) →
>   NVCF deepseek function 级劣化, 无本容器可解参数
> 信号: hm4104 fallback 持续 (PRIMARY-FAIL-STREAM 502 → FALLBACK-STREAM → ms_gw)

## 1. 背景 (改前必有数据)

R1021-R1060 连续记录同一 RemoteDisconnected 风暴并判定模型特异性 NOP。本轮间隔 ~1h
(R1060 为 02:54 UTC) 为同一风暴第 40 轮延续。

### 30min 窗口 (pre-run 注入) — nv_requests (tier_model=dsv4f0731_nv)
- 总量 37, 200=20, 失败=17, **SR=54.1%**
- Avg 114572ms, p50 87402ms, p95 254642ms, max 303651ms
- 429: 0 计数
- upstream_type: nvcf_pexec 30 (200=20, SR=66.7%, avg=83627ms), ms_fallback 6 (200=0,
  avg=248245ms), nv_integrate 1 (200=0, avg=240864ms)
- finish_reason: tool_calls=18, stop=2 (正常业务完成)

### 错误分类 (30min, nv_requests)
| error_type | count | avg_ms |
|---|---|---|
| buffer_exhausted | 7 | 247191 |
| all_tiers_exhausted | 6 | 123441 |
| zombie_empty_completion | 3 | 36957 |
| client_gone_during_flush | 1 | 199268 |

### attempt 层 (nv_tier_attempts, 30min, tier=dsv4f0731_nv, 实时 DB 查询)
- NVCFPexecRemoteDisconnected: 30 (主导)
- 504_nv_gateway_timeout: 7
- empty_200: 6
- NVCFPexecTimeout: 4
- 529_nv_overloaded: 2
- → RemoteDisconnected/504/empty200/timeout 主导, 纯远程断连/过载/超时

### 模型特异性重验证 (6h, 同容器同 key 同出口同时窗, 本轮实时 DB 查询)
- **glm5_2_nv 6h**: 75 请求, 66 200, **SR=88.0%**, avg=67248ms
- **dsv4f0731_nv 6h**: 451 请求, 191 200, **SR=42.4%**, avg=114619ms
- **结论**: 同容器同 key 同出口, glm5_2_nv 88.0% vs dsv4f0731_nv 42.4% → 模型特异性
  第 40 次成立。故障仅存在于 dsv4f0731_nv 具体 function 的远端执行层。

### 6h/24h 趋势
- 6h 请求层 (nv_requests): 451 请求, 191 200, SR=42.4%, 与 R1060 的 423/187/44.2% 基本持平
- 3h 逐小时: 03:00=SR42.9%(27/63), 02:00=41.7%(30/72), 01:00=33.8%(22/65), 00:00=23.1%(3/13)
- 24h all_tiers_exhausted: 276 次 (相对 R1060 的 239 次 +37)
- key_cycle_429s: 30min k0=21, k1=11, k2=3, k3=1, k7=1, 但 429 计数为 0 → 429 均在与
  上游瞬断混叠中出现, 非持续配额耗尽

### hm4104 fallback 日志 (最近 5min)
- **PRIMARY-FAIL-STREAM**: nv_gw 流式 server_5xx status=502 after 164734ms, 切 fallback
- **FALLBACK-STREAM**: 从 primary 切到 ms_gw 流式
- **PRIMARY-BREAKER-SKIP-STREAM**: primary 流式跳过 (circuit OPEN), 直走 fallback
- 说明 hm4104 断路器持续 OPEN, 用户请求持续 fallback 到 ms_gw 保活

## 2. 决策: NOP (无参数修改)

RemoteDisconnected/504_nv_gateway_timeout/empty_200/zombie_empty/buffer_exhausted/
client_gone_during_flush 是 NVCF deepseek **远程 function 级**瞬断/劣化, 与容器 env 无关
(第 40 次确认):
- 同出口同 key 下 glm5_2_nv 6h SR=88.0% + 0 tier 错误 → 网络/mihomo/key/出口路径全部健康
- 故障仅存在于 dsv4f0731_nv 具体 function 的远端执行层
- 错误跨全 5 key 分散 (k0/k2/k3/k4 + 空 key) → 证明非 UPSTREAM_TIMEOUT/budget/cooldown/
  fastbreak 可解的 lever
- attempt 层无持续 429, 无 SSL 错误 (RemoteDisconnected/504/empty_200 主导) → 纯远程断连/过载
- 无单 key 劣化 (错误均匀分散各 key) → 无 key 分配/冷却可调

本轮继续 NOP, 等待 NVCF 侧恢复 (第 40 轮)。模型特异性铁证 (6h glm5_2_nv 88.0% +
0 tier 错误 vs dsv4f0731_nv 42.4% + 错误均匀分散) 第 40 次成立。hm4104 断路器
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

- /health: status=ok, proxy_role=passthrough, nv_num_keys=5, nvcf_pexec_models 含
  dsv4f0731_nv/nv_model_tiers 含 dsv4f0731_nv, nv_default_model=glm5_2_nv, port=40666 ✓
- 容器: dsvf0731_nv40666 Up 30 hours, env 读取正常 (与 R1060 一致, 无漂移) ✓
- 6h 模型特异性实时复核: glm5_2_nv 88.0%(66/75) vs dsv4f0731_nv 42.4%(191/451) ✓
- attempt 层 30min 复核: RemoteDisconnected=30, 504=7, empty200=6, timeout=4, 529=2 ✓
- 无 env 变更, 无需重启
- 本次 pre-run 注入的 fallback 日志 PRIMARY-FAIL-STREAM(502 after 164734ms)/FALLBACK-STREAM
  为本容器自身轮次触发的正常 fallback 信号, 非本轮修改引起

## 5. 下一步建议

继续等待 NVCF deepseek function 侧恢复。本轮模型特异性铁证第 40 次成立 (6h glm5_2_nv
88.0%/0 tier 错误 vs dsv4f0731_nv 42.4%/错误均匀分散)。风暴延续 ≥40h 无衰减。
建议由 CC 评估 (非本容器决策): 是否将 hermes 主链路模型从 dsv4f0731_nv 临时切换为同为
NVCF 的 glm5_2_nv (同链路 6h ~88% 成功) 以消除用户侧 fallback 依赖及 ms_gw 侧时延,
或联系 NVCF 侧确认 deepseek function 健康状况。本容器保持 NOP 以待 NVCF 修复。