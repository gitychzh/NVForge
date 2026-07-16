# R1656 (HM2→HM1): NOP — 零 dsv4p 流量无法评估 BUDGET=90，所有参数 at floor

## 数据 (6h, HM1, 2026-07-16 15:33–21:33 UTC)

```sql
-- 6h 总览
-- 35 total / 19 OK (54.3%) / 16 fail
SELECT COUNT(*) FILTER (WHERE status>=200 AND status<300) as ok,
       COUNT(*) FILTER (WHERE status<200 OR status>=300) as fail,
       COUNT(*) as total
FROM nv_requests WHERE ts > NOW() - INTERVAL '6 hours';
-- 19 OK / 16 fail / 35 total

-- 按模型
SELECT mapped_model, COUNT(*) FILTER (WHERE status>=200 AND status<300) as ok,
       COUNT(*) FILTER (WHERE status<200 OR status>=300) as fail,
       ROUND(AVG(duration_ms) FILTER (WHERE status>=200 AND status<300))::int as avg_ok_ms,
       ROUND(AVG(duration_ms) FILTER (WHERE status<200 OR status>=300))::int as avg_fail_ms
FROM nv_requests WHERE ts > NOW() - INTERVAL '6 hours'
GROUP BY mapped_model;
-- dsv4p_nv:  7 OK / 5 ATE, avg_ok=24555ms, avg_fail=62279ms
-- glm5_2_nv: 12 OK / 11 zombie, avg_ok=6155ms, avg_fail=6521ms

-- 错误分类
SELECT mapped_model, error_type, error_subcategory, COUNT(*) as cnt
FROM nv_requests WHERE (status<200 OR status>=300) AND ts > NOW() - INTERVAL '6 hours'
GROUP BY mapped_model, error_type, error_subcategory ORDER BY cnt DESC;
-- glm5_2_nv | zombie_empty_completion |     | 11
-- dsv4p_nv  | all_tiers_exhausted     | all_tiers_failed_in_mapped_tier | 5
```

### 24h 全景

```sql
-- 332 total / 179 OK (53.9%) / 153 fail
-- zombie: 120, dsv4p ATE: 17, glm5_2 ATE: 16
SELECT mapped_model, error_type, COUNT(*) as cnt
FROM nv_requests WHERE (status<200 OR status>=300) AND ts > NOW() - INTERVAL '24 hours'
GROUP BY mapped_model, error_type ORDER BY cnt DESC;
```

### dsv4p ATE 时间线: 全部 pre-R1652

```
ts                                | duration_ms | tiers_tried | fallback
2026-07-16 18:04:07.695888+00    | 64280       | 1           | f
2026-07-16 18:03:58.438997+00    | 61652       | 1           | f
2026-07-16 18:02:56.412244+00    | 61533       | 1           | f
2026-07-16 18:01:45.752138+00    | 61822       | 1           | f
2026-07-16 18:00:40.607973+00    | 62107       | 1           | f
```

- 全部在 18:00-18:04 UTC，R1652 容器重启前 (20:49 UTC)
- 旧 BUDGET=76 下: 61.5-64.3s 用尽 budget 后 abort
- tiers_tried=1: 仅试了 dsv4p_nv tier，peer-fb 未触发
- Post-R1652 (BUDGET=90, restart 20:49 UTC): **ZERO dsv4p 请求** — 仅 glm5_2_nv

### Post-R1652 流量 (2026-07-16 20:49+ UTC)

```
ts                                | mapped_model | status | duration_ms | error_type
2026-07-16 21:33:31.609357+00    | glm5_2_nv    | 502    | 3377        | zombie_empty_completion
2026-07-16 21:33:26.000292+00    | glm5_2_nv    | 200    | 5424        |
2026-07-16 21:33:20.415334+00    | glm5_2_nv    | 200    | 5046        |
2026-07-16 21:03:25.95425+00     | glm5_2_nv    | 502    | 4664        | zombie_empty_completion
2026-07-16 21:03:20.433512+00    | glm5_2_nv    | 200    | 5054        |
```

- 仅 5 个 glm5_2_nv 请求 (3 OK / 2 zombie)，**零 dsv4p 流量**
- DB 最后请求: 21:33 UTC，当前 DB 时间: 21:43 UTC → ~10 min idle

### 429 分析

```
SELECT mapped_model, key_cycle_429s, COUNT(*)
FROM nv_requests WHERE key_cycle_429s > 0 AND ts > NOW() - INTERVAL '6 hours'
GROUP BY mapped_model, key_cycle_429s;
-- glm5_2_nv | key_cycle_429s=1 | 23
```

- 23/35 req 有单次 key 429 (65.7%)，全为 glm5_2_nv
- 无级联 (无 multi-key 429 链)
- KEY=TIER=60 铁律 hold

### Fallback 分析

```
SELECT fallback_occurred, fallback_from, fallback_to, COUNT(*)
FROM nv_requests WHERE ts > NOW() - INTERVAL '6 hours'
GROUP BY fallback_occurred, fallback_from, fallback_to;
-- fallback_occurred=f | 35
```

- **零 fallback 活动** (peer-fb + ms_gw 均未触发)
- dsv4p ATE 全部 fallback_occurred=f — peer-fb 未触发 (tier budget 先砍)

### Tier Attempts

```
SELECT tier, error_type, cnt FROM nv_tier_attempts WHERE ts > NOW() - INTERVAL '6 hours'
GROUP BY tier, error_type ORDER BY cnt DESC;
-- glm5_2_nv | pexec_success | 23
```

- 仅 glm5_2_nv 有 tier attempts，dsv4p_nv 零记录

### HM1 当前 env (docker exec nv_gw)

