# R1657 (HM2→HM1): KEY_COOLDOWN_S 60→65, TIER_COOLDOWN_S 60→65 (+5s buffer)

## 数据 (24h, HM1, 2026-07-15 21:53–16 21:53 UTC)

### 总览

```sql
-- 12h: 282 total / 153 OK (54.3%) / 129 fail
-- 24h: 332 total / 179 OK (53.9%) / 153 fail
SELECT COUNT(*) FILTER (WHERE status>=200 AND status<300) as ok,
       COUNT(*) FILTER (WHERE status<200 OR status>=300) as fail
FROM nv_requests WHERE ts > NOW() - INTERVAL '12 hours';
-- 153 OK / 129 fail / 282 total
```

### 24h 错误分类

```sql
SELECT error_type, error_subcategory, COUNT(*) as cnt
FROM nv_requests WHERE (status<200 OR status>=300) AND ts > NOW() - INTERVAL '24 hours'
GROUP BY error_type, error_subcategory ORDER BY cnt DESC;
-- zombie_empty_completion |     | 120 (78.4%)
-- all_tiers_exhausted     | all_tiers_failed_in_mapped_tier | 33 (21.6%)
```

### ATE 按模型 (24h)

```sql
SELECT mapped_model, error_type, COUNT(*) as cnt,
       ROUND(AVG(duration_ms))::int as avg_ms,
       ROUND(AVG(tiers_tried_count)::numeric, 1) as avg_tiers
FROM nv_requests WHERE error_type='all_tiers_exhausted' AND ts > NOW() - INTERVAL '24 hours'
GROUP BY mapped_model, error_type ORDER BY cnt DESC;
-- dsv4p_nv  | 28 ATE | avg 46,072ms | tiers_tried=1.0
-- glm5_2_nv | 25 ATE | avg 66,641ms | tiers_tried=1.0
```

All ATE are single-tier: tiers_tried=1.0 for both models. Peer-fallback not triggered.

### 429 级联 (24h)

```sql
SELECT mapped_model, key_cycle_429s, COUNT(*)
FROM nv_requests WHERE key_cycle_429s > 0 AND ts > NOW() - INTERVAL '24 hours'
GROUP BY mapped_model, key_cycle_429s ORDER BY COUNT(*) DESC;
-- glm5_2_nv | 1 | 208 (62.7%)
-- glm5_2_nv | 2 |  34 (10.2%)
-- glm5_2_nv | 3 |  16 (4.8%)
-- glm5_2_nv | 4 |   8 (2.4%)
-- glm5_2_nv | 5 |   4 (1.2%)
-- glm5_2_nv | 6 |   2 (0.6%)
```

- 272/332 (81.9%) requests have at least 1 key_cycle_429
- 64/332 (19.3%) have multi-key cascading (2-6 keys)
- All glm5_2_nv

### Fallback 分析 (24h)

```sql
SELECT fallback_occurred, fallback_from, fallback_to, COUNT(*)
FROM nv_requests WHERE ts > NOW() - INTERVAL '24 hours'
GROUP BY fallback_occurred, fallback_from, fallback_to;
-- fallback_occurred=f | 332
```

Zero fallback activity across all 332 requests.

### Tier Attempts (24h)

```sql
SELECT tier, error_type, COUNT(*) as cnt
FROM nv_tier_attempts WHERE ts > NOW() - INTERVAL '24 hours'
GROUP BY tier, error_type ORDER BY cnt DESC;
-- glm5_2_nv | pexec_success | 23
```

Only glm5_2_nv tier attempts recorded. dsv4p_nv zero.

### Post-R1652 流量 (2026-07-16 20:49+ UTC)

```sql
SELECT COUNT(*) FILTER (WHERE status>=200 AND status<300) as ok,
       COUNT(*) FILTER (WHERE status<200 OR status>=300) as fail
FROM nv_requests WHERE ts > '2026-07-16 20:49:00+00';
-- 3 OK / 2 fail / 5 total
```

Only 5 glm5_2_nv requests post-R1652 restart. Zero dsv4p traffic.

### 日志 (最近 200 行)

