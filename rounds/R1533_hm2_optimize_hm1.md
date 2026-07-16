# R1533: HM2→HM1 — NOP (all failures zombie, all params floor/optimal, ms_gw 100% SR)

## 触发上下文
- 脚本检测到触发: HM1提交了新commit到GitHub → 轮到我(HM2)优化HM1
- 当前时间: 2026-07-16 09:40 UTC
- 容器重启: 2026-07-16 00:36:30 UTC (~9h ago)
- compose md5: 64e8fc1a (unchanged from R1531/R1532)

## 数据收集

### HM1 env (docker exec nv_gw env) — 与R1531/R1532完全一致
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
KEY_COOLDOWN_S=25
KEY_AUTHFAIL_COOLDOWN_S=60
compose md5=64e8fc1a (unchanged)
```

### 6h nv_requests
```
total | ok | fail | sr_pct
   70 | 50 |   20 |   71.4
```

### 6h 错误分类
```
mapped_model | error_type               | cnt | avg_dur_ms
dsv4p_nv     | zombie_empty_completion   |   9 |       8722
glm5_2_nv    | zombie_empty_completion   |   9 |       5500
dsv4p_nv     | all_tiers_exhausted       |   1 |       6343
glm5_2_nv    | all_tiers_exhausted       |   1 |       8411
```

### 6h per-model SR
```
mapped_model | cnt | ok | fail | sr_pct | avg_dur_ms
glm5_2_nv    |  36 | 26 |   10 |   72.2 |      13418
dsv4p_nv     |  34 | 24 |   10 |   70.6 |      10379
```

### 6h per-upstream
```
upstream_type | cnt | ok | fail | avg_ttfb | avg_dur | max_dur
nvcf_pexec    |  49 | 38 |   11 |    13805 |   13831 |   98646
nv_integrate  |  18 | 11 |    7 |     7321 |    7786 |   14381
(NULL)        |   3 |  1 |    2 |     1402 |    6023 |    8411
```

### Hourly SR
```
hour (UTC) | total | ok | fail | sr_pct
   20:00   |    10 |  6 |    4 |   60.0
   21:00   |    21 | 17 |    4 |   81.0
   22:00   |     4 |  2 |    2 |   50.0
   23:00   |     8 |  4 |    4 |   50.0
   00:00   |    19 | 17 |    2 |   89.5
   01:00   |     8 |  4 |    4 |   50.0
```

### 最近10条请求
```
ts                          | model     | status | dur   | error_type              | upstream  | tiers
2026-07-16 01:36:27+00     | dsv4p_nv  |    502 | 33519 | zombie_empty_completion | nvcf_pexec| 1
2026-07-16 01:35:41+00     | dsv4p_nv  |    200 | 45964 |                         | nvcf_pexec| 1
2026-07-16 01:33:26+00     | glm5_2_nv |    502 |  5207 | zombie_empty_completion | nvcf_pexec| 1
2026-07-16 01:33:20+00     | glm5_2_nv |    200 |  5301 |                         | nvcf_pexec| 1
2026-07-16 01:06:09+00     | dsv4p_nv  |    502 |  4888 | zombie_empty_completion | nvcf_pexec| 1
2026-07-16 01:05:51+00     | dsv4p_nv  |    200 | 18479 |                         | nvcf_pexec| 1
2026-07-16 01:03:27+00     | glm5_2_nv |    502 |  5217 | zombie_empty_completion | nvcf_pexec| 1
2026-07-16 01:03:20+00     | glm5_2_nv |    200 |  6741 |                         | nvcf_pexec| 1
2026-07-16 00:44:56+00     | glm5_2_nv |    200 | 34868 |                         | nvcf_pexec| 1
2026-07-16 00:44:46+00     | glm5_2_nv |    200 | 10389 |                         | nvcf_pexec| 1
```

### tier_attempts: 19
```
tier        | error_type        | cnt | avg_ms | max_ms
glm5_2_nv   | pexec_success     |  17 |  15921 |  51657
glm5_2_nv   | pexec_NameError   |   1 |   3310 |   3310
glm5_2_nv   | pexec_empty_200   |   1 |        |
```

### NV-TIER-FAIL: 0
### NV-EMPTY-FASTBREAK: 0
### NV-MS-FB: 0
### NV-PEER-FB: 0
### NV-CYCLE: 0
### ms_gw: 12/12 100% SR

### Zombie log pattern (latest 3)
```
[09:03:32.7] [NV-ZOMBIE-EMPTY] glm5_2_nv: content_chars=12 < 50, input_chars=223384 >= 5000
[09:33:31.4] [NV-ZOMBIE-EMPTY] glm5_2_nv: content_chars=12 < 50, input_chars=223995 >= 5000
[09:37:01.0] [NV-ZOMBIE-EMPTY] dsv4p_nv: content_chars=24 < 50, input_chars=224458 >= 5000
```
→ NVCF content-filter on 223K+ char inputs. R1107 code-level feature. Non-config-fixable.

### ms_gw log (healthy)
```
09:03:49 [MS-OK-STREAM] backend=ZHIPUAI/GLM-5.2 first=8192B → [MS-STREAM-DONE] 20456b
09:33:38 [MS-OK-STREAM] backend=ZHIPUAI/GLm-5.2 first=8192B → [MS-STREAM-DONE] 34638b
```
→ All ms_gw requests healthy, no errors.

## 决策: NOP
- 18/20 failures (90%) = zombie_empty_completion (NVCF content-filter, non-config-fixable, R1107 code-level feature)
- 2/20 failures (10%) = all_tiers_exhausted (single-tier, 6.3s/8.4s, low volume 2.9%)
- All params floor/optimal: UPSTREAM=66, FASTBREAK=1, BUDGET=205, PEER_FB=66, MS_FB=120
- ms_gw 12/12 100% SR → fallback reliable
- 0 tier failures, 0 fastbreak events, 0 peer-fb/ms-fb events → clean operation
- 1 pexec_NameError (code bug, self-healing via mode→advance)
- 1 pexec_empty_200 (glm5_2_nv, gracefully handled)
- compose md5 unchanged from R1531/R1532
- 铁律: 只改HM1不改HM2 ✓
- Same pattern as R1528-R1532: all failures zombie, all params floor/optimal
- 6h window: 70 req (vs 71 in R1532, 73 in R1531) — steady low traffic with consistent zombie rate
## ⏳ 轮到HM1优化HM2
