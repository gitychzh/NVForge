# HM2 Optimize HM1 — Round R1122

> **铁律**: 只改HM1不改HM2

## 1. 触发分析

cron 预运行脚本输出: `"这是我提交的, 不触发"` — **FALSE TRIGGER**。

R1121 已由 pre-run 脚本提交 (NOP)。R1122 为 double-dispatch: cron 对同一 false trigger 再次派遣 agent。HM1 本地 git log 仍停留在 R821 (~301 rounds behind) — 正常。

## 2. 数据收集

### 2.1 Container 状态

- Container: `nv_gw` (port 40006)
- 启动时间: `2026-07-10T19:03:27Z` (~9h ago)
- 后重启窗口: ~9h

### 2.2 6h 总体统计

| 指标 | 值 |
|------|-----|
| Total | 140 |
| OK (200) | 126 |
| Fail (non-200) | 14 |
| SR | 90.0% |

### 2.3 Post-Restart (19:03 UTC→now, ~9h)

| 指标 | 值 |
|------|-----|
| Total | 8 |
| OK | 8 |
| SR | **100.0%** |
| Errors | 0 |

- dsv4p_nv: 4/4 (3 nvcf_pexec + 1 nv_integrate), all first-attempt
- glm5_2_nv: 4/4 (4 nv_integrate), all first-attempt
- 0 nv_tier_attempts, 0 fallback_occurred, 0 key cycling
- 0 NV-GLOBAL-COOLDOWN, 0 NV-EMPTY-FASTBREAK, 0 NV-TIER-FAIL
- Docker logs: all [NV-INTEGRATE-SUCCESS] on first attempt

### 2.4 Pre-Restart Errors (all before 19:03 UTC)

| Error Type | Count | Avg Duration | Model |
|-----------|-------|-------------|-------|
| zombie_empty_completion | 9 | 6,826ms | glm5_2_nv |
| all_tiers_exhausted | 3 | 61,297ms | dsv4p_nv |
| NVStream_TimeoutError | 2 | 96,038ms | glm5_2_nv |

### 2.5 Error Analysis

- **zombie_empty_completion (9×)**: 代码级 zombie 检测 (R1107), 快速 abort 替代旧版 NVStream_TimeoutError hang。代码级特性, 不可配置修复。
- **all_tiers_exhausted (3×)**: dsv4p_nv single-tier ATEs, FALLBACK_GRAPH={} 设计下的正常行为。
- **NVStream_TimeoutError (2×)**: glm5_2_nv integrate ~96s 超时, deadline 未强制执行 (代码级缺陷)。

### 2.6 nv_tier_attempts

- 6h: 0 rows (无失败尝试记录)

### 2.7 ms_gw 状态

- 6h: 7 req, 0/7 in DB (ms_requests 表可能不被写入), log shows 6 MS-OK-STREAM + 1 client_disconnect
- EMPTY_200_FASTBREAK_THRESHOLD=3 (at floor)
- ms_gw 不在此窗口被 nv_gw 调用为 fallback

### 2.8 当前参数 (all at floor/optimal)

```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=198
NVU_TIER_BUDGET_DSV4P_NV=72
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NVU_CONNECT_RESERVE_S=0
KEY_COOLDOWN_S=25
KEY_AUTHFAIL_COOLDOWN_S=60
TIER_COOLDOWN_S=15
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_MS_GW_FALLBACK_TIMEOUT=180
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_STREAM_FIRST_BYTE_DEADLINE_S=20
NVU_STREAM_TOTAL_DEADLINE_S=42
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
```

## 3. 决策

**NOP — 零参数变更。**

理由:
1. Post-restart 100% SR (8/8), 零错误, 零警告 — ~9h 稳定窗口
2. 所有 14 个失败均为 pre-restart 代码级错误: zombie_empty_completion (R1107 code-level feature), all_tiers_exhausted (FALLBACK_GRAPH={} design), NVStream_TimeoutError (deadline not enforced)
3. 所有参数已处于 floor/optimal 状态, 无下调空间
4. 所有 post-restart 请求均为 first-attempt success (无 key cycling, 无 fallback, 无 tier_attempts)
5. ms_gw 同样处于 optimal: EMPTY_200_FASTBREAK_THRESHOLD=3 (floor)
6. 无新错误类型, 无性能退化, 无绑定约束
7. 与 R1121 数据完全一致 (仅新增 2 个 glm5_2_nv integrate success, 04:03 UTC)

铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2
