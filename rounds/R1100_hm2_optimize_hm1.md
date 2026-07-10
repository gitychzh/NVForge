# HM2 Optimize HM1 — Round R1100

> **trigger**: false trigger (double-dispatch after R1099, commit 4ccfe5e already processed as R838)
> **nv_gw container restarted**: 2026-07-10 13:59 UTC  
> **铁律**: 只改HM1绝不改HM2

## 1. 改前数据

### 6h总体 (nv_gw, 2026-07-10 14:52 UTC query)
| metric | value |
|--------|-------|
| total | 19 |
| OK | 18 (94.7%) |
| fail | 1 |

### 6h错误分类
| error_type | count |
|------------|-------|
| all_tiers_exhausted | 1 |

### 6h按模型
| model | cnt | OK | SR% | avg_dur | min_dur | max_dur |
|-------|-----|-----|-----|---------|---------|---------|
| glm5_2_nv | 18 | 18 | 100.0% | 20718ms | 3280ms | 125917ms |
| dsv4p_nv | 1 | 0 | 0.0% | 132017ms | 132017ms | 132017ms |

### 6h按上游
| upstream | cnt | OK | avg_dur |
|----------|-----|-----|---------|
| nv_integrate | 17 | 17 | 14530ms |
| nvcf_pexec | 1 | 1 | 125917ms |
| (NULL/ATE) | 1 | 0 | 132017ms |

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
| total_req | 532 |
| total_429s | 3 |
| req_with_429s | 3 |
| avg_429s | 0.01 |

### ms_gw (6h)
| total | OK |
|-------|-----|
| 2 | 0 |

### peer_fallback (6h)
| count |
|-------|
| 0 |

### 容器日志（最近100行）
- glm5_2_nv integrate: all first-attempt success, 3-42s duration, keys K0-K4 rotating
- No dsv4p_nv traffic in last 100 log lines (post-restart window)
- No error/warn patterns

### 磁盘日志 (nv_proxy.2026-07-10.log)
- dsv4p_nv 14:01:45 ATE 110053ms: timeout=1 other=1, NV-PEXEC-FASTBREAK→1 saved keys, ms_gw BrokenPipeError FAILED
- dsv4p_nv 14:09:31 ATE 110068ms: timeout=1 other=1, same pattern
- dsv4p_nv 17:08:20 ATE 132012ms: timeout=1 other=2, ms_gw FAILED (relay_started=True)
- All three failures: ABORT-NO-FALLBACK → ms_gw attempted → BrokenPipeError → no peer-fb observed

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

- **glm5_2_nv**: 100% SR (18/18), all nv_integrate, first-attempt success across K0-K4 rotation. Healthy.
- **dsv4p_nv**: 1 ATE in 6h window, NVCF server-side timeout cycling all 5 keys. PEXEC_TIMEOUT_FASTBREAK=1 works (early abort after 1 timeout), but still ~110-132s elapsed — NVCF pexec timeout is function-level, not config-fixable.
- **ms_gw**: 2 req, 0 OK — BrokenPipeError pattern (relay_started=True). Same unfixable code-level issue as previous rounds. Not a config-fixable path.
- **peer_fb**: 0 uses in 6h. dsv4p_nv eligible (not in PEER_FB_SKIP_MODELS) but peer-fb not observed after ms_gw BrokenPipeError — ms_gw corrupts the stream before peer-fb can fire. Code-level issue, not config-fixable.
- **All nv_gw params at floor**: TIER_COOLDOWN_S=18, KEY_COOLDOWN_S=25, UPSTREAM_TIMEOUT=66, FASTBREAKs=1/1/2, etc. FALLBACK_HEALTH_THRESHOLD=0.05 (floor).
- **No parameter change justified**: glm5_2_nv is 100% SR; dsv4p_nv failures are NVCF server-side; ms_gw at floor; peer-fb path blocked by code-level ordering.

## 4. 决策: NOP

**参数变更**: 无

**理由**: 所有参数已在地板值。glm5_2_nv 100% SR。dsv4p_nv ATE 均为 NVCF 服务端超时+ms_gw BrokenPipeError，属 code-level 问题 (peer-fb 在 ms_gw 流式中断后未触发)。ms_gw 无配置优化空间。铁律：只改HM1不改HM2。

## 5. 触发分析
- cron 脚本输出: "已处理过此commit(4ccfe5e37185a608ee3aa403911b9c419aa5e35a), 等待新提交"
- 4ccfe5e = R838 (opc_uname / HM1 commit, 2026-07-08)
- R838 已由 HM2 R838 轮处理 (NOP)
- HM1 本地 git log: fbf0e43 R821 (279轮落后HM2)
- HM2 最新: R1099_hm2_optimize_hm1.md (NOP)
- 判定: **false trigger — R838 commit already processed, double-dispatch after R1099**
- 数据与 R1098/R1099 一致，无需额外操作

## ⏳ 轮到HM1优化HM2