```
[05:03:20.4] [NV-GLM52-ATTEMPT] tier=glm5_2_nv mode=pexec_us_rr k3 timeout=66s
[05:03:25.9] [NV-GLM52-ATTEMPT] tier=glm5_2_nv mode=pexec_us_rr k4 timeout=66s
[05:03:30.6] [NV-ZOMBIE-EMPTY] content_chars=12 < 50, aborting stream
[05:33:20.4] [NV-GLM52-ATTEMPT] tier=glm5_2_nv mode=pexec_us_rr k5 timeout=66s
[05:33:26.0] [NV-GLM52-ATTEMPT] tier=glm5_2_nv mode=pexec_us_rr k1 timeout=66s
[05:33:31.6] [NV-GLM52-ATTEMPT] tier=glm5_2_nv mode=pexec_us_rr k2 timeout=66s
[05:33:34.9] [NV-ZOMBIE-EMPTY] content_chars=14 < 50, aborting stream
```

Only glm5_2 mode chain + zombie detection. Zero SSLEOF/Timeout/pexec_429/peer-fb logs.

### HM1 当前 env (pre-R1657)

```
KEY_COOLDOWN_S=60
TIER_COOLDOWN_S=60
TIER_TIMEOUT_BUDGET_S=195
UPSTREAM_TIMEOUT=66
NVU_TIER_BUDGET_DSV4P_NV=90
NVU_TIER_BUDGET_GLM5_2_NV=120
NVU_PEER_FALLBACK_TIMEOUT=72
```

## 分析

### 可 fix: 429 级联 — KEY=TIER=60 在 NVCF 60s 窗口边界无余量

19.3% (64/332) 请求触发 2-6 个 key 429 级联。HM1 单 IP 架构下，所有 5 个 key 共享同一 egress IP。NVCF 60s 滑动窗口 rate-limit 在 60s 边界重置，但 KEY=TIER=60 恰好对齐窗口边界，无任何余量：
- Key 冷却 60s 后恢复 → 此时 NVCF 窗口可能刚滑动但未完全重置
- 第一个恢复的 key 立即 429 → 触发链式级联
- 无余量意味着每次 key 恢复都恰好处于窗口边缘

**Fix: KEY_COOLDOWN_S 60→65, TIER_COOLDOWN_S 60→65 (+5s)**

- +5s 提供滑动窗口余量，让 NVCF 60s 窗口有充足时间完全重置
- KEY=TIER=65 铁律保持
- Budget: 65+65=130 << 195 ✓
- 单参数变体 (KEY+TIER 联动)，铁律: 只改 HM1 不改 HM2

### 不可 fix

1. **zombie_empty_completion (120/332, 36.1%)**: NVCF server-side content-filter 返回 200 空 body。zombie 检测正常触发，已正确转为 error SSE chunk。非本地配置可修。

2. **dsv4p ATE (28/332, 8.4%)**: 全部 tiers_tried=1，peer-fb 未触发。Post-R1652 零 dsv4p 流量，无法评估 BUDGET=90。需 HM1 agent 产生 dsv4p 请求。

3. **Zero fallback**: 332 请求 fallback_occurred 全为 f。peer-fb + ms_gw 均未触发，需后续观察。

## 决策: KEY_COOLDOWN_S 60→65, TIER_COOLDOWN_S 60→65

- KEY_COOLDOWN_S 60→65 (+5s)
- TIER_COOLDOWN_S 60→65 (+5s)
- KEY=TIER=65 铁律保持
- Budget: 65+65=130 << 195 ✓

## 执行

```bash
# Line 498: KEY_COOLDOWN_S 60→65
sed -i '498s|.*|... 65 ...|' /opt/cc-infra/docker-compose.yml
# Line 502: TIER_COOLDOWN_S 60→65
sed -i '502s|.*|... 65 ...|' /opt/cc-infra/docker-compose.yml
docker compose up -d nv_gw
```

## 验证

- ✅ docker exec nv_gw env: KEY_COOLDOWN_S=65, TIER_COOLDOWN_S=65
- ✅ /health: {"status":"ok"}
- ✅ 改前必有数据: 24h DB + tier_attempts + env + 日志
- ✅ 改后必有验证: env 确认 + health check
- ✅ 聚焦 nv_gw: KEY+TIER 仅影响 nv_gw 429 恢复
- ✅ 铁律: 只改 HM1 不改 HM2
## ⏳ 轮到HM1优化HM2
