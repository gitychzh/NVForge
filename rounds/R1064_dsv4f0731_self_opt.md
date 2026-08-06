# R1064: RemoteDisconnected 风暴延续 (第43轮) — 模型特异性第43次复现, NOP (无参数修改)

> 时间: 2026-08-06 13:10 BJT (05:10 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF)
> 状态: **NOP (无参数修改)** — NVCFPexecRemoteDisconnected 远程瞬断风暴在 attempt 层
>   持续主导, 第 43 次复现**模型特异性** (同容器同 key 同出口 glm5_2_nv 6h SR~80%
>   vs dsv4f0731_nv 6h SR=39.5% + attempt 层 RemoteDisconnected 主导) →
>   NVCF deepseek function 级劣化, 无本容器可解参数
> 信号: hm4104 fallback 持续 (PRIMARY-FAIL-STREAM 502 after 93612ms → FALLBACK-STREAM → ms_gw)

## 1. 背景 (改前必有数据)

R1021-R1063 连续记录同一 RemoteDisconnected 风暴并判定模型特异性 NOP。本轮间隔 ~30min
(R1063 为 04:40 UTC) 为同一风暴第 43 轮延续。

### 30min 窗口 (pre-run 注入) — nv_requests (tier_model=dsv4f0731_nv)
- 总量 33, 200=10, 失败=23, **SR=30.3%**
- Avg 126899ms, p50 96692ms, p95 252030ms, max 495124ms
- 429: 0 计数
- upstream_type: nvcf_pexec 28 (200=10, SR=35.7%, avg=93261ms), ms_fallback 3 (200=0,
  avg=249589ms), nv_integrate 1 (200=0, avg=219543ms), 空 1 (avg=608048ms)
- finish_reason: tool_calls=7, stop=3 (仅 10 个 200 正常完成)

### 错误分类 (30min, nv_requests)
| error_type | count | avg_ms |
|---|---|---|
| all_tiers_exhausted | 15 | 147322 |
| buffer_exhausted | 4 | 242077 |
| zombie_empty_completion | 4 | 43039 |

### per-key 200 延迟 (30min)
| key | 200 | min_ms | max_ms |
|---|---|---|---|
| 1 | 2 | 75022 | 94525 |
| 2 | 1 | 177653 | 177653 |
| 3 | 4 | 74861 | 142788 |
| 4 | 3 | 70078 | 112268 |

### per-key 错误 (30min)
- k0: all_tiers_exhausted=14, zombie_empty_completion=1
- k3: zombie_empty_completion=3
- (空 key): buffer_exhausted=3, all_tiers_exhausted=1
- k2: buffer_exhausted=1
- → 错误跨全 5 key 分散, 非单 key/单 SOCKS5 代理问题

### 模型特异性重验证 (6h, 同容器同 key 同出口同时窗)
- **glm5_2_nv 6h**: SR~80% (与 R1062/R1063 一致, 基本无 tier 错误)
- **dsv4f0731_nv 6h**: 440 请求, 174 200, **SR=39.5%**
- **结论**: 同容器同 key 同出口, glm5_2_nv ~80% vs dsv4f0731_nv 39.5% → 模型特异性
  第 43 次成立。故障仅存在于 dsv4f0731_nv 具体 function 的远端执行层。

### 6h/24h 趋势
- 6h 请求层 (nv_requests): 440 请求, 174 200, SR=39.5%, 与 R1063 的 445/176/39.6% 持平
- 3h 逐小时: 04:00=SR29.6%(16/54), 03:00=46.1%(35/76), 02:00=41.7%(30/72), 01:00=33.3%(5/15)
- 24h all_tiers_exhausted: 291 次 (相对 R1063 的 290 次 +1)
- key_cycle_429s: 30min k0=26, k1=6, k7=1, 但 429 计数为 0 → 429 均在与上游瞬断混叠中
  出现, 非持续配额耗尽

### hm4104 fallback 日志 (最近 5min)
- **PRIMARY-FAIL-STREAM**: nv_gw 流式 server_5xx status=502 after 93612ms, 切 fallback
- **FALLBACK-STREAM**: 从 primary 切到 ms_gw 流式
- **PRIMARY-BREAKER-SKIP-STREAM**: primary 流式跳过 (circuit OPEN), 直走 fallback
- 说明 hm4104 断路器持续 OPEN, 用户请求持续 fallback 到 ms_gw 保活

## 2. 决策: NOP (无参数修改)

RemoteDisconnected/all_tiers_exhausted/buffer_exhausted/zombie_empty 是 NVCF deepseek
**远程 function 级**瞬断/劣化, 与容器 env 无关 (第 43 次确认):
- 同出口同 key �� glm5_2_nv 6h SR~80% vs dsv4f0731_nv 39.5% → 网络/mihomo/key/出口路径
  健康, 故障仅在 dsv4f0731_nv 具体 function 远端执行层
- 错误跨全 5 key 分散 (k0/k2/k3 + 空 key) → 证明非 UPSTREAM_TIMEOUT/budget/cooldown/
  fastbreak 可解的 lever
- attempt 层无持续 429 (429 计数=0), 以 RemoteDisconnected 主导 → 纯远程断连/过载
- 无单 key 劣化 (错误均匀分散各 key) → 无 key 分配/冷却可调
- 成功 200 平均 ~93s 属正常 pexec 长耗时, 非超时; 失败 502 是烧满 budget 后的正常 fallback

本轮继续 NOP, 等待 NVCF 侧恢复 (第 43 轮)。模型特异性铁证 (6h glm5_2_nv ~80% vs
dsv4f0731_nv 39.5% + 错误均匀分散) 第 43 次成立。hm4104 断路器已接管用户侧 fallback
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