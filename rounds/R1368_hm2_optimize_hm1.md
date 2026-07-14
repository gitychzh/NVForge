# HM2 Optimize HM1 — Round R1368

## 触发分析
- Cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit: c78b295 (R1367, opc2_uname HM2)
- 判定: 误触发 / double-dispatch (528th chain of R1133)
- HM1 git log 仍落后 (长期未自提交, 最新 R1206 3天前), HM1 无新 commit

## 数据收集 (改前必有数据)

### DB (6h window)
```
6h_overall:  29req / 21OK / 8fail = 72.4% SR
6h_by_error: zombie_empty_completion × 8 (only error type)
6h_by_model: glm5_2_nv 29req (21OK/8fail), avg_dur=9860ms
6h_fallback: 0 fallback occurred
tier_attempts: 0
ms_gw: 0/0 (no traffic)
zombie_detail: glm5_2_nv zombie_empty_completion ×8, avg_ichars=190267, avg_dur=9693ms, avg_out_tok=10
ate_detail: 0
6h_tiers_tried: all 29 = tiers_tried_count=1
```

### 6h Hourly SR
```
09:00  4/5   80.0%
10:00  3/4   75.0%
11:00  4/5   80.0%
12:00  2/4   50.0%
13:00  4/6   66.7%
14:00  4/5   80.0%
```

### 24h Window (broad context)
```
24h_overall: 235req / 191OK / 44fail = 81.3% SR
24h_by_error: zombie_empty_completion ×34, all_tiers_exhausted ×9, NVStream_IncompleteRead ×1
24h_ate: dsv4p_nv ×9, ~72s (UPSTREAM_TIMEOUT=66 + ~6s overhead), input_chars 57K-244K, tiers_tried=1, all 05:00-06:00 UTC (outside current 6h window)
24h_dsv4p: 05:00 1/1(0%), 06:00 53/48(90.6%), 13:18: 13/10(76.9%)
```

### Recent 10 requests
All glm5_2_nv integrate. 3 zombie (502, content_chars=6-21, ~190K input) + 7 OK (200, 42-77 output_tokens, 6.6-14.7s). Zombie pattern: content_chars=6-42, total_input_chars=~190K, finish_reason=stop, content_filter error chunk via NV-ZOMBIE-EMPTY detection.

### Container Logs (nv_gw --tail 200)
- NV-ZOMBIE-EMPTY × 5: content_chars=12/41/42 (all <50), input_chars 190K-195K
- NV-ZOMBIE-ERROR-CHUNK: content_filter SSE sent to trigger openclaw fallback
- NV-INTEGRATE-ERR × 1: k2 SSLEOFError (SSL UNEXPECTED_EOF, 5002ms, cycle to k3 = success)
- All NV-REQ: glm5_2_nv, tier_chain=['glm5_2_nv'], no fallback, 3model
- All NV-INTEGRATE-SUCCESS: first-attempt, 3-12s

### Container Env (nv_gw)
```
UPSTREAM_TIMEOUT=66
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
TIER_TIMEOUT_BUDGET_S=205
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_DSV4P_NV=94
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_EMPTY_200_FASTBREAK=2
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006
NVU_PEER_FB_SKIP_MODELS=
NVU_MS_GW_FALLBACK_TIMEOUT=195
NVU_STREAM_FIRST_BYTE_DEADLINE_S=20
NVU_STREAM_TOTAL_DEADLINE_S=42
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
MIN_OUTBOUND_INTERVAL_S=0
NVU_CONNECT_RESERVE_S=0
```

### Container Status
- nv_gw: Up 11h 9m (healthy, started 2026-07-14T11:29:07Z)
- Health: {"status":"ok","proxy_role":"passthrough","nv_num_keys":5}
- Compose md5: b367c647a8d42d9d86ed8814234a1d19 (unchanged from R1367)

## 决策: NOP

### 零可修故障
- 8/8 failures = zombie_empty_completion (glm5_2_nv integrate, NVCF content-filter stop, 6-42 chars output, ~190K input)
- 0 ATE, 0 timeout, 0 empty_200, 0 tier_attempts, 0 fallback
- 0 dsv4p_nv / 0 kimi_nv / 0 minimax_m3_nv traffic
- ms_gw 0/0
- All params floor/optimal — no config-fixable issue
- Zombie = code-level NVCF content-filter behavior (NV-ZOMBIE-EMPTY detection working correctly, 6-16s abort vs old 96s timeout)
- 528th consecutive chain of R1133 false trigger
- 24h ATE (9× dsv4p_nv ~72s) is outside the 6h window (05:00-06:00 UTC), container was up at the time, UPSTREAM_TIMEOUT=66 + ~6s overhead, but these are 6h+ old and not actionable

### 铁律遵守
- 只改HM1不改HM2: ✓ (本轮无任何配置变更)
- 改前必有数据: ✓ (DB + logs + env 收集完毕)
- 所有参数 floor/optimal: ✓

## ⏳ 轮到HM1优化HM2