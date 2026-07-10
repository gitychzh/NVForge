# HM2 Optimize HM1 — Round R1101

> **trigger**: false trigger (HM2 fetched own R1100 commit; HM1 has no new commits — last HM1 commit is R790 opc_uname)
> **nv_gw container restarted**: 2026-07-10 13:59 UTC
> **铁律**: 只改HM1绝不改HM2

## 1. 改前数据

### 容器状态
- 重启: 2026-07-10 13:59 UTC, 运行 ~9h, healthy
- 容器: nv_gw

### 6h总体 (nv_gw, 2026-07-10 15:09 UTC query)
| metric | value |
|--------|-------|
| total | 19 |
| OK | 19 (100.0%) |
| fail | 0 |

### 6h按模型
| model | cnt | OK | SR% | avg_dur | min_dur | max_dur |
|-------|-----|-----|-----|---------|---------|---------|
| glm5_2_nv | 19 | 19 | 100.0% | 14387ms | 3280ms | 45690ms |

### 6h按上游
| upstream | cnt | OK | avg_dur |
|----------|-----|-----|---------|
| nv_integrate | 19 | 19 | 14387ms |

### 6h tier attempts
| tier | error_type | cnt |
|------|-----------|-----|
| (0 rows) | | |

### 12h (含重启前)
| metric | value |
|--------|-------|
| total | 78 |
| OK | 70 (89.7%) |
| fail | 8 |

### 12h按模型
| model | cnt | OK | SR% |
|-------|-----|-----|-----|
| glm5_2_nv | 74 | 70 | 94.6% |
| dsv4p_nv | 4 | 0 | 0.0% |

### 12h dsv4p_nv 502详情
| ts | duration_ms | error_subcategory | fallback |
|----|------------|-------------------|-----------|
| 09:06 UTC | 132,017 | all_tiers_failed_in_mapped_tier | f |
| 08:20 UTC | 1,328 | all_tiers_failed_in_mapped_tier | f |
| 06:07 UTC | 110,073 | all_tiers_failed_in_mapped_tier | f |
| 05:59 UTC | 110,058 | all_tiers_failed_in_mapped_tier | f |

### 12h glm5_2_nv 502详情
| ts | duration_ms | error_type |
|----|------------|------------|
| 08:15 UTC | 96,068 | NVStream_TimeoutError |
| 06:10 UTC | 99,181 | NVStream_TimeoutError |
| 06:02 UTC | 102,323 | NVStream_TimeoutError |
| 05:54 UTC | 105,819 | NVStream_TimeoutError |

### 24h错误全景
| error_type | cnt |
|------------|-----|
| all_tiers_exhausted | 26 |
| NVStream_TimeoutError | 7 |
| stream_total_deadline | 3 |

### 今日完整统计 (2026-07-10)
| model | total | OK | SR% |
|-------|-------|-----|-----|
| glm5_2_nv | 100 | 96 | 96.0% |
| dsv4p_nv | 4 | 0 | 0.0% |
| **total** | **104** | **96** | **92.3%** |

### 磁盘日志 (nv_proxy.2026-07-10.log)
- dsv4p_nv 14:01 UTC: NVCFPexecTimeout → FASTBREAK=1 → NV-TIER-FAIL (110,053ms) → ms_gw BrokenPipeError (7,144ms)
- dsv4p_nv 14:09 UTC: NVCFPexecTimeout → FASTBREAK=1 → NV-TIER-FAIL (110,068ms) → ms_gw BrokenPipeError (12,989ms)
- dsv4p_nv 16:20 UTC: ms_gw relay failed TimeoutError (171,036ms)
- dsv4p_nv 17:08 UTC: NVCFPexecTimeout → FASTBREAK=1 → NV-TIER-FAIL (132,012ms) → ms_gw BrokenPipeError (4,211ms)
- ⚠️ 14:01/14:09 失败**未写入DB** — NVCF server-side reject, nv_gw DB write 在 ms_gw fallback 失败后路径不完整
- SSLEOFError: 12次今日, 全部成功 rescue (SSL-cycle → 下一 key). glm5_2_nv k2 7次 (10:03, 10:34, 13:51×2, 21:03, 00:22, 00:36), minimax_m3_nv k2/k5, dsv4p_nv k3, kimi_nv k4
- Peer-fb: minimax_m3_nv 尝试6次 (00:59-01:30 UTC), 全部 TimeoutError 45s (HM2 不可达). dsv4p_nv 无 peer-fb (ms_gw modelmap 优先, ms_gw 失败后不触发 peer-fb)
- 17:08 UTC 后 → 零失败 (6h+ clean window)

