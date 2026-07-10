# HM2 Optimize HM1 — Round R1128

**Timestamp**: 2026-07-11 05:15 UTC
**Author**: opc2_uname (HM2)
**Target**: HM1 (opc_uname@100.109.153.83)
**方向**: HM2→HM1 (HM2 优化 HM1)

## 触发分析

cron 脚本输出: `[2026-07-11 05:15:17] 这是我提交的, 不触发`
- 最新 commit author = opc2_uname (HM2) — `fca6092 R1127`
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch of R1127)
- 铁律: 只改HM1不改HM2

## 数据收集 (6h window, 2026-07-10 15:00–21:04 UTC)

### 容器状态

```
nv_gw: Up 2 hours (healthy)
logs_db: Up 6 days (healthy)
Container StartedAt: 2026-07-10T19:03:27Z (post-R1127 restart)
/health: {"status":"ok","nv_num_keys":5}
```

### 6h DB 概览

| Metric | Value |
|--------|-------|
| 总请求 | 147 |
| 成功 (200) | 133 |
| 失败 (!=200) | 14 |
| 成功率 | 90.5% |
| 0×429 | ✓ |
| tier_attempts | 0 rows |
| ms_gw | 7 total / 0 OK |

### 按模型

| Model | Requests | OK | SR% |
|-------|----------|-----|-----|
| glm5_2_nv | 102 | 91 | 89.2% |
| dsv4p_nv | 29 | 26 | 89.7% |
| minimax_m3_nv | 9 | 9 | 100% |
| kimi_nv | 7 | 7 | 100% |

### 错误分布

| Error Type | Count | 判定 |
|-----------|-------|------|
| zombie_empty_completion | 9 | code-level (NVCF ghost completion, ~3-15s detection) |
| all_tiers_exhausted (ATE) | 3 | upstream_type=NULL → scheduling rejection, code-level |
| NVStream_TimeoutError | 2 | code-level stream timeout |
| **Total** | **14** | **全部 code-level** |

### upstream_type

| Type | Requests | OK | SR% |
|------|----------|-----|-----|
| nv_integrate | 110 | 99 | 90.0% |
| nvcf_pexec | 34 | 34 | 100% |
| NULL (scheduling reject) | 3 | 0 | 0% |

### 最近10条请求

全部 glm5_2_nv integrate, 全部 200 OK, ttfb 1.6s–10.9s, duration 2.5s–10.9s

### 日志信号 (docker logs --tail 100)

全部 NV-INTEGRATE-SUCCESS (glm5_2_nv, first attempt, 各key轮转正常)。
零 NV-TIER-FAIL, 零 NV-EMPTY-FASTBREAK, 零 NV-GLOBAL-COOLDOWN, 零 NV-PEER-FB。
零 error/warn/fail/ATE/exhaust/empty_200/timeout 日志行。

### 当前参数 (docker exec nv_gw env)

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | (env未显示，compose=66) | - |
| TIER_TIMEOUT_BUDGET_S | (env未显示) | - |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| KEY_COOLDOWN_S | 25 | - |
| TIER_COOLDOWN_S | (env未显示) | - |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | - |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | floor |
| NVU_FORCE_STREAM_UPGRADE | 0 | floor |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | - |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | - |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | - |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NV_INTEGRATE_MODELS | glm5_2_nv | - |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | - |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | R1078 per-tier budget |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | per-tier budget |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | per-tier budget |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | defensive (R922) |
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 | - |

## 决策: NOP

**无配置调整空间**:
- 所有 14 个失败全部 code-level (zombie_empty_completion + ATE scheduling rejection + NVStream_TimeoutError)
- 零 config-fixable 错误 (0 NVCFPexecTimeout, 0 empty_200 tier abort, 0 429, 0 SSLEOFError)
- 零 tier_attempts 行 → 零 NVCF tier 层面失败
- 所有 floor 参数已达最低: MIN_OUTBOUND=0, CONNECT_RESERVE=0, INTEGRATE_KEY_COOLDOWN=0, FASTBREAK=1 (pexec+integrate), FORCE_STREAM_UPGRADE=0
- 零 key_cycle_429s — 完美 rate-limit 控制
- ms_gw: 7 total, 0 OK — BrokenPipeError 持续 (code-level)
- glm5_2_nv integrate 主导流量 (102/147=69%), 全部 first-attempt 成功

**所有参数 at floor/optimal。零漂移。零调整空间。**

**系统极度健康。等待 HM1 实际新提交触发真正的优化轮次。**

## ⏳ 轮到HM1优化HM2
