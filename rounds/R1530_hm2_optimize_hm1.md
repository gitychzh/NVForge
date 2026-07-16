# R1530: HM2→HM1 — NOP (all failures zombie, all params floor/optimal, ms_gw 100% SR)

## 触发上下文
- 脚本检测到触发: HM1提交了R1529 commit → 轮到我(HM2)优化HM1
- 但"这是我提交的, 不触发" → 实际是false trigger (HM2的R1529被误判为HM1新提交)
- 当前时间: 2026-07-16 09:05 UTC
- 容器重启: 2026-07-16 00:36:30 UTC (8.5h ago)
- compose md5: 64e8fc1a (unchanged from R1529)

## 数据收集

### HM1 env (docker exec nv_gw env) — 与R1529完全一致
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
   73 | 52 |   21 |   71.2
```

### 6h 错误分类
```
mapped_model | error_type               | cnt | avg_dur_ms
dsv4p_nv     | zombie_empty_completion   |  10 |       5049
glm5_2_nv    | zombie_empty_completion   |   9 |       5637
dsv4p_nv     | all_tiers_exhausted       |   1 |       6343
glm5_2_nv    | all_tiers_exhausted       |   1 |       8411
```

### 6h per-model SR
```
mapped_model | cnt | ok | fail | sr_pct | avg_dur_ms
dsv4p_nv     |  37 | 26 |   11 |   70.3 |       8530
glm5_2_nv    |  36 | 26 |   10 |   72.2 |      13494
```

### 6h per-upstream
```
upstream_type | cnt | ok | fail | avg_ttfb | avg_dur | max_dur
nvcf_pexec    |  50 | 39 |   11 |    12573 |   12599 |   98646
nv_integrate  |  20 | 12 |    8 |     7251 |    7670 |   14381
(NULL)        |   3 |  1 |    2 |     1402 |    6023 |    8411
```

### Hourly SR
```
hour (UTC) | total | ok | fail | sr_pct
   19:00   |     7 |  4 |    3 |   57.1
   20:00   |    10 |  6 |    4 |   60.0
   21:00   |    21 | 17 |    4 |   81.0
   22:00   |     4 |  2 |    2 |   50.0
   23:00   |     8 |  4 |    4 |   50.0
   00:00   |    19 | 17 |    2 |   89.5
   01:00   |     4 |  2 |    2 |   50.0
```

### 最近10条请求
```
ts                          | model     | status | dur   | error_type                    | upstream  | tiers
2026-07-16 01:06:14+00     | dsv4p_nv  |    502 |  4888 | zombie_empty_completion       | nvcf_pexec| 1
2026-07-16 01:06:09+00     | dsv4p_nv  |    200 | 18479 |                               | nvcf_pexec| 1
2026-07-16 01:03:32+00     | glm5_2_nv |    502 |  5217 | zombie_empty_completion       | nvcf_pexec| 1
2026-07-16 01:03:27+00     | glm5_2_nv |    200 |  6741 |                               | nvcf_pexec| 1
2026-07-16 00:45:31+00     | glm5_2_nv |    200 | 34868 |                               | nvcf_pexec| 1
2026-07-16 00:44:56+00     | glm5_2_nv |    200 | 10389 |                               | nvcf_pexec| 1
2026-07-16 00:44:46+00     | glm5_2_nv |    200 |  6439 |                               | nvcf_pexec| 1
2026-07-16 00:44:39+00     | glm5_2_nv |    200 |  2143 |                               | nvcf_pexec| 1
2026-07-16 00:44:37+00     | glm5_2_nv |    200 |  6108 |                               | nvcf_pexec| 1
2026-07-16 00:44:31+00     | glm5_2_nv |    200 |  5880 |                               | nvcf_pexec| 1
```

### tier_attempts: 17
```
tier        | error_type        | cnt | avg_ms | max_ms
glm5_2_nv   | pexec_success     |  15 |  17345 |  51657
glm5_2_nv   | pexec_NameError   |   1 |   3310 |   3310
glm5_2_nv   | pexec_empty_200   |   1 |        |
```

### NV-PEER-FB: 0
### NV-MS-FB: 0
### NV-TIER-FAIL: 0
### NV-EMPTY-FASTBREAK: 0
### NV-CYCLE-504: 0
### ms_gw: 12/12 100% SR

### NameError code bugs (from logs)
```
NameError: name '_glm52_rr_us_lock' is not defined          ← NEW (R1529)
[08:36:02.8] [NV-GLM52-ERR] NameError: name 'NV_INTEGRATE_EGRESS_IPS' is not defined → mode→advance
```
→ Both gracefully handled: caught error, advanced to next mode. Non-config-fixable.

### empty_200 on glm5_2_nv k2 (gracefully salvaged)
```
[08:38:38.0] [NV-EMPTY-200] k2 (glm5_2_nv) → 200 Content-Length:0 (stream)
[08:38:38.0] [NV-GLM52-EMPTY] tier=glm5_2_nv mode=pexec_us_rr k2 empty 200, cooling, mode→advance
[08:38:38.0] [NV-GLM52-ATTEMPT] tier=glm5_2_nv k3 channel=pexec → continued
```
→ empty_200 on k2 gracefully handled by mode→advance to k3. No tier failure.

### Post-restart zombie (2 new)
```
[09:03:32.7] [NV-ZOMBIE-EMPTY] glm5_2_nv: content_chars=12 < 50, input_chars=223384 >= 5000
[09:06:14.5] [NV-ZOMBIE-EMPTY] dsv4p_nv: content_chars=48 < 50, input_chars=224013 >= 5000
```
→ New zombie in 01:00 hour (post-restart). NVCF content-filter on 223K+ char inputs. R1107 code-level feature.

### Zombie Pattern (R1107)
- NVCF content-filter: 223K+ chars input → finish_reason=stop but content_chars < 50
- 3-8s fast abort (vs old 96s hang)
- 19/21 failures = zombie (90.5%), all NVCF content-filter
- 非proxy-config可修复

## 决策: NOP
- 19/21 failures = zombie_empty_completion (NVCF content-filter, non-config-fixable, R1107 code-level feature)
- 2/21 failures = all_tiers_exhausted (single-tier, 6.3s/8.4s, low volume 2.7%)
- All params floor/optimal: UPSTREAM=66, FASTBREAK=1, BUDGET=205, PEER_FB=66, MS_FB=120
- ms_gw 12/12 100% SR → fallback reliable
- 1 empty_200 on glm5_2_nv salvaged by k3 (graceful)
- 2 NameError bugs: _glm52_rr_us_lock (new) + NV_INTEGRATE_EGRESS_IPS (known), both gracefully handled
- compose md5 unchanged from R1529
- 铁律: 只改HM1不改HM2 ✓
- Same pattern as R1528-R1529: all failures zombie, all params floor/optimal
- False trigger: 脚本检测到"轮到我"是因HM2自己的R1529 commit被误判为HM1新提交
- 6h window: 73→73 (same as R1529, only 2 new requests in 01:00 hour)
## ⏳ 轮到HM1优化HM2