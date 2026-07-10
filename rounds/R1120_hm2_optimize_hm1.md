# HM2 Optimize HM1 — Round R1120

> **铁律**: 只改HM1不改HM2

## 1. 触发分析

cron 脚本输出: `[2026-07-11 03:50:15] 这是我提交的, 不触发` — **false trigger (HM2 self-commit, double-dispatch of R1119)**

- R1119 已由预运行脚本提交 (NOP, same commit 807a2b6)
- 符号链接已指向 R1119 — 这是 double-dispatch (R884 pattern)
- HM1 本地 git log 仍停留在 R821 (~299 rounds behind) — 正常
- 最新 commit: `c53592a R1119: HM2→HM1 — NOP`

## 2. 数据收集

### 2.1 Container 状态

- Container: `nv_gw` (port 40006)
- 启动时间: `2026-07-10T19:03:27Z` (~9h ago)
- Tier chain: `['dsv4p_nv'] (no fallback, 3model)` — 预期状态 (R832 FALLBACK_GRAPH={} design)
- FALLBACK_HEALTH_THRESHOLD=0.05 (dead param, 实际 effective=0.05 from NVU_FALLBACK_HEALTH_THRESHOLD)

### 2.2 6h 总体统计

| 指标 | 值 |
|------|-----|
| Total | 140 |
| OK (200) | 126 |
| Fail (non-200) | 14 |
| SR | 90.0% |

### 2.3 Post-Restart (19:03 UTC→now)

| 指标 | 值 |
|------|-----|
| Total | 6 |
| OK | 6 |
| SR | 100.0% |
| Errors | 0 |

- dsv4p_nv: 4/4 (3 nvcf_pexec + 1 nv_integrate)
- glm5_2_nv: 2/2 (2 nv_integrate)
- 0 nv_tier_attempts
- 0 fallback_occurred
- 0 NV-GLOBAL-COOLDOWN

### 2.4 Pre-Restart Errors (all before 19:03 UTC)

| Error Type | Count | Avg Duration | Model |
|-----------|-------|-------------|-------|
| zombie_empty_completion | 9 | 6,826ms | glm5_2_nv |
| all_tiers_exhausted | 3 | 61,297ms | dsv4p_nv |
| NVStream_TimeoutError | 2 | 96,038ms | glm5_2_nv |

### 2.5 Error Analysis

- **zombie_empty_completion (9×)**: 代码级 zombie 检测功能 (R1107), 在 3-15s 内快速 abort 替代旧版 96s NVStream_TimeoutError hang。代码级特性, 不可配置修复。zero-change.
- **all_tiers_exhausted (3×)**: dsv4p_nv single-tier ATEs (~61s), tiers_tried_count=1, fallback_actually_attempted=false。FALLBACK_GRAPH={} 设计下的正常行为。ms_gw BrokenPipeError (stream sync defect, 代码级)。zero-change.
- **NVStream_TimeoutError (2×)**: glm5_2_nv integrate ~96s 超时, 远超 NVU_STREAM_FIRST_BYTE_DEADLINE_S=20 和 NVU_STREAM_TOTAL_DEADLINE_S=42 — deadline 未强制执行 (代码级缺陷)。zero-change.

### 2.6 nv_tier_attempts

- 6h: 0 rows (无失败尝试记录)
- 所有错误均为代码级, 不产生 tier_attempts

### 2.7 ms_gw 状态

- 6h: 7 req, 6 ok (86%), 1 client_disconnect
- 24h: 21 req, 16 ok (76%), 5 client_disconnect
- EMPTY_200_FASTBREAK_THRESHOLD=3 (R900 optimal, at floor)
- MS-FASTBREAK breaking at consecutive_empty=3 — 正常工作
- client_disconnect 来自 nv_gw BrokenPipeError (stream sync defect, 代码级)
- ms_gw 不在此窗口被 nv_gw 调用为 fallback (0 nv_gw fallback 请求)

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
1. Post-restart 100% SR (6/6), 零错误
2. 所有 14 个失败均为 pre-restart 代码级错误: zombie_empty_completion (R1107 code-level feature), all_tiers_exhausted (FALLBACK_GRAPH={} design + ms_gw BrokenPipeError), NVStream_TimeoutError (deadline not enforced)
3. 所有参数已处于 floor/optimal 状态
4. ms_gw 同样处于 optimal: EMPTY_200_FASTBREAK_THRESHOLD=3 (floor), 86% 6h SR (6/7)
5. 无新错误类型, 无性能退化, 无绑定约束

铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2
