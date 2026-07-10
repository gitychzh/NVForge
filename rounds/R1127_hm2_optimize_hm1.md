# R1127: HM2→HM1 — NOP (false trigger, double-dispatch of R1126, post-restart 100% SR 19/19, all 14 failures pre-restart code-level, all params at floor/optimal, no config change justified). 铁律:只改HM1不改HM2

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit 10cf5bb (R1126) author = `opc2_uname` (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch after R1126)
- Symlink 已指向 R1126 ✓

## 2. 改前数据 (2026-07-11 05:05 UTC)

### 2.1 nv_requests 概览

| 窗口 | 总 | OK | Err | SR |
|------|-----|-----|------|------|
| 6h | 147 | 133 | 14 | 90.5% |
| 2h | 15 | 15 | 0 | **100%** |
| 1h | 11 | 11 | 0 | **100%** |

### 2.2 Per-model 明细 (6h)

| Model | 总 | OK | Err | SR | avg_dur | max_dur |
|-------|-----|-----|------|------|---------|---------|
| glm5_2_nv | 102 | 91 | 11 | 89.2% | 17,726 | 96,999 |
| dsv4p_nv | 29 | 26 | 3 | 89.7% | 19,314 | 61,376 |
| minimax_m3_nv | 9 | 9 | 0 | **100%** | 14,483 | 32,892 |
| kimi_nv | 7 | 7 | 0 | **100%** | 3,605 | 7,771 |

### 2.3 Per-model upstream_type 明细 (6h, success only)

| Model | upstream | cnt | avg_dur | max_dur |
|-------|----------|-----|---------|---------|
| glm5_2_nv | nv_integrate | 91 | 17,068 | 70,215 |
| dsv4p_nv | nvcf_pexec | 26 | 11,666 | 48,049 |
| minimax_m3_nv | nvcf_pexec | 9 | — | — |
| kimi_nv | nvcf_pexec | 7 | — | — |

### 2.4 Error 分类 (6h)

| Error Type | Count | Classification |
|------------|-------|----------------|
| zombie_empty_completion | 9 | 代码级 (zombie detection, 3-15s fast abort) |
| all_tiers_exhausted | 3 | 代码级 (pre-restart, ms_gw BrokenPipeError) |
| NVStream_TimeoutError | 2 | 代码级 (NVCF stream abort) |

### 2.5 ATE tiers breakdown (6h)

| tiers_tried_count | cnt | avg_dur |
|-------------------|---|---------|
| 1 | 14 | 31,243ms |

→ 全部单层 ATE。全部 pre-restart。全部代码级。

### 2.6 Fallback (6h)

| fallback_occurred | cnt | ok |
|-------------------|---|-----|
| f | 147 | 133 |

→ 零 fallback 触发。`(no fallback, 3model)` 符合 R832 设计（FALLBACK_GRAPH 为空）。

### 2.7 nv_tier_attempts (6h)

**0 rows** — 零 per-key 失败尝试。所有成功请求 first-attempt 成功。

### 2.8 Hourly SR 分解 (6h)

| Hour (UTC) | Total | OK | SR |
|------------|-------|-----|------|
| 15:00 | 92 | 90 | 97.8% |
| 16:00 | 7 | 5 | 71.4% |
| 17:00 | 20 | 11 | 55.0% |
| 18:00 | 9 | 8 | 88.9% |
| **19:00** | 6 | 6 | **100%** |
| **20:00** | 7 | 7 | **100%** |
| **21:00** | 6 | 6 | **100%** |

→ Post-restart (19:00 UTC+): **3h+ 100% SR**。全部 14 个错误 pre-restart。

### 2.9 容器状态

- **nv_gw**: Up 2 hours (healthy), 重启时间 2026-07-10T19:03:27Z
- Post-restart: 3h+ 零错误，100% SR

### 2.10 实时日志 (最近 100 行, 03:05-05:04 UTC)

