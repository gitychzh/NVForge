# R1524: HM2→HM1 — NOP (false trigger, zero post-restart ATEs, all params floor/optimal)

## 触发上下文
- HM1提交: `69f3e11` — "R1523: HM2→HM1 — NOP (false trigger, zero post-restart ATEs, all params floor/optimal)"
- HM1提交消息: "这是我提交的, 不触发" — 自提交误触发
- 容器重启: 2026-07-15T22:25:46Z (距当前 ~10h)

## 数据收集

### HM1 env (docker exec nv_gw env)
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=205
NVU_TIER_BUDGET_DSV4P_NV=66
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006
NVU_PEER_FB_SKIP_MODELS=
NVU_MS_GW_FALLBACK_TIMEOUT=120
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_CONNECT_RESERVE_S=0
MIN_OUTBOUND_INTERVAL_S=0
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=15
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_STREAM_FIRST_BYTE_DEADLINE_S=20
NVU_STREAM_TOTAL_DEADLINE_S=42
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NV_INTEGRATE_MODELS=glm5_2_nv
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
compose md5=9fb97661 (不变)
```

### 6h nv_requests
```
total | ok | fail | sr_pct
    66 | 42 |   24 |   63.6
```

### 6h 错误分类
```
error_type               | cnt
zombie_empty_completion   |  21
all_tiers_exhausted      |   3
```

### Post-Restart (22:25Z→now)
```
total | ok | fail | sr_pct
    15 |  9 |    6 |   60.0
```
→ 6 post-restart failures: 全部 zombie_empty_completion, 0 ATE

### 6h per-model
```
mapped_model | cnt | ok | fail | avg_dur_ms | avg_ttfb_ms
dsv4p_nv     |  40 | 28 |   12 |      10429 |        8766
glm5_2_nv    |  26 | 14 |   12 |       8994 |        8369
```

### 6h per-upstream
```
upstream_type | cnt | ok | avg_ttfb | avg_dur | max_dur
nvcf_pexec    |  38 | 28 |     9200 |    9201 |   21543
nv_integrate  |  25 | 14 |     8682 |    9017 |   28193
(NULL/ATE)    |   3 |  0 |      533 |   25310 |   61177
```

### ATE详情 (全6h)
```
ts                          | model    | ttfb | dur   | tiers_tried | fb_attempted
2026-07-15 22:07:44+00     | dsv4p_nv |  339 |  6343 |           1 | f
2026-07-15 22:03:20+00     | glm5_2_nv|  551 |  8411 |           1 | f
```
→ 2 ATE均为pre-restart (22:03, 22:07), 容器于22:25重启。Post-restart: 0 ATE

### 最近10条请求
```
ts                          | model    | status | ttfb  | dur   | error_type              | upstream
2026-07-16 00:06:11+00     | dsv4p_nv |    502 |  7582 |  7583 | zombie_empty_completion | nvcf_pexec
2026-07-16 00:05:52+00     | dsv4p_nv |    200 | 19537 | 19538 |                         | nvcf_pexec
2026-07-16 00:03:39+00     | glm5_2_nv|    502 |  5412 |  5413 | zombie_empty_completion | nv_integrate
2026-07-16 00:03:26+00     | glm5_2_nv|    200 |  4447 | 12815 |                         | nv_integrate
2026-07-16 00:03:20+00     | glm5_2_nv|    200 |  5359 |  5360 |                         | nv_integrate
```

### tier_attempts: 0 (clean key pool)
### NV-TIER-FAIL logs: 0 (no key cycling)
### ms_gw: 14/14 100% SR (perfect fallback)

## Zombie Pattern
- NVCF content-filter: 大输入(223K+ chars) → finish_reason=stop 但 content_chars < 50
- Gateway检测: `[NV-ZOMBIE-EMPTY]` → 发送 `finish_reason=timeout` error chunk 触发客户端fallback
- 非proxy-config可修复 — NVCF侧内容过滤行为

## 决策: NOP
- 0 post-restart ATE → 无需调整
- 21 zombie = NVCF content-filter, 非config-fixable
- 所有参数已是floor/optimal (compose md5=9fb97661, 与R1523一致)
- ms_gw 14/14 100% SR → fallback可靠
- 0 tier_attempts → key pool clean
- 铁律: 只改HM1不改HM2 ✓
## ⏳ 轮到HM1优化HM2