```
NVU_TIER_BUDGET_DSV4P_NV=90         # R1652: 76→90
NVU_TIER_BUDGET_GLM5_2_NV=120
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
TIER_TIMEOUT_BUDGET_S=195
UPSTREAM_TIMEOUT=66
KEY_COOLDOWN_S=60
TIER_COOLDOWN_S=60
MIN_OUTBOUND_INTERVAL_S=0
NVU_CONNECT_RESERVE_S=0
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006
NVU_PEER_FALLBACK_TIMEOUT=72
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_MS_GW_FALLBACK_TIMEOUT=120
NVU_SSLEOF_RETRY_DELAY_S=0.5
NVU_PEER_FB_SKIP_MODELS=
NVU_EMPTY_200_FASTBREAK=2
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_STREAM_FIRST_BYTE_DEADLINE_S=20
NVU_STREAM_TOTAL_DEADLINE_S=42
```

### HM2 peer budgets (for cross-reference)

```
NVU_TIER_BUDGET_DSV4P_NV=70
NVU_TIER_BUDGET_GLM5_2_NV=120
NVU_PEER_FALLBACK_TIMEOUT=25     # HM2→HM1
```

### 日志

```
[05:03:20.4] [NV-GLM52-ATTEMPT] tier=glm5_2_nv mode=pexec_us_rr k3 channel=pexec via http://host.docker.internal:7894
[05:03:25.9] [NV-GLM52-ATTEMPT] tier=glm5_2_nv mode=pexec_us_rr k4 channel=pexec via http://host.docker.internal:7895
[05:03:30.6] [NV-ZOMBIE-EMPTY] (glm5_2_nv) passthrough zombie empty completion: finish_reason=stop but content_chars=12 reasoning_chars=0 < 50
[05:03:30.6] [NV-UPSTREAM-ERROR-CHUNK] (glm5_2_nv) sent finish_reason=content_filter error SSE chunk
```

- 仅 glm5_2_nv mode chain 日志 + zombie 检测
- 零 SSLEOF/Timeout/pexec_429/peer-fb 日志

## 分析

### 可 fix 的问题: 0 个

1. **glm5_2 zombie_empty_completion (11/35, 31.4%)**: NVCF server-side content-filter 返回 200 空 body。zombie 检测正常触发 (finish_reason=stop, content_chars < 50)，已正确转为 error SSE chunk 触发下游 retry。非本地配置可修。

2. **dsv4p ATE (5/35, 14.3%)**: 全部 pre-R1652 (18:00-18:04 UTC，旧 BUDGET=76)。Post-R1652 (BUDGET=90) **ZERO dsv4p 请求** — 无法评估 BUDGET=90 是否充分。需 HM1 agent 产生 dsv4p 流量。

3. **key_cycle_429s=1 (23/35, 65.7%)**: 单次 key 429，非级联。KEY=TIER=60 铁律满足。单 IP 架构下 65.7% 单 key 429 率是 NVCF rate-limit 的固有特征。

### 所有参数状态

| 参数 | 当前值 | 状态 |
|------|--------|------|
| KEY_COOLDOWN_S | 60 | floor (KEY=TIER 铁律) |
| TIER_COOLDOWN_S | 60 | floor (KEY=TIER 铁律) |
| NVU_TIER_BUDGET_DSV4P_NV | 90 | R1652 部署，零 dsv4p 流量待观察 |
| NVU_TIER_BUDGET_GLM5_2_NV | 120 | 2×mode 切换，稳定 |
| TIER_TIMEOUT_BUDGET_S | 195 | 90+72=162<195 ✓ |
| UPSTREAM_TIMEOUT | 66 | floor (NVCFPexecTimeout max~62s) |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NVU_PEER_FALLBACK_TIMEOUT | 72 | HM2 BUDGET=70+2=72 ✓ |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | appropriate |
| NVU_SSLEOF_RETRY_DELAY_S | 0.5 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | aggressive zombie detection |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | aggressive |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | aggressive |

### 为何不调

1. **dsv4p BUDGET=90 无法评估** — Post-R1652 重启后仅 5 个 glm5_2 请求，零 dsv4p 流量。需要 HM1 agent 产生 dsv4p 请求才能判断 BUDGET=90 是否充分。
2. **zombie (31.4%) 是 NVCF content-filter server-side** — zombie 检测已正确触发，下游正常 retry，非本地配置可修。
3. **所有参数已在 floor** — KEY_COOLDOWN=60 (不可再减，KEY≥TIER 铁律)，UPSTREAM=66 (不可再减，接近 NVCFPexecTimeout max=62s)，MIN_OUTBOUND=0，CONNECT_RESERVE=0，NV_INTEGRATE_KEY=0，SSLEOF_RETRY=0.5。
4. **当前失败全为 upstream/NVCF 问题** — 无本地配置可改善的失败模式。

## 决策: NOP

- 零参数变更
- 让 R1652 BUDGET=90 继续观察，需 HM1 agent 产生 dsv4p 流量
- 下次轮到时重评估: 若有 dsv4p ATE 复发 → 检查 peer-fb 是否触发 + 是否需调 BUDGET
- 若 zombie 持续高发 → 考虑 ms_gw fallback 调整 (但 zombie 是 NVCF server-side)

## 验证

- ✅ 改前必有数据: 6h + 24h DB + tier_attempts + env + 日志
- ✅ 改后必有验证: N/A
- ✅ 聚焦 nv_gw: 仅分析 nv_gw 链路
- ✅ 所有修改写入仓库: 本轮 NOP 仍记录
- ✅ 铁律: 只改 HM1 不改 HM2
## ⏳ 轮到HM1优化HM2
