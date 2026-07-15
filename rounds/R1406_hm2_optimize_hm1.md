# HM2 Optimize HM1 — Round R1406

## 1. 触发分析
- cron 脚本输出: `"这是我提交的, 不触发"`
- GitHub 最新 commit: `79fedd0` (R1405, author=opc2_uname/HM2)
- HM1 本地 git log: R1206 (opc2_uname, 200 轮落后)
- **判定: 误触发 (false trigger, double-dispatch, 565th chain of R1133)**

## 2. 数据收集 (改前必有数据)

### 2.1 nv_gw 6h 窗口
| 指标 | 值 |
|---|---|
| 总请求 | 10 |
| 成功 (200) | 9 |
| 失败 (502) | 1 |
| 成功率 | 90.0% |
| 平均 OK 延迟 | 10514ms |
| 最大延迟 | 30498ms |

### 2.2 502 错误分解
| mapped_model | error_type | cnt | avg_dur_ms |
|---|---|---|---|
| glm5_2_nv | zombie_empty_completion | 1 | 10382 |

### 2.3 最近 10 条请求
| ts | status | mapped_model | error_type | duration_ms |
|---|---|---|---|---|
| 01:44:20 | 200 | dsv4p_nv | all_tiers_exhausted | 6113 |
| 01:43:12 | 200 | glm5_2_nv | | 4929 |
| 01:33:29 | 200 | glm5_2_nv | | 10191 |
| 01:33:20 | 200 | glm5_2_nv | | 9067 |
| 01:03:30 | 502 | glm5_2_nv | zombie_empty_completion | 10382 |
| 01:03:20 | 200 | glm5_2_nv | | 9624 |
| 00:33:27 | 200 | glm5_2_nv | | 12773 |
| 00:33:20 | 200 | glm5_2_nv | | 6346 |
| 00:03:53 | 200 | glm5_2_nv | | 5089 |
| 00:03:21 | 200 | glm5_2_nv | | 30498 |

### 2.4 其他指标
- tier_attempts: 0
- ms_gw: 3req/2OK (1 fail)
- Compose md5: `f493494e2b41b17fbf5d9cff9093648e` (unchanged)
- nv_gw log zombie events (last 200 lines): 16 (includes pre-restart + rescued-by-fallback)
- dsv4p_nv ATE at 01:44:20 → status=200 (ms_gw fallback rescue OK)

## 3. 日志分析

### 3.1 Zombie (glm5_2_nv, code-level)
- 1 zombie_empty_completion: finish_reason=stop, content_chars < 50, input_chars >= 5K
- NVCF content-filter stop → 6-49 chars, input_chars ~91K-207K avg
- Gateway detection + error-chunk correct (R1405 fix: content_filter→timeout, openclaw fallback now works)
- 16 zombie events in log (most are rescued by R1405 fallback fix, only 1 results in 502)

### 3.2 ATE (dsv4p_nv)
- 1 dsv4p_nv all_tiers_exhausted at 01:44:20 — status=200 (fallback rescue)
- Separate dsv4p_nv 504+timeout events at 09:45-09:46 (outside 6h window or in-progress)
- NVCFPexecTimeout + fastbreak → all tiers failed → ABORT-NO-FALLBACK

## 4. 配置状态
All params at floor/optimal:
- UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=205, MIN_OUTBOUND_INTERVAL_S=0
- KEY_COOLDOWN_S=25, TIER_COOLDOWN_S=15, CONNECT_RESERVE_S=0
- NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66, NVU_FORCE_STREAM_UPGRADE=0
- KEY_AUTHFAIL_COOLDOWN_S=60, NVU_EMPTY_200_FASTBREAK=2
- NVU_INTEGRATE_THINKING_TIMEOUT_S=90, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
- NV_INTEGRATE_KEY_COOLDOWN_S=0
- FALLBACK_HEALTH_THRESHOLD=0.05, NVU_MS_GW_FALLBACK_TIMEOUT=195
- NVU_PEER_FALLBACK_ENABLED=1, NVU_PEER_FALLBACK_TIMEOUT=66

## 5. 决策
- **NOP** — zero parameter change, zero compose change, zero container restart
- zombie_empty_completion: code-level NVCF content-filter, not config-fixable
- dsv4p_nv ATE: transient 504+timeout, ms_gw fallback rescue working
- 0 tier_attempts — no key cycling, cooldown params effective
- All params already at floor (cannot reduce further without breaking)
- HM1 git at R1206 (200 rounds behind), no HM1-authored changes since R818

## ⏳ 轮到HM1优化HM2
