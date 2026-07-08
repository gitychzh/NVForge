# HM2 Optimize HM1 — Round R929

**时间**: 2026-07-09 06:12 UTC  
**角色**: HM2 → HM1 优化执行者  
**触发**: cron 检测 HM1 新 commit (R928 自提交 + symlink fix)，但脚本误判为自提交

## 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`  
- 脚本检测到最新 commit author = opc2_uname (HM2)  
- 实际触发 commit 是 R928 的 cleanup (remove stale RN_hm2_optimize_hm1.md)  
- cron 仍被派遣 — double-dispatch 模式 (R928 已处理)

## HM1 数据收集 (改前必有数据)

### nv_gw 配置
| 参数 | 值 |
|---|---|
| UPSTREAM_TIMEOUT | 64 |
| TIER_TIMEOUT_BUDGET_S | 114 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 |
| MIN_OUTBOUND_INTERVAL_S | 0 |
| KEY_COOLDOWN_S | 25 |
| TIER_COOLDOWN_S | 25 |
| NVU_CONNECT_RESERVE_S | 0 |
| NVU_EMPTY_200_FASTBREAK | 3 |
| NVU_FORCE_STREAM_UPGRADE | 0 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 |
| KEY_AUTHFAIL_COOLDOWN_S | 60 |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv,dsv4p_nv |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 |

### nv_gw 6h 统计
| 指标 | 值 |
|---|---|
| 总请求 | 61 |
| 成功 (200) | 61 (100.0%) |
| 失败 | 0 |
| ATE (502) | 0 |
| errors/warns (logs) | 0 |

### nv_gw 24h 统计
| 指标 | 值 |
|---|---|
| 总请求 | 191 |
| 成功 (200) | 190 |
| 失败 | 1 |
| ATE (502) | 1 (0.52%) |

### 24h 按模型分布
| 模型 | 请求数 | 成功率 | 平均延迟 |
|---|---|---|---|
| glm5_2_nv | 183 | 99.5% | 17,999ms |
| dsv4p_nv | 6 | 100% | 42,255ms |
| (null) | 2 | 100% | 0ms |

### nv_gw 最近 10 请求
全部 `glm5_2_nv` → 200 OK，duration 2764-15016ms，均首次尝试成功。最新请求: 2026-07-09 06:04 UTC。

### 容器日志 (最近 200 行)
全部 `[NV-SUCCESS]` + `succeeded on first attempt`，无 error/warn。所有请求来自 openclaw，key 轮转正常 (k1-k5)。

### 24h ATE 详情
- 时间: 2026-07-08 13:21 UTC
- 模型: glm5_2_nv
- duration: 121,075ms
- fallback_occurred: false
- fallback_actually_attempted: false
- tiers_tried_count: 2
- nv_tier_attempts: 0 条记录（无失败尝试日志）
- 特征: fallback 未触发，两个 glm5_2_nv tier 直接耗尽 → FALLBACK_GRAPH 瞬时消失 (R710 已知问题)

### nv_tier_attempts (6h)
| tier | error_type | cnt | avg_ms |
|---|---|---|---|
| dsv4p_nv | NVCFPexecTimeout | 1 | 52,849 |
| dsv4p_nv | empty_200 | 1 | - |

### ms_gw 6h 统计
- 0 请求，零流量。

## 决策

**NOP — 全参数在地板，无可优化项。**

理由:
1. **零错误**: 6h 内 61/61 100% SR，零 ATE，零 error/warn
2. **全参数地板**: 所有可调参数已在地板值 (UPSTREAM_TIMEOUT=64, TIER_TIMEOUT_BUDGET_S=114, FASTBREAK=1, EMPTY_200_FASTBREAK=3, KEY_COOLDOWN_S=25, TIER_COOLDOWN_S=25)
3. **24h 单次 ATE**: 0.52% 失败率，为 FALLBACK_GRAPH 瞬时消失 (已知问题，非配置问题)，距今 17h+
4. **ms_gw**: 零流量，同在地板
5. **容器日志**: 完全干净，所有请求首次尝试成功

HM1 当前的瓶颈不是配置 — 参数已无可降空间。openclaw 持续使用 glm5_2_nv，hermes 和 opencode 的 agent 在 HM1 上未触发 (106 轮落后于 HM2 的 agent 活跃度)。

## ⏳ 轮到HM1优化HM2