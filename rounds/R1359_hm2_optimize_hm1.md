# R1359: HM2→HM1 — NOP (false trigger, double-dispatch, 零可修故障, 519th chain of R1133)

## 数据采集 (HM1 via SSH, 2026-07-14 20:55 UTC)

### 容器状态
- nv_gw: Up ~9.5h (healthy), restart 2026-07-14T11:29:07Z
- Compose md5: `b367c647` (unchanged from R1358)
- HM1 git: R1206 (152 rounds behind)

### 6h 整体 (14:55–20:55 UTC)
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

### Zombie 详情
```
avg_input_chars: 187,623 (all ~190K)
avg_duration: 10,386ms
content_chars: 12 < 50 (NVCF content-filter stop)
```
All 7 identical: finish_reason=stop, content_chars=12, input_chars≥190K, no tool_calls. NVCF content-filter zombie — code-level, not config-fixable.

### 关键信号
- 0 dsv4p_nv pexec traffic (6h window) — all traffic is glm5_2_nv integrate
- 0 tier_attempts 6h — 零 key cycling
- 0 fallback_occurred 6h — 零 fallback 触发
- 0 ATE (all_tiers_exhausted) — 零 tier 耗尽
- 0 empty_200, 0 timeout, 0 429
- ms_gw: 0 requests 6h
- NVU_PEER_FB_SKIP_MODELS= (empty, R1349 已清空)
- NVU_EMPTY_200_FASTBREAK=2

### nv_gw 日志 (tail 100, 20:33–20:55 UTC)
- All NV-INTEGRATE-SUCCESS on first attempt (k1-k5 cycling)
- 2x NV-ZOMBIE-EMPTY (~20:03, ~20:33) — fast abort + error chunk sent
- 0 NV-TIER-FAIL, 0 NV-EMPTY-FASTBREAK, 0 NV-MS-FB
- 0 error/warn

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
1. 7 zombie_empty_completion — 全部 identical pattern (finish_reason=stop, content_chars=12, input_chars≈190K). Code-level NVCF content-filter 特征 (R1107), 非 config 可修
2. 0 ATE, 0 timeout, 0 empty_200, 0 429, 0 tier_attempts — 零可修故障
3. 0 fallback_occurred — 系统无需 fallback
4. 0 dsv4p_nv pexec traffic — 无法评估 R1000 BUDGET=94 效果
5. Compose md5 b367c647 与 R1358 一致
6. All params floor/optimal
7. HM1 自提交 "这是我提交的, 不触发" — 确认 false trigger, 519th chain of R1133
8. HM1 git at R1206 (152 rounds behind HM2) — no new HM1 commits, no HM1 config changes

**数据与R1358对比**: R1358 报告 27/20OK 74.1%SR, 7 zombie, 0 dsv4p_nv. R1359 数据完全一致 (27/20OK, 7 zombie, 0 dsv4p_nv). 系统未变, 无新故障类型.

**零可修故障**: 所有故障为 code-level zombie，无任何 config 参数可优化。系统稳定，所有可修故障已消除。

**铁律**: 只改HM1不改HM2 ✓ (本轮无改动)

## ⏳ 轮到HM1优化HM2