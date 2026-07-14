# HM2 Optimize HM1 — Round R1367

## 触发分析
- Cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit: 91ca6cd (R1366, opc2_uname HM2)
- 判定: 误触发 / double-dispatch (527th chain of R1133)
- HM1 git log 仍落后 (长期未自提交), HM1 无新 commit

## 数据收集 (改前必有数据)

### DB (6h window)
```
6h_overall:  30req / 23OK / 7fail = 76.7% SR
6h_by_error: zombie_empty_completion × 7 (only error type)
6h_by_model: glm5_2_nv 30req (23OK/7fail), avg_dur=9550ms
6h_fallback: 0 fallback occurred
tier_attempts: 0
ms_gw: 0/0 (no traffic)
zombie_detail: glm5_2_nv zombie_empty_completion ×7, avg_ichars=189491, avg_dur=8710ms
ate_detail: 0
6h_tiers_tried: all 7 failures = tiers_tried_count=1
```

### 6h Hourly SR
```
08:00  3/3   100.0%
09:00  4/5   80.0%
10:00  3/4   75.0%
11:00  4/5   80.0%
12:00  2/4   50.0%
13:00  4/6   66.7%
14:00  3/3   100.0%
```

### Recent 10 requests
All glm5_2_nv. 3 zombie (502, 6-42 output_chars, ~190K input) + 7 OK (200, 42-77 output_tokens, 6.6-14.7s). Zombie pattern: content_chars=6-42, total_input_chars=~190K, finish_reason=stop, content_filter error chunk via NV-ZOMBIE-EMPTY detection.

### Container Logs (nv_gw --tail 100)
- NV-ZOMBIE-EMPTY × 3: content_chars=12/42/41 (all <50), input_chars 190K+
- NV-ZOMBIE-ERROR-CHUNK: content_filter SSE sent to trigger openclaw fallback
- NV-INTEGRATE-ERR × 1: k2 SSLEOFError (SSL UNEXPECTED_EOF, 5002ms, cycle)
- All NV-REQ: glm5_2_nv, tier_chain=['glm5_2_nv'], no fallback, 3model

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
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006
NVU_PEER_FB_SKIP_MODELS=
MIN_OUTBOUND_INTERVAL_S=0
```

### Container Status
- nv_gw: Up 3 hours (healthy)
- Compose md5: b367c647a8d42d9d86ed8814234a1d19 (unchanged from R1366)

## 决策: NOP

### 零可修故障
- 7/7 failures = zombie_empty_completion (glm5_2_nv integrate, NVCF content-filter stop, 6-42 chars output, ~190K input)
- 0 ATE, 0 timeout, 0 empty_200, 0 tier_attempts, 0 fallback
- 0 dsv4p_nv / 0 kimi_nv / 0 minimax_m3_nv traffic
- ms_gw 0/0
- All params floor/optimal — no config-fixable issue
- Zombie = code-level NVCF content-filter behavior (NV-ZOMBIE-EMPTY detection working correctly, 6-15s abort vs old 96s timeout)
- 527th consecutive chain of R1133 false trigger

### 铁律遵守
- 只改HM1不改HM2: ✓ (本轮无任何配置变更)
- 改前必有数据: ✓ (DB + logs + env 收集完毕)
- 所有参数 floor/optimal: ✓

## ⏳ 轮到HM1优化HM2
