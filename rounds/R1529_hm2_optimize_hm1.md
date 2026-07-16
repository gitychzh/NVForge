# R1529: HM2→HM1 — NOP (post-restart 100% SR, all failures zombie, all params floor/optimal)

## 触发上下文
- 脚本检测到触发: HM1提交了R1528 commit → 轮到我(HM2)优化HM1
- 但"这是我提交的, 不触发" → 实际是false trigger (HM2的R1528被误判)
- 当前时间: 2026-07-16 09:00 UTC
- 距上次重启: ~8.5h (重启 00:36:30 UTC)

## 数据收集

### HM1 env (docker exec nv_gw env) — 与R1528完全一致
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=205
NVU_TIER_BUDGET_DSV4P_NV=66
NVU_TIER_BUDGET_GLM5_2_NV=120
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006
NVU_PEER_FB_SKIP_MODELS=
NVU_MS_GW_FALLBACK_TIMEOUT=120
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_CONNECT_RESERVE_S=0
MIN_OUTBOUND_INTERVAL_S=0
KEY_COOLDOWN_S=25
KEY_AUTHFAIL_COOLDOWN_S=60
TIER_COOLDOWN_S=15
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_STREAM_FIRST_BYTE_DEADLINE_S=20
NVU_STREAM_TOTAL_DEADLINE_S=42
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
compose md5=64e8fc1a (unchanged)
```

### 6h nv_requests
```
total | ok | fail | sr_pct
    71 | 51 |   20 |   71.8
```

### 6h 错误分类
```
mapped_model | error_type               | cnt | avg_dur_ms
dsv4p_nv     | zombie_empty_completion   |   9 |       5067
glm5_2_nv    | zombie_empty_completion   |   9 |       7846
dsv4p_nv     | all_tiers_exhausted       |   1 |       6343
glm5_2_nv    | all_tiers_exhausted       |   1 |       8411
```

### 6h per-model SR
```
mapped_model | cnt | ok | fail | sr_pct | avg_dur_ms
glm5_2_nv    |  36 | 26 |   10 |   72.2 |      14643
dsv4p_nv     |  35 | 25 |   10 |   71.4 |       8350
```

### Hourly SR
```
hour (UTC) | total | ok | fail | sr_pct
   19:00   |     9 |  5 |    4 |   55.6
   20:00   |    10 |  6 |    4 |   60.0
   21:00   |    21 | 17 |    4 |   81.0
   22:00   |     4 |  2 |    2 |   50.0
   23:00   |     8 |  4 |    4 |   50.0
   00:00   |    19 | 17 |    2 |   89.5
```

### Post-restart (00:36:30 UTC 后)
```
12 requests, ALL glm5_2_nv, ALL 200 → 100% SR
No dsv4p_nv traffic in post-restart window
```

### 最近10条请求 (post-restart)
```
ts                          | model     | status | dur   | error_type | tiers_tried
2026-07-16 00:45:31+00     | glm5_2_nv |    200 | 34868 |            | 1
2026-07-16 00:44:56+00     | glm5_2_nv |    200 | 10389 |            | 1
2026-07-16 00:44:46+00     | glm5_2_nv |    200 |  6439 |            | 1
2026-07-16 00:44:39+00     | glm5_2_nv |    200 |  2143 |            | 1
2026-07-16 00:44:37+00     | glm5_2_nv |    200 |  6108 |            | 1
2026-07-16 00:44:31+00     | glm5_2_nv |    200 |  5880 |            | 1
2026-07-16 00:44:06+00     | glm5_2_nv |    200 | 52114 |            | 1
2026-07-16 00:42:20+00     | glm5_2_nv |    200 | 33247 |            | 1
2026-07-16 00:39:14+00     | glm5_2_nv |    200 | 98646 | fallback_actually_attempted=t | 1
2026-07-16 00:39:08+00     | glm5_2_nv |    200 | 44913 |            | 1
```

### tier_attempts: 15
```
tier        | error_type        | cnt | avg_ms | max_ms
glm5_2_nv   | pexec_success     |  13 |  19110 |  51657
glm5_2_nv   | pexec_NameError   |   1 |   3310 |   3310
glm5_2_nv   | pexec_empty_200   |   1 |        |
```

### NV-PEER-FB: 0
### NV-MS-FB: 0
### NV-TIER-FAIL: 0
### NV-ZOMBIE: 0
### NV-CYCLE-504: 0
### ms_gw: 12/12 100% SR

### NameError code bugs (from logs)
```
[08:35:59.4] NameError: name '_glm52_rr_us_lock' is not defined  ← NEW
[08:36:02.8] [NV-GLM52-ERR] NameError: name 'NV_INTEGRATE_EGRESS_IPS' is not defined → mode→advance
```
→ Both gracefully handled: caught error, advanced to next mode. Non-config-fixable.

### empty_200 on glm5_2_nv k2 (gracefully salvaged)
```
[08:38:38.0] [NV-EMPTY-200] k2 (glm5_2_nv) → 200 Content-Length:0 (stream)
[08:38:38.0] [NV-GLM52-EMPTY] tier=glm5_2_nv mode=pexec_us_rr k2 empty 200, cooling, mode→advance
[08:38:38.0] [NV-GLM52-ATTEMPT] tier=glm5_2_nv k3 channel=pexec → SUCCESS 30s later
```

### Zombie Pattern (R1107, code-level feature)
- NVCF content-filter: 223K+ chars input → finish_reason=stop but content_chars < 50
- 3-8s fast abort (vs old 96s hang)
- 18/20 failures = zombie (90%), all pre-restart
- 非proxy-config可修复

## 决策: NOP
- Post-restart: 12/12 100% SR (all glm5_2_nv, no dsv4p_nv traffic) — container healthy
- 18/20 failures = zombie_empty_completion (NVCF content-filter, non-config-fixable, R1107 code-level feature)
- 2/20 failures = all_tiers_exhausted (single-tier, 6.3s/8.4s, low volume 2.8%)
- All params floor/optimal: UPSTREAM=66, FASTBREAK=1, BUDGET=205, PEER_FB=66, MS_FB=120
- ms_gw 12/12 100% SR → fallback reliable
- 1 empty_200 on glm5_2_nv salvaged by k3 (graceful)
- 2 NameError bugs: _glm52_rr_us_lock (new) + NV_INTEGRATE_EGRESS_IPS (known), both gracefully handled
- compose md5 unchanged from R1528
- 铁律: 只改HM1不改HM2 ✓
- No dsv4p_nv traffic in current window — all post-restart requests are glm5_2_nv only
- 6h window stale (same 71 requests as R1528, no new data since ~8.5h ago)
- False trigger: 脚本检测到"轮到我"是因HM2自己的R1528 commit被误判为HM1新提交
## ⏳ 轮到HM1优化HM2
