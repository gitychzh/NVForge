# HM2 Optimize HM1 — Round R1390

## 1. 触发判定
- cron 脚本输出: "这是我提交的, 不触发" → FALSE TRIGGER
- 最新 commit author = opc2_uname (HM2, R1389)
- HM1 未提交新commit — R1389 是HM2自提
- cron 仍被派遣 — double-dispatch (549th chain of R1133)

## 2. 数据收集 (改前必有数据)
**时间**: 2026-07-15 03:00 UTC
**容器**: nv_gw Up 4 hours (healthy), ms_gw Up 13 hours (healthy), logs_db Up 13 hours (healthy)
**Compose md5**: f493494e2b41b17fbf5d9cff9093648e (unchanged)

### 2.1 6h 总体
| metric | value |
|--------|-------|
| total | 45 |
| OK | 31 |
| fail | 14 |
| SR | 68.9% |

### 2.2 按模型
| model | req | OK | fail | SR | avg_dur | max_dur |
|-------|-----|----|------|-----|---------|---------|
| glm5_2_nv | 34 | 22 | 12 | 64.7% | 8,253ms | 16,567ms |
| dsv4p_nv | 11 | 9 | 2 | 81.8% | 50,470ms | 106,059ms |

### 2.3 错误分类
| error_type | cnt | notes |
|-----------|-----|-------|
| zombie_empty_completion | 12 | all glm5_2_nv integrate, NVCF content-filter stop+8-22 chars, avg 91K-201K input chars, ~4-5s abort |
| all_tiers_exhausted | 2 | all dsv4p_nv pexec, avg 106,049ms, NVCF transient empty_200+timeout, self-recovered |

### 2.4 按路径
| upstream | cnt | OK | fail | avg_dur | avg_ttfb | max_dur |
|----------|-----|----|------|---------|----------|---------|
| nv_integrate | 34 | 22 | 12 | 8,253ms | 8,247ms | 16,567ms |
| nvcf_pexec | 9 | 9 | 0 | 38,119ms | 38,114ms | 93,865ms |
| (null/ATE) | 2 | 0 | 2 | 106,049ms | 792ms | 106,059ms |

### 2.5 Tier attempts
| tier | error_type | cnt |
|------|-----------|---|
| dsv4p_nv | empty_200 | 1 |

### 2.6 Fallback
- fallback_occurred=f: 45/45 (0 fallback)
- ms_gw: ⚠️ DEGRADED — 2 dsv4p_ms fallback attempts both failed with TimeoutError (253s, 254s). relay_started=True but timed out mid-stream. ms_gw is not the optimization target but this is worse than R1389.

### 2.7 Hourly SR
| hour (UTC) | total | ok | fail | SR |
|-----------|-------|----|------|-----|
| 13:00 | 3 | 2 | 1 | 66.7% |
| 14:00 | 5 | 4 | 1 | 80.0% |
| 15:00 | 4 | 3 | 1 | 75.0% |
| 16:00 | 6 | 5 | 1 | 83.3% |
| 17:00 | 4 | 2 | 2 | 50.0% |
| 18:00 | 20 | 12 | 8 | 60.0% |
| 19:00 | 3 | 3 | 0 | 100.0% |

### 2.8 nv_gw 日志 (tail 100, error/warn/zombie)
- NV-ZOMBIE-EMPTY: 6× glm5_2_nv integrate (content_chars=8-22, input_chars=90K-201K, NVCF content-filter finish_reason=stop)
- NV-ZOMBIE-ERROR-CHUNK: 6× sent content_filter error SSE chunk → openclaw fallback trigger
- NV-PEXEC-FASTBREAK: 1× dsv4p_nv (1 consecutive NVCFPexecTimeout → fast-break)
- NV-TIER-FAIL: 1× dsv4p_nv all 5 keys failed (429=0, empty200=1, timeout=1, other=0, elapsed=106050ms)
- NV-MS-FB: 2× dsv4p_ms fallback failed with TimeoutError (253s, 254s)
- No NV-GLOBAL-COOLDOWN, no NV-EMPTY-FASTBREAK (EMPTY_200_FASTBREAK=2 not honored — known R1039 bug)

### 2.9 容器 env (关键参数)
| param | value |
|-------|-------|
| UPSTREAM_TIMEOUT | 66 |
| TIER_COOLDOWN_S | 15 |
| KEY_COOLDOWN_S | 25 |
| NVU_TIER_BUDGET_DSV4P_NV | 106 |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 |
| NVU_PEER_FALLBACK_TIMEOUT | 66 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 195 |
| NVU_EMPTY_200_FASTBREAK | 2 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 |
| NVU_PEER_FB_SKIP_MODELS | (empty) |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 |
| FALLBACK_HEALTH_THRESHOLD | 0.05 |

## 3. 决策
**NOP — 零可修故障。**
- 12 zombie_empty_completion: glm5_2_nv integrate, NVCF content-filter stop (finish_reason=stop, content_chars < 50, input_chars >> 5000). Code-level detection + fast abort (~4-5s). Not config-fixable.
- 2 ATE: dsv4p_nv pexec, NVCF transient empty_200+timeout, self-recovered. Confirmed by 1 tier_attempt empty_200, 9/9 pexec success in same window, avg pexec dur 38s.
- ms_gw degradation: 2 dsv4p_ms fallback attempts both TimeoutError (253s, 254s). Not nv_gw config-fixable — ms_gw is a separate service.
- All params at floor/optimal. Compose md5 f493494e unchanged.
- 铁律: 只改HM1不改HM2.

## 4. 回合链
R1133→R1390: 549th consecutive false-trigger double-dispatch.
HM1 git at R1206 (184 rounds behind, last pull June 2026).
Last HM1-authored commit: 7625e14 (R818, 2026-07-08).
## ⏳ 轮到HM1优化HM2
