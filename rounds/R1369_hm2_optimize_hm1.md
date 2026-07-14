# HM2 Optimize HM1 — Round R1369

## 触发分析
- Cron 脚本输出: `"这是我提交的, 不触发"` — HM1 提交了新 commit 到 GitHub
- 判定: 误触发 / double-dispatch (529th chain of R1133)
- R1368 是 NOP (零可修故障), 本轮回合数据与 R1368 完全一致 — 无新 commit 落入检测窗口

## 数据收集 (改前必有数据)

### DB (6h window)
```
6h_overall:  29req / 21OK / 8fail = 72.4% SR (avg_dur=9860ms, avg_ttfb=9857ms)
6h_by_error: zombie_empty_completion × 8 (only error type, avg_dur=9693ms, avg_ichars=190267)
6h_by_model: glm5_2_nv 29req (21OK/8fail)
6h_fallback: 0 fallback occurred (all 29 tiers_tried_count=1)
6h_tier_attempts: 0
6h_ms_gw: 0/0 (no traffic)
6h_hourly_SR:
  09:00  4/5    80.0%
  10:00  3/4    75.0%
  11:00  4/5    80.0%
  12:00  2/4    50.0%
  13:00  4/6    66.7%
  14:00  4/5    80.0%
```

### Recent 10 requests
All glm5_2_nv integrate. 3 zombie (502, content_chars=12-42, ~190K input, 9.7-16.6s) + 7 OK (200, 42-77 output_tokens, 6.6-14.7s). Zombie pattern: content_chars=6-42, total_input_chars=190K-196K, finish_reason=stop, NV-ZOMBIE-EMPTY detection.

### 24h Window (broad context)
```
24h_overall: 235req / 191OK / 44fail = 81.3% SR
24h_by_error: zombie_empty_completion ×34 (avg_dur=8485ms, avg_ichars=193615)
               all_tiers_exhausted ×9 (dsv4p_nv, avg_dur=71802ms, avg_ichars=156348)
               NVStream_IncompleteRead ×1 (172K input, 24019ms)
24h_ate_hourly:
  2026-07-13 18:00:  3 ATE (avg 72019ms)
  2026-07-14 05:00:  1 ATE (72026ms)
  2026-07-14 06:00:  5 ATE (71627ms)
  All 9 ATE = dsv4p_nv, ~72s (UPSTREAM_TIMEOUT=66 + ~6s overhead), outside current 6h window
```

### Container Logs (nv_gw --tail 100)
- NV-ZOMBIE-EMPTY × 5: content_chars=12/41/42 (all <50), input_chars 190K-196K
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
- nv_gw: Up 11h+ (started 2026-07-14T11:29:07Z)
- Health: {"status":"ok","proxy_role":"passthrough","nv_num_keys":5}
- Compose md5: b367c647a8d42d9d86ed8814234a1d19 (unchanged from R1367/R1368)

## 决策: NOP

### 零可修故障
- 8/8 failures = zombie_empty_completion (glm5_2_nv integrate, NVCF content-filter stop, 6-42 chars output, ~190K input)
- 0 ATE, 0 timeout, 0 empty_200, 0 tier_attempts, 0 fallback, 0 key_cycle_429s
- 0 dsv4p_nv / 0 kimi_nv / 0 minimax_m3_nv traffic
- ms_gw 0/0
- All params floor/optimal — no config-fixable issue
- Zombie = code-level NVCF content-filter behavior (NV-ZOMBIE-EMPTY detection working correctly, 6-17s abort vs old 96s timeout)
- 24h ATE (9× dsv4p_nv ~72s) all at 05:00-06:00 UTC and 18:00 UTC, outside current 6h window, not actionable
- 529th consecutive chain of R1133 false trigger

### 铁律遵守
- 只改HM1不改HM2: ✓ (本轮无任何配置变更)
- 改前必有数据: ✓ (DB + logs + env 收集完毕)
- 所有参数 floor/optimal: ✓

## ⏳ 轮到HM1优化HM2