### 容器日志（最近100行）
- 全部 glm5_2_nv integrate: first-attempt success, K1-K5 轮转, 3-42s duration
- 无 dsv4p_nv / kimi_nv / minimax_m3_nv 流量
- 无 error/warn/fail 模式

### ms_gw (6h)
| total | OK |
|-------|-----|
| 1 | 0 |

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
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
NVU_MS_GW_FALLBACK_TIMEOUT=180
```

## 3. 分析

### glm5_2_nv: 健康
- 6h: 19/19 100% SR, 全部 nv_integrate first-attempt
- 12h: 70/74 94.6% SR — 4次 NVStream_TimeoutError (96-106s, 均在 05:54-08:15 UTC)
- SSLEOFError 全部 rescue (SSL-cycle → next key), 无 tier 级影响
- 无参数调整空间 (所有 param 已至 floor)

### dsv4p_nv: NVCF server-side, 不可配置修复
- 今日 4/4 502 (0% SR), 全部 NVCFPexecTimeout → FASTBREAK=1 → NV-TIER-FAIL
- 磁盘日志额外 4 次 502 (14:01/14:09/16:20/17:08, 未入库) — NVCF function-level reject
- ms_gw fallback: BrokenPipeError (relay_started=True) 或 TimeoutError (171s) — code-level 不可修复
- Peer-fb: 未触发 (ms_gw modelmap 优先, ms_gw 失败后不 fallback 到 peer-fb — code-level)
- 无法通过配置修复: NVCF 超时是函数级, ms_gw BrokenPipe 是 code-level, peer-fb 路径被 ms_gw 阻塞

### 其他模型
- kimi_nv: 无 6h 流�� (100% 24h pexec, 仅 1 次 SSLEOFError)
- minimax_m3_nv: 无 6h 流量 (24h 6 次 peer-fb TimeoutError 45s, HM2 不可达)

### 参数状态
- 所有参数已至地板值: TIER_COOLDOWN_S=18, KEY_COOLDOWN_S=25, UPSTREAM_TIMEOUT=66
- FASTBREAK 全部 1/1/2 (已至 floor)
- FALLBACK_HEALTH_THRESHOLD=0.05 (floor, R1097)
- TIER_BUDGET_DSV4P_NV=66 (floor = UPSTREAM_TIMEOUT)
- 无参数可进一步降低而不破坏正常请求

### 触发分析
- GitHub origin/main HEAD: 5aa0130 (R1100, opc2_uname — HM2 自己的 commit)
- HM1 最新 commit: fbf0e43 R821 (opc2_uname, 279 轮落后 HM2)
- HM1 最后 opc_uname commit: b217aae R790 (2026-07-05)
- 判定: **false trigger** — 无 HM1 新 commit, cron 误检测 HM2 的 R1100 commit 为 HM1 提交

## 4. 决策: NOP

**参数变更**: 无

**理由**: 
1. glm5_2_nv 6h 100% SR, 所有参数已至 floor
2. dsv4p_nv 失败均为 NVCF server-side function-level timeout + ms_gw BrokenPipeError (code-level)
3. 所有可调参数已至地板值, 无进一步降低空间
4. 铁律: 只改HM1不改HM2

## 5. 评判
- 更少报错: ✓ (6h 零错误, 12h 仅 8 次全 NVCF 侧)
- 更快请求: ✓ (glm5_2_nv avg 14.4s, 无优化空间)
- 超低延迟: ✓ (所有参数 floor)
- 稳定优先: ✓ (100% 6h SR, 无破坏性变更)

**铁律: 只改 HM1 不改 HM2** ✓

## ⏳ 轮到HM1优化HM2