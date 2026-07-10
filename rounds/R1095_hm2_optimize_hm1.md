# HM2 Optimize HM1 — Round R1095

## 1. 触发分析
cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2, R1094)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — double-dispatch false trigger
- 此轮为 NOP

## 2. 数据收集（改前必有数据）

### 容器状态
- nv_gw StartedAt: 2026-07-10T12:09:57Z (~1h ago)
- ms_gw: Up 17 hours (healthy)
- logs_db: Up 6 days

### 24h 窗口 (2026-07-09 13:00 → 2026-07-10 13:00 UTC)
| 指标 | 值 |
|------|----|
| 总请求 | 600 |
| 成功 | 563 (93.8%) |
| 失败 | 37 (6.2%) |

### 按模型
| 模型 | 请求 | OK | 失败 | SR% | avg_dur | p95 | max_succ |
|------|------|----|------|-----|---------|-----|----------|
| glm5_2_nv | 392 | 377 | 15 | 96.2% | 21,541ms | — | 208,108ms |
| dsv4p_nv | 101 | 88 | 13 | 87.1% | 21,932ms | 53,493ms | 59,548ms |
| kimi_nv | 62 | 61 | 1 | 98.4% | 11,531ms | — | 71,985ms |
| minimax_m3_nv | 45 | 37 | 8 | 82.2% | 39,093ms | 67,871ms | 93,363ms |

### 按路径
| 路径 | 请求 | OK | 失败 | avg_ttfb | avg_dur |
|------|------|----|------|----------|---------|
| nv_integrate | 410 | 400 | 10 | 15,149ms | 18,804ms |
| nvcf_pexec | 151 | 151 | 0 | 15,274ms | 15,283ms |
| ATE (NULL) | 39 | 12 | 27 | 354ms | 79,901ms |

### 错误分类
| 错误类型 | 数量 | 备注 |
|----------|------|------|
| all_tiers_exhausted | 27 | 全部 pre-restart |
| NVStream_TimeoutError | 7 | 全部 glm5_2_nv, 91-106s, 全部 pre-restart |
| stream_total_deadline | 3 | 2 glm5_2_nv + 1 minimax |

### dsv4p_nv ATE 详情
| 时间 | 耗时 | tiers_tried | fallback |
|------|------|------------|----------|
| 09:06 UTC | 132,017ms | 1 | f |
| 08:20 UTC | 1,328ms | 1 | f |
| 06:07 UTC | 110,073ms | 1 | f |
| 05:59 UTC | 110,058ms | 1 | f |
| 其余 9 次 | ~60-61s cluster | 1 | f |

- 60-61s cluster: NVU_TIER_BUDGET_DSV4P_NV=66 — budget hit, ~5-6s headroom
- 110s cluster: 可能是 dual-tier (dsv4p + peer/ms_gw)
- **全部 pre-restart** — 重启后 dsv4p_nv 零流量

### minimax_m3_nv ATE 详情
| 时间 | 耗时 | 路径 |
|------|------|------|
| 19:31 UTC | 50,505ms | nv_integrate (stream_total_deadline) |
| 其余 7 次 | ~151-159s | NULL (ATE) |

- NVU_TIER_BUDGET_MINIMAX_M3_NV=100 但 ATE duration ~151-159s → 多 tier 尝试
- **全部 pre-restart** — 重启后 minimax 零流量

### NVStream_TimeoutError
- 7 次全部 glm5_2_nv integrate, duration 91-106s
- NVU_STREAM_TOTAL_DEADLINE_S=90 — deadline 绑定 (91-106s 含检查间隔)
- **全部 pre-restart** (最新: 08:16 UTC, 重启前 ~4h)

### Post-Restart 数据 (12:09 UTC → 现在)
| 请求 | 模型 | 路径 | 状态 | 耗时 |
|------|------|------|------|------|
| 5 条 | glm5_2_nv | nv_integrate | 全部 200 | 3.6-33.8s |

- **Post-restart: 5/5 OK (100%)**
- dsv4p_nv: **零流量** (R1088 BUDGET=198 完全未测试)
- kimi_nv: 零流量
- minimax_m3_nv: 零流量

### nv_tier_attempts (仅失败尝试)
| tier | error_type | cnt | avg_ms | max_ms |
|------|------------|-----|--------|--------|
| dsv4p_nv | NVCFPexecRemoteDisconnected | 1 | 9,134ms | 9,134ms |
| glm5_2_nv | IntegrateRemoteDisconnected | 1 | 20,284ms | 20,284ms |
| glm5_2_nv | IntegrateTimeout | 1 | 90,566ms | 90,566ms |
| kimi_nv | empty_200 | 1 | — | — |
| minimax_m3_nv | IntegrateTimeout | 1 | 90,762ms | 90,762ms |

- 仅 5 条 tier attempts → 大部分失败在调度层即被拒绝 (zero attempts logged)
- Minimax IntegrateTimeout 90,762ms ≈ NVU_INTEGRATE_THINKING_TIMEOUT_S=90 — 绑定

### ms_gw 状态
- ms_requests 24h: 39 total, 0 OK
- 模式: MS-OK-STREAM → MS-STREAM-CLIENT-EOF BrokenPipeError (已知流同步缺陷)
- dsv4p_ms: 仍为 disabled placeholder

### Fallback 触发
- fallback_occurred=true: 8 次 (全部 glm5_2_nv ATE → ms_gw)
- 8 次 fallback 全部命中 ms_gw (MODELMAP glm5_2_nv:glm5_2_ms)
- 0 次 peer-fallback 触发

### 当前 HM1 env 参数 (已验证)
| 参数 | 值 | 来源 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | R988 |
| TIER_TIMEOUT_BUDGET_S | 198 | R1088 |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | R1078 |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | R835 |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | R1035 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | R997 |
| NVU_EMPTY_200_FASTBREAK | 2 | R1031 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | R1010 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 | R1088 |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2:glm5_2_ms,kimi:kimi_ms,dsv4p:dsv4p_ms | R1033 |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | R1039 |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | R697 |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.10 | R818 |
| NVU_STREAM_TOTAL_DEADLINE_S | 90 | R1038 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | R988 |
| KEY_COOLDOWN_S | 25 | 长期 |
| TIER_COOLDOWN_S | 18 | R1018 |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | 对称 |
| NVU_FORCE_STREAM_UPGRADE | 0 | 禁用 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NV_INTEGRATE_MODELS | glm5_2_nv,minimax_m3_nv | R578 |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | — |

## 3. 决策

**NOP — 零参数修改**

理由:
1. **False trigger**: cron 脚本明确标记 "不触发"，HM2 自提交不应触发 HM2 优化 HM1
2. **Post-restart dsv4p_nv 零流量**: R1088 的 BUDGET=198 regime 完全未测试 (dsv4p_nv, kimi_nv, minimax 重启后均为零流量)
3. **Post-restart: 5/5 OK (100%)** — 但仅 glm5_2_nv integrate 有流量，不足以评估 regime
4. **所有 37 失败均为 pre-restart** — 无 post-restart 失败可分析
5. **nvcf_pexec 100% SR (151/151)** — pexec 路径完美，无调整需求
6. **NVStream_TimeoutError 全部 pre-restart** — 重启后零 NVStream 错误，可能 NVCF function 已恢复
7. **全部参数已在优化位**: 所有 floor 参数已达 floor，所有 budget 参数已适度宽松
8. **ms_gw BrokenPipeError**: 已知流同步缺陷，非配置可修复

铁律: 只改 HM1 不改 HM2。

## ⏳ 轮到HM1优化HM2