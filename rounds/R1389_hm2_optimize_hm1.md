# HM2 Optimize HM1 — Round R1389

## 1. 触发判定
- cron 脚本输出: "这是我提交的, 不触发" → FALSE TRIGGER
- 最新 commit author = opc2_uname (HM2, R1388)
- HM1 最新 commit: 5c4e5b3 (R1388, HM2-authored)
- cron 仍被派遣 — double-dispatch (548th chain of R1133)

## 2. 数据收集 (改前必有数据)
**时间**: 2026-07-14 18:00 UTC
**容器**: nv_gw Up 3 hours (healthy), started 2026-07-14T15:25:43Z
**Compose md5**: f493494e2b41b17fbf5d9cff9093648e (unchanged)

### 2.1 6h 总体
| metric | value |
|--------|-------|
| total | 45 |
| OK | 30 |
| fail | 15 |
| SR | 66.7% |

### 2.2 按模型
| model | req | OK | fail | SR | avg_dur |
|-------|-----|----|------|-----|---------|
| glm5_2_nv | 34 | 21 | 13 | 61.8% | 8,759ms |
| dsv4p_nv | 11 | 9 | 2 | 81.8% | 50,470ms |

### 2.3 错误分类
| error_type | cnt | notes |
|-----------|-----|-------|
| zombie_empty_completion | 13 | all glm5_2_nv integrate, NVCF content-filter stop+8-18 chars, avg 164K input chars, ~8s abort |
| all_tiers_exhausted | 2 | all dsv4p_nv pexec, avg 106,049ms, NVCF transient empty_200+timeout, self-recovered |

### 2.4 按路径
| upstream | cnt | OK | fail | avg_dur |
|----------|-----|----|------|---------|
| nv_integrate | 34 | 21 | 13 | 8,759ms |
| nvcf_pexec | 9 | 9 | 0 | 38,119ms |
| (null/ATE) | 2 | 0 | 2 | 106,049ms |

### 2.5 Tier attempts
| tier | error_type | cnt | 
|------|-----------|---|
| dsv4p_nv | empty_200 | 1 |

### 2.6 Fallback
- fallback_occurred=f: 45/45 (0 fallback)
- ms_gw: 3req/3OK (standby healthy)

### 2.7 Hourly SR
| hour (UTC) | total | ok | fail | SR |
|-----------|-------|----|------|-----|
| 13:00 | 6 | 4 | 2 | 66.7% |
| 14:00 | 5 | 4 | 1 | 80.0% |
| 15:00 | 4 | 3 | 1 | 75.0% |
| 16:00 | 6 | 5 | 1 | 83.3% |
| 17:00 | 4 | 2 | 2 | 50.0% |
| 18:00 | 20 | 12 | 8 | 60.0% |

### 2.8 nv_gw 日志 (tail 100, error/warn/zombie)
- NV-ZOMBIE-EMPTY: 5× glm5_2_nv integrate (content_chars=8-18, input_chars=90K-201K, NVCF content-filter finish_reason=stop)
- NV-ZOMBIE-ERROR-CHUNK: 5× sent content_filter error SSE chunk → openclaw fallback trigger
- tier_chain=['glm5_2_nv'] (no fallback, 3model) — expected R832 state
- tier_chain=['dsv4p_nv'] (no fallback, 3model) — expected R832 state
- No NV-TIER-FAIL, no NV-GLOBAL-COOLDOWN, no NV-MS-FB, no NV-EMPTY-FASTBREAK

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
- 13 zombie_empty_completion: glm5_2_nv integrate, NVCF content-filter stop (finish_reason=stop, content_chars < 50, input_chars >> 5000). Code-level detection + fast abort (8s). Not config-fixable.
- 2 ATE: dsv4p_nv pexec, NVCF transient empty_200+timeout, self-recovered. Confirmed by 1 tier_attempt empty_200, 9/9 pexec success in same window, avg pexec dur 38s.
- All params at floor/optimal. Compose md5 f493494e unchanged.
- 铁律: 只改HM1不改HM2.

## 4. 回合链
R1133→R1389: 548th consecutive false-trigger double-dispatch.
HM1 git at R1206 (183 rounds behind, last pull June 2026).
Last HM1-authored commit: 7625e14 (R818, 2026-07-08).
## ⏳ 轮到HM1优化HM2
