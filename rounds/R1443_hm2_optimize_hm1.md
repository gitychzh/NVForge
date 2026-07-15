# HM2 Optimize HM1 — Round R1443 (NOP)

## 1. 触发分析
cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = `opc2_uname` (HM2)
- 最新 commit: `3c8e42b R1442: HM2→HM1 — PROXY_TIMEOUT 300→360, NVU_MS_GW_FALLBACK_TIMEOUT 210→240`
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 / double-dispatch (R1395→R1443 chain, 第43次)
- symlink 已指向 `rounds/R1442_hm2_optimize_hm1.md`

## 2. 改前数据 (6h窗口, 2026-07-15 11:35 UTC)

### 2.1 nv_gw SR
| 指标 | 值 |
|------|-----|
| 总请求 | 54 |
| 成功 (200) | 35 |
| 失败 (502) | 19 |
| SR | 64.8% |

### 2.2 502 error breakdown
| Model | Error Type | Count | Avg Duration |
|-------|-----------|-------|-------------|
| glm5_2_nv | zombie_empty_completion | 10 | 7,033ms |
| dsv4p_nv | all_tiers_exhausted | 5 | 109,635ms |
| dsv4p_nv | zombie_empty_completion | 4 | 14,550ms |

- **zombie**: 14 total (10 glm5_2_nv + 4 dsv4p_nv) — NVCF content-filter, not config-fixable
- **ATE**: 5 dsv4p_nv all_tiers_exhausted, avg 109s (mostly pre-R1442, BUDGET=66 already at floor)
- **tier_attempts**: 0

### 2.3 成功请求
| Model | Count | Avg Duration |
|-------|-------|-------------|
| glm5_2_nv | 32 | 12,809ms |
| dsv4p_nv | 3 | 22,369ms |

### 2.4 ms_gw
| 指标 | 值 |
|------|-----|
| 总请求 | 31 |
| 成功 (ok) | 28 |
| 失败 (error) | 4 |
| SR | 90.3% |

ms_gw 成功分布:
| Model | Count | Avg Duration |
|-------|-------|-------------|
| ZHIPUAI/GLM-5.2 | 22 | 16,476ms |
| DEEPSEEK-AI/DEEPSEEK-V4-PRO | 7 | 6,469ms |

ms_gw errors: MS-VARIANT-EXHAUSTED for glm5_2_ms (all 10 variants exhausted → 503 return). ModelScope-side degradation, not HM1 config-fixable.

### 2.5 容器状态
- Container: `nv_gw Up 4 minutes (healthy)` — R1442 刚部署 4 分钟
- Post-restart log: 仅 2 条请求（glm5_2_nv integrate→pexec ATE 187s + dsv4p_nv ATE 62s），均为新配置首请求
- Compose md5: `5e81a97c` (R1442 变更后)

### 2.6 关键参数 (container env)
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

### 2.7 近期日志关键事件
```
17:33:20 glm5_2_nv integrate k1 timeout 91s → FASTBREAK → integrate-fallback pexec
  → k2 SSLEOF 5s → k3 SSLEOF 5s → k4 504 → k5 pexec timeout 22s → ATE 187s
  → ms_gw fallback glm5_2_ms → 503 after 30s (MS-VARIANT-EXHAUSTED) → FAILED
17:35:53 dsv4p_nv → k4 504 → ATE 62s → ms_gw fallback dsv4p_ms (result unknown)
```

## 3. 决策: NOP

### 3.1 原因
1. **False trigger**: cron 脚本正确标记 "这是我提交的, 不触发"
2. **R1442 刚部署 4 分钟**: 零有效 post-restart 数据，无法评估 R1442 的 PROXY_TIMEOUT=360 和 NVU_MS_GW_FALLBACK_TIMEOUT=240 效果
3. **所有参数已在 floor/optimal**: BUDGET=66, FASTBREAK=1, PEER_FB_SKIP_MODELS=empty, TIER_COOLDOWN=15, KEY_COOLDOWN=25, MIN_OUTBOUND=0, CONNECT_RESERVE=0
4. **14 zombie 非配置可修复**: NVCF content-filter 返回空响应，非 nv_gw 参数可控制
5. **ms_gw MS-VARIANT-EXHAUSTED**: ModelScope glm5_2_ms 全 variant 耗尽，属上游 ModelScope 侧问题，非 HM1 配置可修复

### 3.2 参数变更: 无 (NOP)

### 3.3 compose 变更: 无

### 3.4 容器重启: 无

## 4. 验证
- 无需验证 (NOP, 无参数变更)

## 5. 数据来源
- HM1 container env: `docker exec nv_gw env`
- HM1 DB: `docker exec logs_db psql -U litellm -d hermes_logs`
- HM1 logs: `docker logs nv_gw --tail 200`
- HM1 ms_gw: `docker logs ms_gw --tail 50`, `ms_requests` table
- Compose md5: `5e81a97c` (R1442 变更后)

---
铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
