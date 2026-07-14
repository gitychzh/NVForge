# HM2 Optimize HM1 — Round R1356

## 1. 角色
- 执行者: HM2 (opc2_uname)
- 优化对象: HM1 (opc_uname@100.109.153.83)
- 铁律: 只改HM1不改HM2 | 改前必有数据 | 改后必有验证

## 2. 触发分析
cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2)
- 预运行脚本已提交 R1355 (NOP)，symlink 已指向 R1355
- cron 仍被派遣 — 双重派遣 (double-dispatch)，516th chain of R1133
- HM1 git log 落后: 最新为 R1206 (de04120, 150 rounds behind)
- 确认: 误触发 (false trigger)

## 3. 数据收集 (6h 窗口, 2026-07-14 ~20:05 UTC)

### 3.1 nv_gw 总体
| 指标 | 值 |
|------|-----|
| Total | 62 |
| OK (200) | 51 |
| Fail (≠200) | 11 |
| SR | 82.3% |

### 3.2 错误分类
| error_type | cnt | avg_dur_ms |
|---|---|---|
| zombie_empty_completion | 7 | 10,150 |
| all_tiers_exhausted | 4 | 71,529 |

### 3.3 按模型/路径
| mapped_model | cnt | ok | fail | avg_dur_ms |
|---|---|---|---|---|
| glm5_2_nv | 27 | 20 | 7 | 12,571 |
| dsv4p_nv | 26 | 22 | 4 | 30,228 |

| upstream_type | cnt | ok | avg_ttfb | avg_dur |
|---|---|---|---|---|
| nv_integrate | 27 | 20 | 12,568 | 12,571 |
| nvcf_pexec | 25 | 25 | 21,925 | 21,931 |
| (null=ATE) | 4 | 0 | 858 | 71,529 |

### 3.4 dsv4p_nv ATE 详情
4 ATEs 全部 PRE-RESTART (06:22-06:37 UTC, container restart at 11:29 UTC):
- tiers_tried_count=1, fallback_actually_attempted=false
- error_subcategory=all_tiers_failed_in_mapped_tier
- duration 70,035-72,032ms
- nv_key_idx=NULL (no cycling recorded in nv_requests)

Post-restart: 0 dsv4p_nv traffic → 0 failures.

### 3.5 zombie_empty_completion 详情
7 zombies (glm5_2_nv integrate, NVCF content-filter stop + 2chars):
- duration 4,762-21,809ms
- input_chars 184,478-190,234
- Code-level zombie detection → fast abort (RST+SO_LINGER)
- Log: "[NV-ZOMBIE-EMPTY] ... [NV-ZOMBIE-ABORT]"

### 3.6 fallback / tier_attempts
- fallback_occurred: 61 false, 0 true (no fallback triggered in window)
- tier_attempts (6h): 0 (零 key cycling 错误)
- FALLBACK_GRAPH: {} (空, R832 设计, ms_gw same-model fallback)

### 3.7 ms_gw
| 指标 | 6h |
|------|-----|
| Total | 4 |
| OK | 4 |
| Fail | 0 |
| SR | 100% |

### 3.8 容器状态
- nv_gw: Up 42 minutes (healthy), restarted 2026-07-14T11:29:07Z
- compose md5: b367c647a8d42d9d86ed8814234a1d19

### 3.9 实时参数 (docker exec nv_gw env)
| 参数 | 值 | 判定 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | floor |
| TIER_COOLDOWN_S | 15 | floor |
| KEY_COOLDOWN_S | 25 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_FORCE_STREAM_UPGRADE | 0 | off (floor) |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | matched |
| NVU_EMPTY_200_FASTBREAK | 2 | optimal |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | optimal |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | optimal |
| NVU_TIER_BUDGET_DSV4P_NV | 94 | optimal (R1000) |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal |
| TIER_TIMEOUT_BUDGET_S | 205 | safe (>>94+66) |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | optimal |
| NVU_PEER_FB_SKIP_MODELS | "" | all models enabled |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | matched |
| NVU_MS_GW_FALLBACK_TIMEOUT | 195 | safe |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | floor |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | optimal |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | optimal |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | optimal |

## 4. 决策

### 4.1 NOP 判定
所有参数 floor/optimal。可修故障=0:
- zombie_empty_completion (7×): code-level (NVCF content-filter), not config-fixable
- dsv4p_nv ATE (4×): ALL pre-restart (06:22-06:37 UTC, container restarted 11:29 UTC)
- Post-restart: 5 glm5_2_nv (4 OK, 1 zombie), 0 dsv4p_nv traffic, 0 failures
- 0 tier_attempts: 零 key cycling 错误
- 0 fallback triggers: ms_gw never needed (only pre-restart ATEs would have triggered)
- ms_gw: 4/4 OK 100% SR
- R1000 NVU_TIER_BUDGET_DSV4P_NV 82→94 still settling (R1355 same observation)

### 4.2 ms_gw 检查
- ms_gw 4/4 OK 100% SR, all params default/optimal
- 无需优化

### 4.3 决策: NOP (零可修故障)
Zero param, zero compose change, zero container restart.

## 5. 数据-vs-R1355 对比
R1355 报告: 83req/70OK 84.3%SR, 7 zombie, 6 ATE all PRE-RESTART
R1356 数据: 62req/51OK 82.3%SR, 7 zombie, 4 ATE all PRE-RESTART
→ 数据一致 (pre-restart ATE 数量因窗口时段略微不同, post-restart 均 0 dsv4p_nv 流量)
→ 确认 NOP: 系统未变, 无新故障类型

## ⏳ 轮到HM1优化HM2