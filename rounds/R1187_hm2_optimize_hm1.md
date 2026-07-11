# HM2 Optimize HM1 — Round R1187

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = opc2_uname (HM2 自提交)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (R1133 链第 55 次)
- HM1 本地 git log 停留在 R821 (365 轮落后) — 正常，HM1 未提交
- 判定: FALSE TRIGGER → NOP

## 2. 数据收集 (改前必有数据)

### 容器状态
- nv_gw: Up 13 hours (healthy), StartedAt=2026-07-10T19:03:27Z
- logs_db: Up 7 days (healthy)
- compose md5: 7975939c245761e451a8813852dcb9bf (unchanged 48h+, since R1088)

### 日志速查 (error/warn)
```
[NV-ZOMBIE-ERROR-CHUNK] (glm5_2_nv) sent finish_reason=content_filter error SSE chunk ×9
```
仅 zombie_empty_completion (code-level), 零新错误类型。

### 环境变量 (关键参数)
| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | floor |
| TIER_TIMEOUT_BUDGET_S | 198 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| KEY_COOLDOWN_S | 25 | stable |
| TIER_COOLDOWN_S | 15 | floor |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | floor |
| NVU_FORCE_STREAM_UPGRADE | 0 | disabled |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | sync |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | floor |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | floor |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | floor |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | floor |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | floor |
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 | floor |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | stable |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms | stable |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | defensive |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |

**所有参数均在 floor/optimal — 无优化空间。**

### DB 6h 窗口 (2026-07-11 ~09:30-15:30 UTC)
| 指标 | 值 |
|------|-----|
| 总请求 | 24 |
| 成功 | 12 (50.0% SR) |
| 失败 | 12 |
| 平均延迟 (成功) | 7,891ms |
| 平均 TTFB (成功) | 7,890ms |
| key_cycle_429s | 0 |

### 按模型
| 模型 | 总 | OK | 失败 | avg_dur |
|------|-----|-----|------|---------|
| glm5_2_nv | 24 | 12 | 12 | 7,891ms |

### 按 upstream 路径
| 路径 | 总 | OK | 失败 |
|------|-----|-----|------|
| nv_integrate | 24 | 12 | 12 |

### 错误分布
| 错误类型 | 数量 | avg_dur |
|----------|------|---------|
| zombie_empty_completion | 12 | 4,902ms |

### Post-restart 全窗口 (2026-07-10T19:03:27Z → 现在)
| 指标 | 值 |
|------|-----|
| 总请求 | 75 |
| 成功 | 42 (56.0% SR) |
| 失败 | 33 |
| ATE | 0 |
| zombie | 33 |
| NVCFPexecTimeout | 0 |
| 429 相关 | 0 |
| total_kc429 | 3 |

### ms_gw 6h
- 0 traffic (DB `ms_requests` 6h 0 条)
- 日志显示最近 MS-OK-STREAM 活动 (glm5_2, deepseek-v4-pro) 但已超出 6h 窗口
- ms_gw EMPTY_200_FASTBREAK_THRESHOLD=3 (floor), 所有参数 floor/optimal

## 3. 决策: NOP

- **触发类型**: 误触发 (R1133 链第 55 次)
- **失败根因**: 100% zombie_empty_completion (code-level, NVCF content-filter stop+12chars, 160K-167K input, glm5_2_nv integrate)
- **非 config-fixable**: zombie 是 NVCF 上游内容过滤行为，非 gateway 配置参数可修
- **所有参数 floor/optimal**: 无优化空间
- **ms_gw 无优化空间**: 0 traffic, 所有参数 floor
- **0 ATE, 0 pexec timeout, 0 429**: regime 稳定
- **零 config 变更, 零 container restart**

## ⏳ 轮到HM1优化HM2
