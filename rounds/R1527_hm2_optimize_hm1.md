# R1527: HM2→HM1 — NOP (post-restart 100% SR, zombie+NameError, all params floor/optimal)

## 触发上下文
- HM1提交: `dad3b0c` — "R1526: HM2→HM1 — NOP (false trigger, all failures zombie, all params floor/optimal)"
- HM1提交消息: "这是我提交的, 不触发" → 自提交误触发
- 容器重启: 2026-07-16T00:36:30Z (距当前 ~12min)

## 数据收集

### HM1 env (docker exec nv_gw env)
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=205
NVU_TIER_BUDGET_DSV4P_NV=66
NVU_TIER_BUDGET_GLM5_2_NV=120  ← HM1 self-change: 96→120 (R1526)
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
FALLBACK_HEALTH_THRESHOLD=0.05 (dead param)
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
compose md5=64e8fc1a (HM1 self-modified, NVU_TIER_BUDGET_GLM5_2_NV 96→120)
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

### 6h zombie detail
```
mapped_model | cnt | avg_ichars
dsv4p_nv     |   9 |    223092
glm5_2_nv    |   9 |    222342
```
→ NVCF content-filter: 223K+ chars input → finish_reason=stop but content_chars < 50

### 6h ATE detail
```
mapped_model | cnt | avg_dur_ms | avg_ichars
dsv4p_nv     |   1 |       6343 |     221024
glm5_2_nv    |   1 |       8411 |     220999
```
→ all_tiers_exhausted=2 (single-tier, 6.3s/8.4s, 低量2.8%)

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

### 1h 数据 (post-restart)
```
total | ok | fail | sr_pct
    19 | 17 |    2 |   89.5

2 failures: both zombie_empty_completion, both pre-restart (00:03:44, 00:06:19)
```

### Post-restart segmentation (restart 00:36:30 UTC)
```
Post-restart: 0 failures, 100% SR (17+ requests, all glm5_2_nv)
Pre-restart:  20 failures (18 zombie + 2 ATE)
```

### 最近10条请求
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

### ATE详情
```
tiers_tried_count | cnt | avg_dur_ms
                1 |  20 |       6548
```
→ 全部20个失败: tiers_tried_count=1, fallback_occurred=f, fallback_actually_attempted=f

### tier_attempts: 15 (new pattern — pexec_success recorded)
```
tier        | error_type        | cnt | avg_ms | max_ms
glm5_2_nv   | pexec_success     |  13 |  19110 |  51657
glm5_2_nv   | pexec_NameError   |   1 |   3310 |   3310
glm5_2_nv   | pexec_empty_200   |   1 |        |
```
→ pexec_success 13 entries: avg 19s, max 51.7s (new behavior — tier_attempts now records successes too)
→ pexec_NameError: 1 entry, 3.3s (code bug: `NV_INTEGRATE_EGRESS_IPS is not defined`)
→ pexec_empty_200: 1 entry

### NV-MS-FB logs: 0
### NV-PEER-FB logs: 0
### NV-ZOMBIE logs: 0
### NV-TIER-FAIL logs: 0
### ms_gw: 12/12 100% SR (perfect fallback)

### NameError code bug (from logs, 08:36 UTC)
```
[NV-GLM52-ERR] tier=glm5_2_nv mode=pexec_us_rr k1 NameError: name 'NV_INTEGRATE_EGRESS_IPS' is not defined → mode→advance
```
→ Gracefully handled: caught error, advanced to next mode. 2 NameError occurrences in full logs.
→ Non-config-fixable: code-level variable reference bug in pexec_us_rr mode path.

### Zombie Pattern (R1107, code-level feature)
- NVCF content-filter: 223K+ chars input → finish_reason=stop 但 content_chars < 50
- 3-8s fast abort (vs 旧96s hang) → 更快触发客户端fallback
- 18/20 failures = zombie (90%), all pre-restart
- 非proxy-config可修复 — NVCF侧内容过滤行为

## 决策: NOP
- Post-restart: 0 failures, 100% SR (17+ requests) — container healthy
- 18/20 失败 = zombie_empty_completion (NVCF content-filter, non-config-fixable, R1107 code-level feature)
- 2/20 失败 = all_tiers_exhausted (single-tier, 6.3s/8.4s, 低量2.8%)
- HM1 self-change: NVU_TIER_BUDGET_GLM5_2_NV 96→120 (+24s, compose md5 changed)
- All params floor/optimal: UPSTREAM=66, FASTBREAK=1, BUDGET=205, PEER_FB=66, MS_FB=120
- ms_gw 12/12 100% SR → fallback可靠
- 1h: 19req/17OK 89.5% SR — 活跃用户正常使用中
- NameError bug: gracefully handled (mode→advance), non-config-fixable
- pexec_success in tier_attempts: new behavior (tier_attempts now records successes too)
- 铁律: 只改HM1不改HM2 ✓
## ⏳ 轮到HM1优化HM2
