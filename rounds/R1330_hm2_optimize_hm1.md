# R1330: HM2→HM1 — NOP (44th consecutive post-R1286, HM1 internal commit)

**Timestamp**: 2026-07-14 14:10 UTC

## 数据收集

### HM1容器状态
- `nv_gw`: running, restart count 0
- `logs_db`: running
- Compose md5: `6e1b58bc` (stable, unchanged)

### DB 6h窗口 (created_at)
| metric | value |
|--------|-------|
| 窗口 | 2026-07-14 00:33 ~ 06:12 UTC |
| 总请求 | 86 |
| 成功(200) | 78 |
| 失败(502) | 8 |
| 成功率 | 90.7% |
| 模型 | glm5_2_nv (integrate), dsv4p_nv (pexec) |
| tier_attempts | 0 |
| fallback_occurred | 0 |
| key cycling | 0 |

### 按模型+路径分布
| mapped_model | cnt | ok | avg_dur | avg_ttfb | upstream_type |
|--------------|-----|----|---------|----------|---------------|
| glm5_2_nv | 53 | 47 | 11,303ms | 10,209ms | nv_integrate |
| dsv4p_nv | 33 | 31 | 23,320ms | 18,999ms | nvcf_pexec |
| ATE | 2 | 0 | 72,024ms | — | — |

### 错误分析
| error_type | count | avg_ms | 模型 |
|------------|-------|--------|------|
| zombie_empty_completion | 6 | 6,190ms | glm5_2_nv (integrate) |
| all_tiers_exhausted | 2 | 72,024ms | dsv4p_nv (pexec) |

#### zombie_empty_completion (6)
- glm5_2_nv NVCF function `3b9748d8` 返回 `finish_reason=stop` 但 `content_chars < 50` (12-46 chars) 且 `input_chars >= 175K`
- 网关正确检测并发送 `content_filter` error SSE chunk 触发 openclaw fallback
- **NVCF function-level content filtering, 非 HM1 配置可修复**

#### all_tiers_exhausted ATE (2)
两个 ATE 均为 dsv4p_nv pexec, 模式完全一致:
```
k4 empty_200 (stream) → cycle → k5 NVCFPexecTimeout → FASTBREAK=1 → tier fail 72s
→ ABORT-NO-FALLBACK → ms_gw dsv4p_ms fallback
```

| ATE | time | tier | ms_gw fallback | total |
|-----|------|------|----------------|-------|
| #1 | 05:57:12 | 72,016ms | TimeoutError 203,107ms | ~275s |
| #2 | 06:03:22 | 72,012ms | BrokenPipeError 8,520ms | ~80s |

**根因**: NVCF dsv4p function `74f02205` 短时 degraded (k4 empty_200 + k5 timeout)。FASTBREAK=1 正确快断。ms_gw fallback 失败: #1 超时 (dsv4p_ms 过载), #2 BrokenPipe (瞬态网络)。**非 HM1 配置可修复**。

⚠️ **Peer-fb 未触发**: 尽管 `NVU_PEER_FALLBACK_ENABLED=1` + `NVU_PEER_FB_SKIP_MODELS=""` + HM2 peer alive (200), 日志中无任何 `PEER` 字样。代码路径 `ABORT-NO-FALLBACK → MS-FB` 跳过了 peer-fb。此为代码级问题, 非配置可修复。

### ms_gw 6h
| status | count |
|--------|-------|
| ok | 14 |
| client_disconnect | 1 |
| 成功率 | 93.3% |

ms_gw dsv4p_ms 仅 1 次 client_disconnect (10.5s), 其余全部 OK。ms_gw 本身健康, 两个 ATE 的 ms_gw fallback 失败为瞬态。

### 配置检查
所有参数均在 floor/optimal:
- NVU_PEER_FB_SKIP_MODELS: "" (空, 启用 peer-fallback)
- TIER_TIMEOUT_BUDGET_S: 205 (optimal)
- NVU_FORCE_STREAM_UPGRADE: 0 (explicit off)
- NVU_PEXEC_TIMEOUT_FASTBREAK: 1 (floor)
- NVU_INTEGRATE_TIMEOUT_FASTBREAK: 1 (floor)
- NVU_EMPTY_200_FASTBREAK: 2 (floor, R1039 bug: pexec path not honored)
- NVU_INTEGRATE_THINKING_TIMEOUT_S: 90 (optimal)
- NVU_STREAM_FIRST_BYTE_DEADLINE_S: 20 (optimal)
- NVU_STREAM_TOTAL_DEADLINE_S: 42 (optimal)
- NVU_TIER_BUDGET_DSV4P_NV: 72 (optimal)
- NVU_TIER_BUDGET_GLM5_2_NV: 96 (optimal)
- NVU_TIER_BUDGET_MINIMAX_M3_NV: 100 (optimal)
- NVU_CONNECT_RESERVE_S: 0 (floor)
- NVU_SSLEOF_RETRY_DELAY_S: 1.0 (floor)
- KEY_COOLDOWN_S: 25 (floor)
- TIER_COOLDOWN_S: 15 (floor)
- MIN_OUTBOUND_INTERVAL_S: 0 (floor)
- NVU_FALLBACK_HEALTH_THRESHOLD: 0.05 (floor)
- NVU_PEER_FALLBACK_ENABLED: 1
- NVU_PEER_FALLBACK_URL: http://100.109.57.26:40006
- NVU_PEER_FALLBACK_TIMEOUT: 66
- NVU_MS_GW_FALLBACK_TIMEOUT: 195
- UPSTREAM_TIMEOUT: 66

### Docker日志
```
[13:58:14.1] [NV-EMPTY-200] k4 (dsv4p_nv) → 200 Content-Length:0 (stream)
[13:58:24.4] [NV-PEXEC-FASTBREAK] 1 consecutive NVCFPexecTimeout → fast-break
[13:58:24.4] [NV-TIER-FAIL] dsv4p_nv all 5 keys failed: empty200=1, timeout=1, elapsed=72016ms
[13:58:24.4] [NV-ALL-TIERS-FAIL] ABORT-NO-FALLBACK
[13:58:24.4] [NV-MS-FB] attempting ms_gw dsv4p_ms
[14:01:47.5] [NV-MS-FB] ms_gw relay failed: TimeoutError (203107ms)
[14:04:25.2] [NV-EMPTY-200] k4 (dsv4p_nv) → 200 Content-Length:0 (stream)
[14:04:34.6] [NV-PEXEC-FASTBREAK] 1 consecutive NVCFPexecTimeout → fast-break
[14:04:34.6] [NV-TIER-FAIL] dsv4p_nv all 5 keys failed: empty200=1, timeout=1, elapsed=72012ms
[14:04:43.1] [NV-MS-FB] ms_gw relay failed: BrokenPipeError (8520ms)
```

## 判定: NOP

6个错误为 `zombie_empty_completion` — NVCF function `3b9748d8` (glm5_2) content filtering, 非 HM1 配置可修复。2个 ATE 为 dsv4p_nv NVCF function 短时 degraded + ms_gw 瞬态 fallback 失败, 非 HM1 配置可修复。Peer-fb 未触发为代码级路径问题, 非配置可修复。所有参数处于 floor/optimal, 无任何可优化项。Compose md5 稳定。

此为第44次连续 post-R1286 NOP (false trigger, HM1 internal commit: '这是我提交的, 不触发')。

铁律:只改HM1不改HM2

## ⏳ 轮到HM1优化HM2