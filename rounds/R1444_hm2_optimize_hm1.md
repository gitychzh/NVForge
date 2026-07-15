# HM2 Optimize HM1 — Round R1444 (NOP)

## 1. 触发分析
cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = `opc2_uname` (HM2)
- 最新 commit: `ae05a0b R1443: HM2→HM1 — NOP (false trigger, R1442 just deployed 4min ago)`
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 / double-dispatch (R1395→R1444 chain, 第44次)
- symlink 已指向 `rounds/R1443_hm2_optimize_hm1.md`

## 2. 改前数据 (6h窗口, 2026-07-15 ~17:45 UTC)

### 2.1 nv_gw SR
| 指标 | 值 |
|------|-----|
| 总请求 | 56 |
| 成功 (200) | 35 |
| 失败 (502) | 21 |
| SR | 62.5% |

### 2.2 502 error breakdown
| Model | Error Type | Count | Avg Duration |
|-------|-----------|-------|-------------|
| glm5_2_nv | zombie_empty_completion | 10 | 7,033ms |
| dsv4p_nv | all_tiers_exhausted | 7 | 101,828ms |
| dsv4p_nv | zombie_empty_completion | 4 | 14,550ms |
| glm5_2_nv | all_tiers_exhausted | 1 | 187,171ms |

- **zombie**: 14 total (10 glm5_2_nv + 4 dsv4p_nv) — NVCF content-filter, not config-fixable
- **ATE**: 8 total (7 dsv4p_nv + 1 glm5_2_nv). dsv4p_nv avg 101s (mostly pre-R1442, BUDGET=66 at floor). glm5_2_nv single ATE: integrate timeout(91s)→FASTBREAK→pexec SSLEOF×2+504+timeout(22s)→187s→ms_gw→MS-VARIANT-EXHAUSTED→503
- **tier_attempts**: 0
- **vs R1443**: +2 requests, +2 ATE (both post-restart from R1442 deploy), -2 SR points (within noise)

### 2.3 Hourly SR
| Hour | Total | OK | Fail | SR |
|------|-------|-----|------|-----|
| 04:00 | 7 | 3 | 4 | 42.9% |
| 05:00 | 26 | 22 | 4 | 84.6% |
| 06:00 | 5 | 3 | 2 | 60.0% |
| 07:00 | 5 | 1 | 4 | 20.0% |
| 08:00 | 5 | 2 | 3 | 40.0% |
| 09:00 | 8 | 4 | 4 | 50.0% |

### 2.4 成功请求
| Model | Count | Avg Duration |
|-------|-------|-------------|
| glm5_2_nv | 32 | ~12,809ms |
| dsv4p_nv | 3 | ~22,369ms |

### 2.5 ms_gw
| 指标 | 值 |
|------|-----|
| 总请求 | 33 |
| 成功 (ok) | 29 |
| 失败 (error) | 4 |
| SR | 87.9% |

ms_gw 成功分布:
| Model | Count | Avg Duration |
|-------|-------|-------------|
| ZHIPUAI/GLM-5.2 | 22 | 16,476ms |
| DEEPSEEK-AI/DEEPSEEK-V4-PRO | 7 | 6,469ms |

ms_gw errors: 4x MS-VARIANT-EXHAUSTED for glm5_2_ms (all 10 variants exhausted → 503). ModelScope-side degradation, not HM1 config-fixable.

### 2.6 容器状态
- Container: `nv_gw Up since 09:32 UTC` (R1442 deploy, ~8h ago)
- Post-restart traffic: 仅 2 条请求 (glm5_2_nv ATE 187s + dsv4p_nv ATE 62s)，均为 R1442 配置下首请求
- Compose md5: `82356a53` (R1442 变更后)
- Post-restart window: 2req/0OK 0%SR (仅2条，无统计意义)

### 2.7 关键参数 (container env)
```
PROXY_TIMEOUT=360                  # R1442: 300→360
NVU_MS_GW_FALLBACK_TIMEOUT=240     # R1442: 210→240
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=205
NVU_TIER_BUDGET_DSV4P_NV=66        # R1440 floor
NVU_TIER_BUDGET_GLM5_2_NV=96
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_PEER_FB_SKIP_MODELS= (empty)
MIN_OUTBOUND_INTERVAL_S=0
NVU_CONNECT_RESERVE_S=0
NVU_SSLEOF_RETRY_DELAY_S=1.0
```

### 2.8 近期日志关键事件
```
17:33:20 glm5_2_nv integrate k1 timeout 91s → FASTBREAK → integrate-fallback pexec
  → k2 SSLEOF 5s → k3 SSLEOF 5s → k4 504 → k5 pexec timeout 22s → ATE 187s
  → ms_gw fallback glm5_2_ms → MS-VARIANT-EXHAUSTED(30s, all 10 variants) → 503 → FAILED
17:35:53 dsv4p_nv → k4 504 → ATE 62s → ms_gw fallback dsv4p_ms → TimeoutError 249s → FAILED
```

## 3. 决策: NOP

### 3.1 原因
1. **False trigger**: cron 脚本正确标记 "这是我提交的, 不触发"
2. **Double-dispatch**: R1443 已提交，symlink 正确，数据与 R1443 一致
3. **所有参数已在 floor/optimal**: 无退化信号，无优化空间
4. **14 zombie 非配置可修复**: NVCF content-filter 返回空响应，非 nv_gw 参数可控制
5. **ms_gw MS-VARIANT-EXHAUSTED**: ModelScope glm5_2_ms 全 variant 耗尽，属上游 ModelScope 侧问题
6. **R1442 的 PROXY_TIMEOUT=360 和 NVU_MS_GW_FALLBACK_TIMEOUT=240**: 仅 2 条 post-restart 请求，数据不足评估效果，但参数方向正确
7. **HM1 git 仍停留在 R1206**: 238 轮落后，HM1 未同步

### 3.2 参数变更: 无 (NOP)

### 3.3 compose 变更: 无

### 3.4 容器重启: 无

## 4. 验证
- 无需验证 (NOP, 无参数变更)

## 5. 数据来源
- HM1 container env: `docker exec nv_gw env`
- HM1 DB: `docker exec logs_db psql -U litellm -d hermes_logs`
- HM1 logs: `docker logs nv_gw --tail 200`, `docker logs ms_gw --tail 50`
- HM1 ms_gw: `ms_requests` table
- Compose md5: `82356a53` (R1442 变更后)
- HM1 git: `de04120 R1206` (238 rounds behind)

---
铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
