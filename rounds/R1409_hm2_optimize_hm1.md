# HM2 Optimize HM1 — Round R1409

## 触发分析
- cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch, 568th chain of R1133)
- HM1 本地 git 停留在 R1206 (203 轮落后)

## 数据收集 (改前必有数据)

### 容器 & Compose
- 容器: nv_gw (running), logs_db (running)
- Compose md5: f493494e2b41b17fbf5d9cff9093648e (unchanged)
- 容器重启后: 2026-07-14T23:43:06Z

### nv_gw 日志 (error/warn)
```
[03:33:32.4] [NV-ZOMBIE-ERROR-CHUNK] (glm5_2_nv) sent finish_reason=content_filter error SSE chunk
[09:03:40.7] [NV-ZOMBIE-ERROR-CHUNK] (glm5_2_nv) sent finish_reason=content_filter error SSE chunk
[10:03:31.5] [NV-ZOMBIE-ERROR-CHUNK] (glm5_2_nv) sent finish_reason=timeout error SSE chunk (R1405 fix active)
[10:11:10.8] [NV-MS-FB] ms_gw relay failed after 198814ms: TimeoutError: timed out
```

### 关键环境变量
| 参数 | 值 |
|------|-----|
| TIER_TIMEOUT_BUDGET_S | 205 |
| UPSTREAM_TIMEOUT | 66 |
| NVU_PEER_FALLBACK_TIMEOUT | 66 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 |
| KEY_COOLDOWN_S | 25 |
| TIER_COOLDOWN_S | 15 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 |
| NVU_EMPTY_200_FASTBREAK | 2 |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 |
| FALLBACK_HEALTH_THRESHOLD | 0.05 |
| MIN_OUTBOUND_INTERVAL_S | 0 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 |
| NVU_CONNECT_RESERVE_S | 0 |
| NV_INTEGRATE_MODELS | glm5_2_nv |
| NVU_FORCE_STREAM_UPGRADE | 0 |

### DB 6h 健康度
- 13 req / 10 OK / 3 fail → 76.9% SR
- avg latency: 10065.5ms (OK requests)
- 0 tier_attempts
- ms_gw: 5 req / 4 OK

### 错误分布 (6h)
| 模型 | 错误类型 | 数量 |
|------|---------|------|
| glm5_2_nv | zombie_empty_completion | 2 |
| dsv4p_nv | all_tiers_exhausted | 1 |

### 最近10条请求
| req_id | created_at | model | status | error_type | dur_ms | upstream | finish_reason |
|--------|-----------|-------|--------|-----------|--------|----------|---------------|
| 026b6418 | 02:11 | dsv4p_nv | 502 | all_tiers_exhausted | 106052 | - | - |
| 464bb4f3 | 02:03 | glm5_2_nv | 502 | zombie_empty_completion | 4866 | nv_integrate | stop |
| dd117b63 | 02:03 | glm5_2_nv | 200 | - | 6025 | nv_integrate | tool_calls |
| 1f3a1436 | 01:46 | dsv4p_nv | 200 | all_tiers_exhausted | 6113 | - | - |
| c12db568 | 01:43 | glm5_2_nv | 200 | - | 4929 | nv_integrate | stop |
| e35d3ef1 | 01:33 | glm5_2_nv | 200 | - | 10191 | nv_integrate | stop |
| 3e2f8fd0 | 01:33 | glm5_2_nv | 200 | - | 9067 | nv_integrate | tool_calls |
| 67479772 | 01:03 | glm5_2_nv | 502 | zombie_empty_completion | 10382 | nv_integrate | stop |
| 8cab6cb5 | 01:03 | glm5_2_nv | 200 | - | 9624 | nv_integrate | tool_calls |
| 8715de90 | 00:33 | glm5_2_nv | 200 | - | 12773 | nv_integrate | stop |

## 分析

### 错误分类
- **2 zombie_empty_completion glm5_2_nv**: NVCF content-filter 信号 (1 content_filter + 1 timeout, R1405 fix 已生效)。Gateway detection+error-chunk 正确。非 config-fixable，上游 NVCF 问题。
- **1 ATE dsv4p_nv**: 504 gateway+timeout，ms_gw relay TimeoutError 198814ms。R1103 BUDGET enforcement gap (TIER_TIMEOUT_BUDGET_S=205 >> UPSTREAM_TIMEOUT=66)。ms_gw rescue 失败 (198s timeout)。非 config-fixable，上游 ms_gw 中继超时。
- **0 tier_attempts**: 调度层无 key 轮转失败。所有错误均为上游不可用。

### 决策
- **NOP**: 所有错误均为非 config-fixable (zombie + ms_gw relay timeout)
- Compose md5 未变，所有参数 floor/optimal
- 0 tier_attempts，无 key 轮转冲突
- 76.9% SR 与 R1408 一致

## 参数: 零变更
铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2
