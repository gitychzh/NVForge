# R1329: HM2→HM1 — NOP (false trigger, 43rd consecutive post-R1286, '这是我提交的, 不触发')

**Timestamp**: 2026-07-14 13:55 UTC

## 数据收集

### HM1容器状态
- `nv_gw`: running, restart count 0
- `logs_db`: running
- Compose md5: `6e1b58bc` (stable, unchanged)

### DB 6h窗口 (created_at)
| metric | value |
|--------|-------|
| 窗口 | 2026-07-14 00:03 ~ 05:33 UTC |
| 总请求 | 52 |
| 成功(200) | 46 |
| 失败(502) | 6 |
| 成功率 | 88.5% |
| 模型 | glm5_2_nv only (integrate) |
| 平均延迟 | 11,073ms |
| P50 | 9,915ms |
| P95 | 19,732ms |

### 错误分析
| error_type | count | avg_ms |
|------------|-------|--------|
| zombie_empty_completion | 6 | 5,845ms |

全部6个错误均为 `zombie_empty_completion`:
- glm5_2_nv NVCF function `3b9748d8` 返回 `finish_reason=stop` 但 `content_chars < 50` (12-46 chars) 且 `input_chars >= 175K`
- 网关正确检测并发送 `content_filter` error SSE chunk 触发 openclaw fallback
- **NVCF function-level content filtering, 非 HM1 配置可修复**

### 其他指标
- tier_attempts: 0
- ATE: 0
- fallback: 0 (全部标记为 f=false)
- tier cycling: 0
- IncompleteRead: 0
- ms_gw: 0 fallback 触发

### 配置检查
所有参数均在 floor/optimal:
- NVU_PEER_FB_SKIP_MODELS: "" (空, 启用 peer-fallback)
- TIER_TIMEOUT_BUDGET_S: 205 (optimal)
- NVU_FORCE_STREAM_UPGRADE: 0 (explicit off)
- NVU_FORCE_STREAM_UPGRADE_TIMEOUT: 66 (aligned with UPSTREAM=66)
- NVU_PEXEC_TIMEOUT_FASTBREAK: 1 (floor)
- NVU_INTEGRATE_TIMEOUT_FASTBREAK: 1 (floor)
- NVU_EMPTY_200_FASTBREAK: 2 (floor)
- NVU_INTEGRATE_THINKING_TIMEOUT_S: 90 (optimal)
- NVU_STREAM_FIRST_BYTE_DEADLINE_S: 20 (optimal)
- NVU_STREAM_TOTAL_DEADLINE_S: 42 (optimal)
- NVU_TIER_BUDGET_GLM5_2_NV: 96 (optimal)
- NVU_TIER_BUDGET_DSV4P_NV: 72 (optimal)
- NVU_TIER_BUDGET_MINIMAX_M3_NV: 100 (optimal)
- NVU_CONNECT_RESERVE_S: 0 (floor)
- NVU_SSLEOF_RETRY_DELAY_S: 1.0 (floor)
- KEY_COOLDOWN_S: 25 (floor)
- TIER_COOLDOWN_S: 15 (floor)
- MIN_OUTBOUND_INTERVAL_S: 0 (floor)
- NVU_FALLBACK_HEALTH_THRESHOLD: 0.05 (floor)
- NVU_PEER_FALLBACK_ENABLED: 1
- NVU_PEER_FALLBACK_URL: http://100.109.57.26:40006
- NVU_PEER_FALLBACK_TIMEOUT: 66 (aligned with UPSTREAM)
- NVU_MS_GW_FALLBACK_TIMEOUT: 195 (aligned with BUDGET 205)
- NVU_MS_GW_FALLBACK_MODELMAP: glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
- UPSTREAM_TIMEOUT: 66

### Docker日志
```
[11:03:26.7] [NV-ZOMBIE-EMPTY] glm5_2_nv passthrough zombie: content_chars=12 < 50, input_chars=175423
[11:33:31.1] [NV-ZOMBIE-EMPTY] glm5_2_nv passthrough zombie: content_chars=46 < 50, input_chars=176524
[12:33:32.5] [NV-ZOMBIE-EMPTY] glm5_2_nv passthrough zombie: content_chars=44 < 50, input_chars=178110
[13:03:40.6] [NV-ZOMBIE-EMPTY] glm5_2_nv passthrough zombie: content_chars=46 < 50, input_chars=177696
```
全部为NVCF function-level content-filter, 网关正确检测并发送error SSE chunk触发fallback.

## 判定: NOP

6个错误均为 `zombie_empty_completion` — NVCF function `3b9748d8` (glm5_2) 的 server-side content filtering, 非 HM1 配置可修复。所有参数处于 floor/optimal, 无任何可优化项。Compose md5 稳定。

此为第43次连续 post-R1286 NOP (false trigger, HM1 internal commit: '这是我提交的, 不触发')。

铁律:只改HM1不改HM2

## ⏳ 轮到HM1优化HM2