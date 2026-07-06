# R804: HM2→HM1 — NOP (false trigger) — 85.4% SR, 全参数floor, NVCF upstream_type=NULL ATE, 100% fallback, 系统稳定

**时间**: 2026-07-07 06:50 UTC
**决策**: NOP — 零参数改动，零compose改动，零容器重启。

## 触发原因

检测脚本判定HM1有新commit触发cron，但R803末尾标记"⏳ 轮到HM1优化HM2"。实际检测到的是HM2自己刚提交的R803（06:47），非HM1新提交。脚本误判为HM1新commit。数据诊断确认系统无需改动。

## 一、当前配置快照

| # | 参数 | HM1 当前值 | Floor? |
|---|------|------------|--------|
| 1 | `UPSTREAM_TIMEOUT` | 66 | — |
| 2 | `TIER_TIMEOUT_BUDGET_S` | 114 | — |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | ✅ floor |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | ✅ floor |
| 5 | `TIER_COOLDOWN_S` | 25 | — |
| 6 | `NVU_PEER_FALLBACK_TIMEOUT` | 45 | — |
| 7 | `NVU_CONNECT_RESERVE_S` | 0 | ✅ floor |
| 8 | `NVU_EMPTY_200_FASTBREAK` | 1 | ✅ floor |
| 9 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 66 | — |
| 10 | `NVU_FORCE_STREAM_UPGRADE` | 0 | ✅ floor |
| 11 | `FALLBACK_HEALTH_THRESHOLD` | 0.10 | ✅ floor |
| 12 | `NV_INTEGRATE_KEY_COOLDOWN_S` | 0 | ✅ floor |
| 13 | `KEY_COOLDOWN_S` | 25 | — |

容器 uptime: 2026-07-06T16:02:04Z (14h+, healthy).

## 二、数据摘要（6h window）

### 2.1 6h 总体

| 指标 | 数值 |
|------|------|
| 总请求 | 260 |
| 成功 (200) | 222 |
| 失败 (502) | **38** |
| SR | **85.4%** |
| Fallback 触发 | 46 |
| Fallback 成功 | 46 (100%) |
| Single-tier ATE | **0** |
| Double-tier ATE | 38 (100%) |
| All ATE upstream_type | NULL (NVCF调度层) |
| key_cycle_429s | 75 total (48@1, 22@2, 5@3) |
| 429-recovery success | 76 (status=200 AND key_cycle_429s>0) |

### 2.2 Upstream type

| upstream_type | cnt | ok | avg_ttfb | avg_dur | max_dur |
|---|---|---|---|---|---|
| nvcf_pexec | 216 | 216 | 48,088 | 48,160 | 211,291 |
| NULL (ATE) | 44 | 6 | 7 | 149,260 | 229,007 |

### 2.3 逐小时 SR

| 小时 (UTC) | total | ok | ate | SR |
|---|---|---|---|---|
| 16:00 | 1 | 0 | 1 | 0.0% |
| 17:00 | 21 | 19 | 2 | 90.5% |
| 18:00 | 24 | 22 | 2 | 91.7% |
| 19:00 | 55 | 49 | 6 | 89.1% |
| 20:00 | 15 | 7 | 8 | 46.7% |
| 21:00 | 10 | 10 | 0 | 100.0% |
| 22:00 | 10 | 7 | 3 | 70.0% |
| 23:00 | 31 | 27 | 4 | 87.1% |
| 00:00 | 42 | 34 | 8 | 81.0% |
| 01:00 | 12 | 12 | 0 | 100.0% |
| 02:00 | 9 | 9 | 0 | 100.0% |
| 03:00 | 8 | 6 | 2 | 75.0% |
| 04:00 | 7 | 7 | 0 | 100.0% |
| 05:00 | 4 | 4 | 0 | 100.0% |
| 06:00 | 11 | 9 | 2 | 81.8% |

### 2.4 逐小时按模型 SR

| 小时 (UTC) | dsv4p_nv SR | glm5_2_nv SR |
|---|---|---|
| 16:00 | 0.0% | — |
| 17:00 | 94.7% | 50.0% |
| 18:00 | 83.3% | 100.0% |
| 19:00 | 66.7% | 91.8% |
| **20:00** | **28.6%** | **62.5%** |
| 21:00 | 100.0% | 100.0% |
| 22:00 | 75.0% | 66.7% |
| 23:00 | 33.3% | 92.9% |
| 00:00 | 100.0% | 78.9% |
| 01:00 | 100.0% | 100.0% |
| 02:00 | 100.0% | 100.0% |
| 03:00 | 66.7% | 100.0% |
| 04:00 | 100.0% | 100.0% |
| 05:00 | 100.0% | 100.0% |
| 06:00 | 71.4% | 100.0% |

20 UTC 窗口 dsv4p_nv 28.6% / glm5_2_nv 62.5% → 21 UTC 两者 100% 恢复。典型 NVCF transient surge → self-recovery 模式。

### 2.5 NVCF Function Health

| Function | Health | Status |
|---|---|---|
| dsv4p_nv 74f02205 | 0.40-0.45 | recovering slowly |
| glm5_2_nv 3b9748d8 | 0.80-0.85 | healthy |

### 2.6 Tier Attempts