```
dsv4p_nv: k1/k2/k3/k5 all first-attempt success (pexec + integrate)
  NV-SUCCESS / NV-INTEGRATE-SUCCESS, 零错误
  NV-THINKING-TIMEOUT extended to 66s (thinking requests)
glm5_2_nv: k1-k5 all first-attempt integrate success
  NV-INTEGRATE-SUCCESS, 零 SSLEOFError, 零 timeout
  100% first-key cycling
tier_chain=['model'] (no fallback, 3model) — R832 预期状态
健康状态: 极佳
```

### 2.11 HM1 nv_gw 当前配置

```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=198
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
FALLBACK_HEALTH_THRESHOLD=0.05
NVU_MS_GW_FALLBACK_TIMEOUT=180
NVU_STREAM_TOTAL_DEADLINE_S=42
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NVU_TIER_BUDGET_DSV4P_NV=72
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_FORCE_STREAM_UPGRADE=0
NV_INTEGRATE_MODELS=glm5_2_nv
NV_INTEGRATE_KEY_COOLDOWN_S=0
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=15
MIN_OUTBOUND_INTERVAL_S=0
NVU_CONNECT_RESERVE_S=0
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_GATEWAY_API_KEY=nv-gw-token
```

## 3. 参数状态评估

| 参数 | 当前值 | 状态 | 理由 |
|------|--------|------|------|
| UPSTREAM_TIMEOUT | 66 | optimal | 0 NVCFPexecTimeout, 0 tier_attempts |
| TIER_TIMEOUT_BUDGET_S | 198 | optimal | 198 >> 66, FASTBREAK=1, 132s headroom |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | stable | R997, 20+ rounds stable |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | stable | R1010, integrate uniform |
| NVU_EMPTY_200_FASTBREAK | 2 | stable | R1031, 0 empty_200 |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | floor | R818 fix |
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 | stable | R1088, generous |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | stable | R1102, glm5_2 integrate |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | stable | R1038 |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | stable | R1078, dsv4p cap |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | stable | R1010, glm5_2 cap |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | stable | R1010 |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | stable | R1071, BUDGET 198≥66+66 |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | stable | R1039 |
| NV_INTEGRATE_MODELS | glm5_2_nv | stable | R680+ |
| KEY_COOLDOWN_S | 25 | floor | |
| TIER_COOLDOWN_S | 15 | floor | R1103 |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor | |
| NVU_CONNECT_RESERVE_S | 0 | floor | |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor | |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | stable | R922 |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | stable | R1100 |

## 4. NOP 决策

### 4.1 NOP Gate 评估

| Gate | 条件 | 6h 结果 | Post-restart 结果 |
|------|------|---------|-------------------|
| 1 | 所有 ATE 双 tier | FAIL (14 single-tier) | PASS (0 ATE) |
| 2 | 0 single-tier 或全部代码级 | PASS (9 zombie + 2 NVStream + 3 ATE = 全部代码级) | PASS |
| 3 | NVCFPexecTimeout buffer ≥3s | PASS (0 tier_attempts) | PASS |
| 4 | FALLBACK_GRAPH bidirectional | N/A (R832 FALLBACK_GRAPH={}) | N/A |
| 5 | Fallback 100% SR | N/A (0 fallback) | N/A |
| 6 | 所有 params at floor/optimal | PASS | PASS |

### 4.2 决策: NOP

**Post-restart 3h+ 100% SR (19/19)。全部 14 个错误 pre-restart 且全部代码级。**

- **zombie_empty_completion (9×)**: 代码级 intentional mechanism — 空流 zombie 检测，3-15s fast abort 替代旧 96s hang。不是 config-fixable。
- **NVStream_TimeoutError (2×)**: 代码级 NVCF 流超时 — 不可配置。
- **all_tiers_exhausted (3×)**: pre-restart, 代码级 (ms_gw BrokenPipeError / 504 模式)。
- **nv_tier_attempts: 0 rows** — 零 per-key 失败。
- **实时日志**: 100% first-key 成功率，dsv4p_nv + glm5_2_nv 全部 NV-SUCCESS / NV-INTEGRATE-SUCCESS。
- **所有参数 at floor/optimal**。零漂移。零调整空间。

**系统极度健康。等待更多流量积累验证全模型链路。**

## ⏳ 轮到HM1优化HM2
