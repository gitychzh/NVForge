# HM2 Optimize HM1 — Round R1099

> **trigger**: false trigger (double-dispatch after R1098 pre-run commit)
> **nv_gw container restarted**: 2026-07-10 13:59 UTC  
> **铁律**: 只改HM1绝不改HM2

## 1. 改前数据

### 6h总体 (nv_gw, 2026-07-10 22:15 UTC query)
| metric | value |
|--------|-------|
| total | 22 |
| OK | 20 (90.9%) |
| fail | 2 |

### 6h错误分类
| error_type | count |
|------------|-------|
| all_tiers_exhausted | 2 |

### 6h按模型
| model | cnt | OK | SR% | avg_dur | avg_ttfb |
|-------|-----|-----|-----|---------|----------|
| glm5_2_nv | 20 | 20 | 100.0% | 20209ms | 20124ms |
| dsv4p_nv | 2 | 0 | 0.0% | 66673ms | 1060ms |

### 6h按上游
| upstream | cnt | OK | avg_dur |
|----------|-----|-----|---------|
| nv_integrate | 19 | 19 | 14645ms |
| (NULL/ATE) | 2 | 0 | 66673ms |
| nvcf_pexec | 1 | 1 | 125917ms |

### 6h tier attempts
| tier | error_type | cnt | avg_ms | max_ms |
|------|-----------|-----|--------|--------|
| glm5_2_nv | IntegrateTimeout | 1 | 90566 | 90566 |

### 24h错误全景
| error_type | cnt |
|------------|-----|
| all_tiers_exhausted | 27 |
| NVStream_TimeoutError | 7 |
| stream_total_deadline | 3 |

### 24h key cycle
| metric | value |
|--------|-------|
| total_req | 543 |
| total_429s | 4 |
| req_with_429s | 4 |
| avg_429s | 0.01 |

### ms_gw (6h)
| total | OK |
|-------|-----|
| 4 | 0 |

### 容器日志（最近100行）
- glm5_2_nv integrate: all first-attempt success, ~4-42s duration
- dsv4p_nv: no traffic in last 100 log lines
- No error/warn/fail patterns

## 2. 当前HM1配置
```
TIER_COOLDOWN_S=18
TIER_TIMEOUT_BUDGET_S=198
UPSTREAM_TIMEOUT=66
KEY_COOLDOWN_S=25
KEY_AUTHFAIL_COOLDOWN_S=60
MIN_OUTBOUND_INTERVAL_S=0
NVU_CONNECT_RESERVE_S=0
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_STREAM_TOTAL_DEADLINE_S=90
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
NVU_TIER_BUDGET_DSV4P_NV=66
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
```

## 3. 分析

- **glm5_2_nv**: 100% SR (20/20), all nv_integrate, first-attempt success. Healthy.
- **dsv4p_nv**: 0% SR (0/2), both ATE single-tier (fallback_occurred=f). NVCF server-side NVStream_TimeoutError / stream_total_deadline. Not a HW/network issue — NVCF pexec timeout.
- **ms_gw**: EMPTY_200_FASTBREAK_THRESHOLD=3 (floor). ms_requests 6h shows 0 OK — likely stream_no_data_lines cycles. No optimization space.
- **All nv_gw params at floor**: TIER_COOLDOWN_S=18, KEY_COOLDOWN_S=25, UPSTREAM_TIMEOUT=66, etc. FALLBACK_HEALTH_THRESHOLD=0.05 (floor).
- **No parameter change justified**: glm5_2_nv is 100% SR, dsv4p_nv failures are NVCF server-side (not configurable), ms_gw at floor.

## 4. 决策: NOP

**参数变更**: 无

**理由**: 所有参数已在地板值。glm5_2_nv 100% SR, dsv4p_nv 2 ATE 均为 NVCF 服务端超时。ms_gw 无优化空间。铁律：只改HM1不改HM2。

## 5. 触发分析
- cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit: b803a3a (R1098 NOP, opc2_uname / HM2)
- HM1 git log: fbf0e43 R821 (277轮落后HM2)
- 判定: **false trigger — double-dispatch after R1098 pre-run commit**
- 预运行脚本已提交 R1098 NOP，符号链接已正确指向 R1098
- 数据与 R1098 一致，无需额外操作

## ⏳ 轮到HM1优化HM2
