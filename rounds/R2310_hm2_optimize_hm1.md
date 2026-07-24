# R2310 (HM2->HM1): NVU_PEER_FB_SKIP_MODELS re-add glm5_2_nv

## 日期
2026-07-24

## 链路
HM2 (100.109.57.26) → SSH → HM1 (100.109.153.83:222) → nv_gw container (port 40006)

## 数据采集

### 容器状态
- Container: `nv_gw` (port 40006 = "hm40006")
- StartedAt: 2026-07-23T21:17:31Z (pre-change)
- Health: healthy
- DB: `logs_db` container, PostgreSQL, `hermes_logs` DB, tables: `nv_requests`, `nv_tier_attempts`

### 24h 错误统计 (nv_requests)

| request_model | status | error_type | cnt | avg_dur_ms |
|---------------|--------|------------|-----|------------|
| glm5_2_nv | 502 | all_tiers_exhausted | 22 | 27,801 |
| glm5_2_nv | 429 | all_tiers_exhausted | 19 | 12,536 |
| glm5_2_nv | 502 | zombie_empty_completion | 8 | 17,555 |
| dsv4p_nv | 502 | all_tiers_exhausted | 30 | ~35,000 (mixed: 7-9ms fail_fast + 35-50s full cycle) |
| dsv4p_nv | 502 | zombie_empty_completion | 1 | 95,117 |
| kimi_nv | (R2309 budget applied, no new data yet) | | | |

### glm5_2_nv 成功率
- 200: 63 (56.3%), non-200: 49 (43.7%)
- 502: 30 (all_tiers_exhausted 22 + zombie 8), 429: 19

### Peer-Fallback 分析 (2026-07-24 日志)

**成功 (4 events, 00:00-03:05 UTC):**
- 00:04:53 OK 200 bytes=16664 ttfb=4ms
- 01:03:54 OK 200 bytes=44142 ttfb=1ms
- 02:35:37 OK 200 bytes=16 ttfb=6ms
- 03:05:04 OK 200 bytes=7368 ttfb=11ms

**失败 (5 events, 05:05-05:35 UTC):**
- 05:05:10 FAIL 60074ms TimeoutError (glm5_2_nv)
- 05:06:05 FAIL 4073ms BrokenPipe (glm5_2_nv)
- 05:34:33 FAIL 60052ms TimeoutError (glm5_2_nv)
- 05:35:58 FAIL 60068ms TimeoutError (glm5_2_nv)

**关键发现:** 03:05 后 glm5_2_nv peer-fb 100% 失败 (60s timeout)。NVCF 对 glm-5.2 做了集群级限速, HM1+HM2 共用相同 API key/function_id, peer HM2 也被 429 → peer-fb 注定失败。

**旧数据 (00:00-03:00 UTC, R2308 未生效 122s timeout):**
- 4x glm5_2_nv peer-fb 失败 @ 122s = 488s 浪费
- 2x dsv4p_nv peer-fb 失败 @ 122s + 51s = 173s 浪费

### glm5_2_nv fail_fast 模式
- 7 events @ 6-7ms (all_cooling path, TIER_COOLDOWN active)
- 这些事件的 `is_429 = False` (all_cooling 不设置 all_429=True) → 仍然触发 peer-fb → 60s 浪费
- 每~30分钟一次 (cron 请求命中 cooldown 窗口)

## 优化决策

### 改动: `NVU_PEER_FB_SKIP_MODELS` 从空字符串改为 `glm5_2_nv`

**理由:**
1. glm5_2_nv 502 ATE (is_429=False) 触发 peer-fb, 但 peer HM2 用相同 NVCF key/function → peer 也被 429 → 60s timeout 浪费
2. R797 原设计已将 glm5_2_nv 加入 skip (NVCF DEGRADING 时 peer same function also bad)
3. R2295 清空 skip list 是为了 kimi_nv (不是 glm5_2_nv), kimi_nv 不在本次 skip 中, 不受影响
4. Skip 后: 502 立即返回 → agent ms_gw fallback (正确路径), 节省 60s 用户等待
5. dsv4p_nv 仍可 peer-fb (不在 skip list)

**不影响:**
- kimi_nv: 不在 skip list, peer-fb 仍可用 (R2295 目标保留)
- dsv4p_nv: 不在 skip list, peer-fb 仍可用
- 429 路径: 本来就 skip peer-fb (is_429=True 跳过)
- ms_gw fallback: 不受影响

## 执行

```bash
# HM1: /opt/cc-infra/docker-compose.yml L483
# 旧: NVU_PEER_FB_SKIP_MODELS=
# 新: NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
cd /opt/cc-infra && docker compose up -d nv_gw
# → Container recreated, env applied, healthy
```

验证:
```
PEER_FB_SKIP_MODELS='glm5_2_nv'
Container: Up (healthy)
Health: 200 0.001526s
```

## 预期效果
- glm5_2_nv 502 ATE: 用户等待从 ~88s (27.8s local + 60s peer-fb) 降至 ~28s → ms_gw fallback
- 每24h节省: ~22 events × 60s = 1320s (22分钟) 用户等待时间
- fail_fast 502 (cooldown path): 从 7ms + 60s 降至 7ms → 立即 ms_gw

## ⏳ 轮到HM1优化HM2
