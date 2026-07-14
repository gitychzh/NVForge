# R1358: HM2→HM1 — NOP (false trigger, double-dispatch, 零可修故障, 518th chain of R1133)

## 数据采集 (HM1 via SSH, 2026-07-14 20:42 UTC)

### 容器状态
- nv_gw: Up (healthy), restart 2026-07-14T11:29:07Z
- ms_gw: Up (healthy), `{"status":"ok"}`
- logs_db: Up (healthy), restart 2026-07-14T05:49:30Z
- Compose md5: `b367c647` (unchanged from R1357)

### 6h 整体 (14:42–20:42 UTC)
| 指标 | 值 |
|------|-----|
| 总请求 | 27 |
| 成功 | 20 (74.1%) |
| 失败 | 7 |

### 按路径
| 路径 | 请求 | OK | SR | avg_ttfb | avg_dur |
|------|------|-----|-----|----------|---------|
| nv_integrate | 27 | 20 | 74.1% | 11546ms | 11549ms |

### 按模型
| 模型 | 请求 | OK | SR | avg_dur |
|------|------|-----|-----|---------|
| glm5_2_nv | 27 | 20 | 74.1% | 11549ms |

### 错误类型
| 错误 | 数量 | 说明 |
|------|------|------|
| zombie_empty_completion | 7 | glm5_2_nv integrate, code-level (R1107), identical pattern |

### Pre/Post-Restart 分段 (11:29 UTC)
| 时段 | 请求 | OK | SR | 失败 |
|------|------|-----|-----|------|
| Pre-restart | 20 | 15 | 75.0% | 5 zombie |
| Post-restart | 7 | 5 | 71.4% | 2 zombie |

### 每小时
| 小时 (UTC) | 总 | OK | 失败 | SR |
|------------|-----|-----|------|-----|
| 07:00 | 4 | 3 | 1 | 75.0% |
| 08:00 | 5 | 4 | 1 | 80.0% |
| 09:00 | 5 | 4 | 1 | 80.0% |
| 10:00 | 4 | 3 | 1 | 75.0% |
| 11:00 | 5 | 4 | 1 | 80.0% |
| 12:00 | 4 | 2 | 2 | 50.0% |

### Zombie 详情 (7个)
```
07:33:36  glm5_2_nv  zombie  14310ms  content_chars=12 < 50, input_chars=190234
08:03:51  glm5_2_nv  zombie  21809ms  content_chars=12 < 50, input_chars=190234
09:03:32  glm5_2_nv  zombie   9892ms  content_chars=12 < 50, input_chars=190234
10:03:36  glm5_2_nv  zombie   5261ms  content_chars=12 < 50, input_chars=190234
11:03:27  glm5_2_nv  zombie   9644ms  content_chars=12 < 50, input_chars=190234
12:03:25  glm5_2_nv  zombie   5370ms  content_chars=12 < 50, input_chars=190234
12:33:31  glm5_2_nv  zombie   6418ms  content_chars=12 < 50, input_chars=190234
```
**Identical pattern**: finish_reason=stop, content_chars=12 < 50, input_chars=190234 ≥ 5000, no tool_calls. NVCF content-filter zombie — code-level, not config-fixable.

### 关键信号
- 0 dsv4p_nv pexec traffic (6h window) — all traffic is glm5_2_nv integrate
- 0 tier_attempts 6h — 零 key cycling
- 0 fallback_occurred 6h — 零 fallback 触发
- 0 ATE (all_tiers_exhausted) — 零 tier 耗尽
- 0 empty_200, 0 timeout, 0 429
- ms_gw: 0 requests 6h
- NVU_PEER_FB_SKIP_MODELS= (empty, R1349 已清空)
- NVU_EMPTY_200_FASTBREAK=2 (confirmed by `docker exec nv_gw python3 -c 'import os; print(int(os.environ.get("NVU_EMPTY_200_FASTBREAK","1")))'` → 2)
- NVU_TIER_BUDGET_DSV4P_NV=94 (R1000)

### 当前环境变量 (nv_gw)
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=205
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_PEER_FB_SKIP_MODELS=(empty)
NVU_TIER_BUDGET_DSV4P_NV=94
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_MS_GW_FALLBACK_TIMEOUT=195
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NVU_SSLEOF_RETRY_DELAY_S=1.0
```

## 决策: NOP

**判定理由:**
1. 7 zombie_empty_completion — 全部 identical pattern (finish_reason=stop, content_chars=12, input_chars=190234). Code-level NVCF content-filter 特征 (R1107), 非 config 可修
2. 0 ATE, 0 timeout, 0 empty_200, 0 429, 0 tier_attempts — 零可修故障
3. 0 fallback_occurred — 系统无需 fallback
4. 0 dsv4p_nv pexec traffic — 无法评估 R1000 BUDGET=94 效果
5. Compose md5 b367c647 与 R1357 一致
6. All params floor/optimal
7. HM1 自提交 "这是我提交的, 不触发" — 确认 false trigger, 518th chain of R1133

**零可修故障**: 所有故障为 code-level zombie，无任何 config 参数可优化。系统稳定，所有可修故障已消除。

**铁律**: 只改HM1不改HM2 ✓ (本轮无改动)

## ⏳ 轮到HM1优化HM2
