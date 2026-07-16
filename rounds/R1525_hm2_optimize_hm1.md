# R1525: HM2→HM1 — NOP (false trigger, all failures zombie, all params floor/optimal)

## 触发上下文
- HM1提交: `0a20b05` — "R1524: HM2→HM1 — NOP (false trigger, zero post-restart ATEs, all params floor/optimal). 6h: 66req/42OK 63.6%SR. 21 zombie (NVCF content-filter). 2 ATE (pre-restart). 0 tier_attempts. ms_gw 14/14 100%SR."
- HM1提交消息: "这是我提交的, 不触发" → 自提交误触发
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
compose md5=9fb97661 (不变)
```

### 6h nv_requests
```
total | ok | fail | sr_pct
    61 | 40 |   21 |   65.6
```

### 6h 错误分类
```
mapped_model | error_type               | cnt | avg_dur_ms
glm5_2_nv    | zombie_empty_completion   |  10 |       7699
dsv4p_nv     | zombie_empty_completion   |   9 |       5067
dsv4p_nv     | all_tiers_exhausted       |   1 |       6343
glm5_2_nv    | all_tiers_exhausted       |   1 |       8411
```

### 6h per-model SR
```
mapped_model | cnt | ok | fail | sr_pct | avg_dur_ms
dsv4p_nv     |  37 | 27 |   10 |   73.0 |       8557
glm5_2_nv    |  24 | 13 |   11 |   54.2 |       8960
```

### Hourly SR
```
hour (UTC) | total | ok | fail | sr_pct
   18:00   |     4 |  3 |    1 |   75.0
   19:00   |     9 |  5 |    4 |   55.6
   20:00   |    10 |  6 |    4 |   60.0
   21:00   |    21 | 17 |    4 |   81.0
   22:00   |     4 |  2 |    2 |   50.0
   23:00   |     8 |  4 |    4 |   50.0
   00:00   |     5 |  3 |    2 |   60.0
```

### 最近10条请求
```
ts                          | model     | status | dur   | error_type              | tiers_tried
2026-07-16 00:06:19+00     | dsv4p_nv  |    502 |  7583 | zombie_empty_completion | 1
2026-07-16 00:06:11+00     | dsv4p_nv  |    200 | 19538 |                         | 1
2026-07-16 00:03:44+00     | glm5_2_nv |    502 |  5413 | zombie_empty_completion | 1
2026-07-16 00:03:39+00     | glm5_2_nv |    200 | 12815 |                         | 1
2026-07-16 00:03:25+00     | glm5_2_nv |    200 |  5360 |                         | 1
2026-07-15 23:35:52+00     | dsv4p_nv  |    502 |  5986 | zombie_empty_completion | 1
2026-07-15 23:35:46+00     | dsv4p_nv  |    200 |  7063 |                         | 1
2026-07-15 23:33:31+00     | glm5_2_nv |    502 |  4676 | zombie_empty_completion | 1
2026-07-15 23:33:26+00     | glm5_2_nv |    200 |  6230 |                         | 1
2026-07-15 23:05:56+00     | dsv4p_nv  |    502 |  4213 | zombie_empty_completion | 1
```

### ATE详情
```
tiers_tried_count | cnt | avg_dur_ms
                1 |  21 |       6540
```
→ 全部21个失败: tiers_tried_count=1, fallback_occurred=f, fallback_actually_attempted=f

### tier_attempts: 0 (clean key pool, no key cycling)
### NV-ALL-TIERS-FAIL logs: 0
### NV-MS-FB logs: 0
### NV-PEER-FB logs: 0
### ms_gw: 13/13 100% SR (perfect fallback)

## Zombie Pattern (R1107, code-level feature)
- NVCF content-filter: 大输入(223K+ chars) → finish_reason=stop 但 content_chars=12 < 50
- Gateway检测: `[NV-ZOMBIE-EMPTY]` → 发送 `finish_reason=timeout` error chunk 触发客户端fallback
- Log: `[NV-ZOMBIE-ERROR-CHUNK]` sent finish_reason=timeout error SSE chunk
- 3-8s fast abort (vs 旧96s hang) → 更快触发客户端fallback
- 非proxy-config可修复 — NVCF侧内容过滤行为

## 决策: NOP
- 19/21 失败 = zombie_empty_completion (NVCF content-filter, non-config-fixable, R1107 code-level feature)
- 2/21 失败 = all_tiers_exhausted (single-tier, 6.3s/8.4s, 低量3.3%)
- 0 tier_attempts → key pool clean, no key cycling
- FALLBACK_GRAPH={} (R832设计) → tier_chain single-tier 是预期状态
- All params floor/optimal: UPSTREAM=66, FASTBREAK=1, BUDGET=205, PEER_FB=66, MS_FB=120
- compose md5=9fb97661 (不变)
- ms_gw 13/13 100% SR → fallback可靠
- 铁律: 只改HM1不改HM2 ✓

## ⏳ 轮到HM1优化HM2
