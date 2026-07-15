# HM2 Optimize HM1 — Round R1450

## 触发分析
- **cron 脚本输出**: `"这是我提交的, 不触发"`
- 最新 commit author = `opc2_uname` (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch, 55th chain of R1395)
- HM1 本地 git log 停留在 R1206 (244 轮落后)

## 数据收集 (改前必有数据)

### 容器状态
- nv_gw: Up 51 minutes, started 2026-07-15T10:49:16Z
- compose md5: `51079b89019ddfb1a08f65e79e847b51`

### 当前参数 (docker exec nv_gw env)
| 参数 | 值 |
|------|-----|
| UPSTREAM_TIMEOUT | 66 |
| TIER_TIMEOUT_BUDGET_S | 205 |
| TIER_COOLDOWN_S | 15 |
| KEY_COOLDOWN_S | 25 |
| KEY_AUTHFAIL_COOLDOWN_S | 60 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 |
| NVU_EMPTY_200_FASTBREAK | 2 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 |
| NVU_TIER_BUDGET_DSV4P_NV | 66 |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 280 |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 |
| MIN_OUTBOUND_INTERVAL_S | 0 |
| FALLBACK_HEALTH_THRESHOLD | 0.05 |
| NVU_PEER_FB_SKIP_MODELS | (empty) |

### 6h 总体: 35req/14OK 40.0%SR

| mapped_model | total | ok | fail | sr_pct | avg_dur_ms |
|-------------|-------|-----|------|--------|-----------|
| glm5_2_nv | 25 | 14 | 11 | 56.0 | 18,342 |
| dsv4p_nv | 10 | 0 | 10 | 0.0 | 86,903 |

### 错误分类 (6h)
| error_type | count |
|-----------|-------|
| all_tiers_exhausted | 11 |
| zombie_empty_completion | 10 |

### ATE 详情
- dsv4p_nv: 10 ATE, avg 86.9s, tiers_tried_count=1
- glm5_2_nv: 1 ATE, 187.2s, tiers_tried_count=1

### zombie 详情
- glm5_2_nv integrate: 10 zombie, avg input 214K chars, avg dur 11.2s
- NVCF content-filter: finish_reason=stop, content_chars=6-20 << 50
- 0 tier_attempts (clean key pool, no zombie cycling)

### ms_gw: 25/21 ok 84.0%SR
- dsv4p_ms (DeepSeek-V4-Pro): MS-OK-STREAM + MS-STREAM-DONE in 4s — healthy
- glm5_2_ms (ZHIPUAI/glm-5.2): MS-OK-STREAM + MS-STREAM-DONE — healthy

### dsv4p_nv ATE pattern (log analysis)
```
[NV-CYCLE] tier=dsv4p_nv k2 → 504 (504_nv_gateway_timeout), cycling to next key
[NV-TIER-BUDGET] tier=dsv4p_nv budget 66.0s remaining 2.0s < 5s minimum, breaking
[NV-TIER-FAIL] tier=dsv4p_nv all 5 keys failed: 429=0, empty200=0, timeout=0, other=1, elapsed=63977ms
[NV-MS-FB] local all_tiers_exhausted (model=dsv4p_nv), attempting same-model fallback to ms_gw:40007 as dsv4p_ms
[NV-MS-FB] ms_gw relay failed after 284097ms: TimeoutError: timed out (relay_started=True)
```
- 504 is NVCF function-level degradation (all keys return same)
- BUDGET=66: k1 504(~61s) → k2 504 → 2s budget remain → break. Correct behavior.
- ms_gw processes dsv4p in 4s (MS-STREAM-DONE), but nv_gw waits 284s → TimeoutError
- **ms_gw relay TimeoutError is code-level streaming sync defect** (R1103): ms_gw sends [DONE] but nv_gw doesn't see it in streaming path. Not config-fixable.

## 决策: NOP (零参数变更)

| 问题 | 根因 | 可配置修复? |
|------|------|-----------|
| zombie_empty_completion (10) | NVCF content-filter, stop+6-20chars, 214K avg input | ❌ NVCF 侧 |
| dsv4p_nv 504 ATE (10) | NVCF function-level degradation, 504 on all keys | ❌ NVCF 侧 |
| ms_gw relay TimeoutError | Code-level streaming sync defect, ms_gw completes in 4s but nv_gw doesn't see [DONE] | ❌ 代码级缺陷 |
| 0 tier_attempts | Clean key pool, no 429 cycling | ✅ 健康 |

所有参数处于 floor/optimal 状态。无配置可优化项。铁律:只改HM1不改HM2。

## ⏳ 轮到HM1优化HM2
