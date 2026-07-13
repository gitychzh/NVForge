# HM2 Optimize HM1 — Round R1234

> **铁律**: 只改HM1配置绝不改HM2本地

## 1. 触发信息
- **Cron script output**: "这是我提交的, 不触发"
- **Latest commit**: f3cece3 by opc2_uname (HM2) — R1233
- **HM1 git log**: R1206 (27 rounds behind HM2)
- **Verdict**: FALSE TRIGGER (double-dispatch). Same data as R1233, no HM1 changes.

## 2. 数据收集 (改前必有数据)

### 2.1 nv_gw 容器日志 (最近100行)
- glm5_2_nv integrate active, all keys succeeding on first attempt (k1-k5, 2-3s TTFB)
- 1 zombie_empty_completion detected: finish_reason=stop, content_chars=12 < 50, input_chars=115551 — NVCF content-filter, gateway detection+error-chunk correct

### 2.2 nv_gw 环境变量 (floor/optimal)
```
TIER_TIMEOUT_BUDGET_S=210        UPSTREAM_TIMEOUT=66
KEY_COOLDOWN_S=25               TIER_COOLDOWN_S=15
MIN_OUTBOUND_INTERVAL_S=0       NVU_CONNECT_RESERVE_S=0
NVU_PEXEC_TIMEOUT_FASTBREAK=1   NVU_EMPTY_200_FASTBREAK=2
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_KEY_COOLDOWN_S=0  NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NVU_TIER_BUDGET_DSV4P_NV=72     NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_FORCE_STREAM_UPGRADE=0      NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
```

### 2.3 DB 6h 总体统计
| Metric | Value |
|--------|-------|
| Total | 104 req |
| OK (200) | 80 (76.9% SR) |
| Fail | 24 |

### 2.4 DB 6h 按模型
| request_model | mapped_model | cnt | ok | fail | avg_ttfb_ms | avg_dur_ms |
|---------------|-------------|-----|-----|------|-------------|------------|
| glm5_2_nv | glm5_2_nv | 96 | 77 | 19 | 37400 | 50297 |
| dsv4p_nv | dsv4p_nv | 8 | 3 | 5 | 10108 | 55866 |

### 2.5 DB 6h 按路径
| upstream_type | cnt | ok | fail | avg_ttfb_ms | avg_dur_ms | max_dur_ms |
|---------------|-----|-----|------|-------------|------------|------------|
| nv_integrate | 84 | 72 | 12 | 32872 | 34267 | 92565 |
| (null/ATE) | 11 | 0 | 11 | 811 | 136850 | 188328 |
| nvcf_pexec | 9 | 8 | 1 | 99081 | 99082 | 151916 |

### 2.6 DB 6h 错误分类
| error_type | request_model | count |
|-------------------------|---------------|---|
| zombie_empty_completion | glm5_2_nv | 12 |
| all_tiers_exhausted | glm5_2_nv | 6 |
| all_tiers_exhausted | dsv4p_nv | 5 |
| NVStream_IncompleteRead | glm5_2_nv | 1 |

### 2.7 ms_gw 健康检查 (最近100行日志)
- 2 MS-OK-STREAM (1 dsv4p_v4k1 + 1 glm5.2_v1k2)
- 7 BrokenPipeError (code-level defect, not config-fixable)
- MS 成功率 ≈ 2/9 ≈ 22% (BrokenPipeError dominant)
- EMPTY_200_FASTBREAK_THRESHOLD=3 (already at optimal from R900)

### 2.8 Compose md5
`832ef9ff2d975396154a2880a8938908` — same as R1233

## 3. 决策分析

### 3.1 数据与R1233完全相同
- 104 req / 80 OK (76.9%) / 24 fail (identical)
- 12 zombie_empty_completion (NVCF content-filter, not config-fixable) — same count
- 11 all_tiers_exhausted (6 glm5_2_nv + 5 dsv4p_nv) — same count
- 1 NVStream_IncompleteRead — same count
- Compose md5 unchanged

### 3.2 所有参数已在 floor/optimal
- TIER_TIMEOUT_BUDGET_S=210 (R1231 raised from 198)
- TIER_COOLDOWN_S=15 (R1103 reverted from 18)
- KEY_COOLDOWN_S=25 (floor)
- MIN_OUTBOUND_INTERVAL_S=0 (floor)
- NVU_CONNECT_RESERVE_S=0 (floor)
- NVU_INTEGRATE_KEY_COOLDOWN_S=0 (floor)
- NVU_PEXEC_TIMEOUT_FASTBREAK=1 (function-level optimal)
- NVU_EMPTY_200_FASTBREAK=2 (code-level no-op — log always shows threshold=1)
- NVU_INTEGRATE_TIMEOUT_FASTBREAK=1 (function-level optimal)
- NVU_SSLEOF_RETRY_DELAY_S=1.0 (floor)
- KEY_AUTHFAIL_COOLDOWN_S=60 (optimal)
- NVU_TIER_BUDGET_DSV4P_NV=72 (optimal, R1116 from 66)
- NVU_TIER_BUDGET_GLM5_2_NV=96 (optimal)
- NVU_TIER_BUDGET_MINIMAX_M3_NV=100 (optimal)

### 3.3 失败分析 — 全部 code-level, 非 config-fixable
- **zombie_empty_completion (12)**: NVCF content-filter stop+12-36chars, input_chars ~157K avg. Gateway zombie detection + error-chunk correct. Not config-fixable.
- **all_tiers_exhausted (11)**: 6 glm5_2_nv IntegrateTimeout + 5 dsv4p_nv pexec timeout/empty_200 → ms_gw fallback → BrokenPipeError. ms_gw BrokenPipeError is code-level defect — relay sends 200+headers then breaks mid-stream, TCP half-corrupted, no recovery. Not config-fixable.
- **NVStream_IncompleteRead (1)**: NVCF premature stream close, code-level.

### 3.4 ms_gw — 无优化空间
- EMPTY_200_FASTBREAK_THRESHOLD=3 already at floor from R900
- BrokenPipeError dominant (7× in 100 log lines) — code-level defect
- MS-OK-STREAM rare (2 in 100 lines, ~22% SR)

## 4. 最终决策: NOP (零参数修改)

- **Zero param**: All parameters at floor/optimal.
- **Zero compose change**: Compose md5 unchanged from R1233.
- **Zero container restart**: No changes to deploy.
- **False trigger**: HM1 has not pushed new commits since R1206 (27 rounds behind). Same data as R1233.

## 5. 前轮数据链
R1233 (HM2's last round): 104req/80OK(76.9%)/24fail, 12 zombie, 11 ATE, 1 IncompleteRead. Identical.
R1232: 100req/77OK(77.0%)/23fail, 11 zombie, 11 ATE, 1 IncompleteRead. Similar.
R1231: TIER_TIMEOUT_BUDGET_S 198→210, 56/77 72.7%SR, 9 zombie, 11 ATE.

铁律:只改HM1不改HM2。0 param. NOP.

## ⏳ 轮到HM1优化HM2
