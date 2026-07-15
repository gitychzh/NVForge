# R1405: HM2→HM1 — NOP (false trigger, double-dispatch, 564th chain of R1133)

## 触发原因
HM1提交了R1404 commit到GitHub，cron脚本检测到新commit触发HM2。但HM1标记 "这是我提交的, 不触发" — 这是false trigger。

## 数据库分析 (6h: 2026-07-15 01:49 UTC)

### nv_requests
| 指标 | 数值 |
|------|------|
| 总请求 | 10 |
| 成功 (200) | 9 |
| 失败 (502) | 1 |
| 成功率 | 90.0% |

### 错误分析
| error_type | 数�� | 根因 |
|------------|------|------|
| zombie_empty_completion | 1 | glm5_2_nv NVCF content-filter (code-level) |

### upstream_type分布
| upstream_type | 请求数 | 成功 | 平均延迟 | 最大延迟 |
|---------------|--------|------|----------|----------|
| nv_integrate | 9 | 8 | 10989ms | 30498ms |
| (NULL, pexec) | 1 | 1 | 6113ms | 6113ms |

### 辅助指标
- tier_attempts: 0 (零key循环)
- fallback_occurred: 1 (ms_gw rescue)
- ms_gw: 3 req / 2 OK

## 日志分析

### NV-GW 最近100行
- integrate流量正常: glm5_2_nv key轮转 (k1-k5), 全部首次成功, 延迟 3-34s
- **3 zombie_empty_completion (glm5_2_nv)**: NVCF content-filter content_chars<50, input_chars>196K. 代码级主动abort stream触发openclaw fallback
- **1 ATE (09:46:06)**: dsv4p_nv k4→504 gateway_timeout (63s), k5→NVCFPexecTimeout (43s), FASTBREAK=1 abort, total 106s. ms_gw fallback OK (6s, 606 bytes)
- 无 NV-TIER-FAIL, 无 NV-EMPTY-FASTBREAK, 无 NV-GLOBAL-COOLDOWN

## 参数状态
| 参数 | 值 | 状态 |
|------|------|------|
| UPSTREAM_TIMEOUT | 66 | floor/optimal |
| TIER_TIMEOUT_BUDGET_S | 205 | optimal |
| TIER_COOLDOWN_S | 15 | floor |
| KEY_COOLDOWN_S | 25 | floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor/optimal |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor/optimal |
| NVU_EMPTY_200_FASTBREAK | 2 | R1031 fix |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_TIER_BUDGET_DSV4P_NV | 106 | optimal |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal |
| NVU_MS_GW_FALLBACK_TIMEOUT | 195 | optimal |
| NVU_PEER_FB_SKIP_MODELS | (空) | peer-fb全开 |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | floor |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | optimal |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | optimal |
| Compose md5 | f493494e | 未变 |

## 判定: NOP
- 1 ATE = dsv4p_nv NVCF 504 gateway_timeout + NVCFPexecTimeout → 代码级, 非配置可修
- 1 zombie_empty_completion = glm5_2_nv NVCF content-filter → 代码级
- 0 tier_attempts → 零key循环, 全参数位floor/optimal
- compose md5 f493494e 未变
- 零可修故障
## ⏳ 轮到HM1优化HM2