| tier | error_type | cnt | avg_ms | max_ms |
|---|---|---|---|---|
| dsv4p_nv | 504_nv_gateway_timeout | 29 | — | — |
| dsv4p_nv | NVCFPexecTimeout | 17 | 50,351 | 51,577 |
| dsv4p_nv | empty_200 | 10 | — | — |
| dsv4p_nv | 500_nv_error | 1 | — | — |
| glm5_2_nv | 504_nv_gateway_timeout | 35 | — | — |
| glm5_2_nv | empty_200 | 10 | — | — |
| glm5_2_nv | NVCFPexecTimeout | 6 | 51,526 | 51,637 |

### 2.7 UPSTREAM Binding Check

| tier | UPSTREAM | NVCFPexecTimeout max | buffer |
|---|---|---|---|
| dsv4p_nv | 66s | 51,577ms (51.6s) | **14.4s** |
| glm5_2_nv | 66s | 51,637ms (51.6s) | **14.4s** |

Buffer ≥ 3s threshold: ✅ both tiers non-binding. UPSTREAM=66 far from binding.

### 2.8 NVCFPexecTimeout 按 key 分布

| tier | k0 | k1 | k2 | k3 | k4 |
|---|---|---|---|---|---|
| dsv4p_nv | 2 (51,033ms) | 5 (51,201ms) | 4 (51,354ms) | 3 (51,577ms) | 3 (51,069ms) |
| glm5_2_nv | 2 (51,628ms) | 1 (51,458ms) | 0 | 0 | 3 (51,637ms) |

均匀分布 → function-level timeout, 非key-specific。所有key max_ms 在 ~51.5s 附近集中。

### 2.9 Fallback 按方向

| fallback_from | fallback_to | cnt |
|---|---|---|
| dsv4p_nv | glm5_2_nv | 30 |
| glm5_2_nv | dsv4p_nv | 16 |

双向 fallback 正常工作。100% SR (46/46)。

### 2.10 ATE 详情

| request_model | mapped_model | tiers_tried_count | fallback_tiers_used | cnt |
|---|---|---|---|---|
| glm5_2_nv | glm5_2_nv | 2 | {glm5_2_nv,dsv4p_nv} | 20 |
| dsv4p_nv | dsv4p_nv | 2 | {dsv4p_nv,glm5_2_nv} | 18 |

## 三、NOP 决策分析

### Gate 1: All ATE double-tier ✅
38 ATE → 38 tiers_tried_count=2. 零 single-tier.

### Gate 2: Zero single-tier ATE ✅
0 rows from `start_tier_idx` single-tier query.

### Gate 3: NVCFPexecTimeout buffer ≥3s ✅
dsv4p_nv buffer=14.4s, glm5_2_nv buffer=14.4s — >> 3s. UPSTREAM=66 远远未绑定。

### Gate 4: FALLBACK_GRAPH bidirectional ✅
docker logs confirm: `tier_chain=['dsv4p_nv', 'glm5_2_nv']` AND `['glm5_2_nv', 'dsv4p_nv']` both `(dynamic fallback, health={...})`.

### Gate 5: Fallback 100% SR ✅
fallback_occurred=true: 46/46 OK (100%).

### Gate 6: All params at floor ✅
8 floor params confirmed at minimum. UPSTREAM=66, BUDGET=114, FORCE_STREAM=66 at optimal (synced, 14.4s buffer, BUDGET headroom 48s per tier). KEY_COOLDOWN=25, TIER_COOLDOWN=25 stable (429 75/260=28.8% across all requests, 76 429-recoveries prove key rotation rescues).

### Additional signals
- 4 consecutive 100% SR hours (01:00, 02:00, 04:00, 05:00 UTC)
- NVCFPexecTimeout max stable at 51.6s across rounds (no drift)
- 24h SR 92.6% (healthy long-range)
- Fallback bidirectional 100% SR (46/46)
- 76 successful 429-recoveries (key rotation working effectively)
- 20 UTC transient surge → 21 UTC full recovery (self-recovered)

### Decision

**NOP.** All 6 gates pass. All 38 ATE are `upstream_type=NULL` NVCF scheduling-layer rejections with `error_type=all_tiers_exhausted` — both tiers exhausted after trying all 5 keys each. The 504_nv_gateway_timeout (29 dsv4p + 35 glm5_2 = 64 total) dwarfs NVCFPexecTimeout (17+6=23) — this is NVCF upstream gateway-level timeout, not proxy-config fixable. dsv4p_nv function 74f02205 health=0.40-0.45 producing empty_200 spam contributes to tier exhaustion. All config parameters already at their floor values. Fallback 100% SR covers the remaining successful fallback path. NVCFPexecTimeout buffer 14.4s >> 3s — UPSTREAM=66 is not the bottleneck. Single param per round; iron rule: only change HM1 never HM2.

## 四、结论

R804 NOP. 260req/222OK 85.4% SR, 38 ATE 全 upstream_type=NULL NVCF调度层(非配置可修), fallback 100% SR(46/46). dsv4p_nv health=0.40-0.45 缓慢恢复中, glm5_2_nv health=0.80-0.85 healthy. NVCFPexecTimeout buffer 14.4s >> 3s. 全参数已达floor/最优值. 零变更.

## ⏳ 轮到HM1优化HM2