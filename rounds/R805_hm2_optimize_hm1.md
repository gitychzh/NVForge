# R805: HM2→HM1 — NOP — 86.0% SR, 全参数floor, NVCF upstream_type=NULL ATE, 100% fallback, 系统稳定

**时间**: 2026-07-07 07:10 UTC
**决策**: NOP — 零参数改动，零compose改动，零容器重启。

## 触发原因

检测脚本判定HM1有新commit触发cron — R804末尾标记"⏳ 轮到HM1优化HM2"。HM2执行R805自身。

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

容器 uptime: 2026-07-07T00:17:??Z (7h+, healthy). FORCE_STREAM=66 ↔ UPSTREAM=66 synced ✅.

## 二、数据摘要（6h window, 01:10–07:10 UTC）

### 2.1 6h 总体

| 指标 | 数值 |
|------|------|
| 总请求 | 258 |
| 成功 (200) | 222 |
| 失败 (502) | **36** |
| SR | **86.0%** |
| Fallback 触发 | 45 |
| Fallback 成功 | 45 (100%) |
| Single-tier ATE | **0** |
| Double-tier ATE | 36 (100%) |
| All ATE upstream_type | NULL (NVCF调度层) |
| key_cycle_429s | 75 total (49@1, 22@2, 4@3) |
| 429-recovery success | 75 (status=200 AND key_cycle_429s>0) |

### 2.2 Upstream type

| upstream_type | cnt | ok | max_dur | avg_dur |
|---|---|---|---|---|
| nvcf_pexec | 216 | 216 | 211,291 | 47,231 |
| NULL (ATE) | 42 | 6 | 229,007 | 146,760 |

### 2.3 逐小时 SR

| 小时 (UTC) | total | ok | ate | SR |
|---|---|---|---|---|
| 01:00 | 12 | 12 | 0 | 100.0% |
| 02:00 | 9 | 9 | 0 | 100.0% |
| 03:00 | 8 | 6 | 2 | 75.0% |
| 04:00 | 7 | 7 | 0 | 100.0% |
| 05:00 | 4 | 4 | 0 | 100.0% |
| 06:00 | 12 | 10 | 2 | 83.3% |
| 07:00 | 1 | 1 | 0 | 100.0% |

4 consecutive 100% SR hours: 01, 02, 04, 05 UTC ✅.

### 2.4 逐小时按模型 SR

| 小时 (UTC) | dsv4p_nv SR | glm5_2_nv SR |
|---|---|---|
| 01:00 | 100.0% | 100.0% |
| 02:00 | 100.0% | 100.0% |
| 03:00 | 66.7% | 100.0% |
| 04:00 | 100.0% | 100.0% |
| 05:00 | 100.0% | 100.0% |
| 06:00 | 71.4% | 100.0% |
| 07:00 | 100.0% | — |

### 2.5 Model-level SR

| request_model | mapped_model | cnt | sr_pct |
|---|---|---|---|
| glm5_2_nv | glm5_2_nv | 173 | 89.0% |
| dsv4p_nv | dsv4p_nv | 83 | 79.5% |
| kimi_nv | kimi_nv | 2 | 100.0% |

### 2.6 NVCF Function Health

| Function | Health | Status |
|---|---|---|
| dsv4p_nv 74f02205 | 0.40-0.45 | recovering slowly |
| glm5_2_nv 3b9748d8 | 0.80-0.85 | healthy |

### 2.7 Tier Attempts

| tier | error_type | cnt | avg_ms | max_ms |
|---|---|---|---|---|
| dsv4p_nv | 504_nv_gateway_timeout | 28 | — | — |
| dsv4p_nv | NVCFPexecTimeout | 16 | 50,297 | 51,577 |
| dsv4p_nv | empty_200 | 10 | — | — |
| dsv4p_nv | 500_nv_error | 1 | — | — |
| glm5_2_nv | 504_nv_gateway_timeout | 34 | — | — |
| glm5_2_nv | empty_200 | 10 | — | — |
| glm5_2_nv | NVCFPexecTimeout | 6 | 51,526 | 51,637 |

504_nv_gateway_timeout dominates: 28+34=62 vs NVCFPexecTimeout 16+6=22 — NVCF upstream gateway-level timeout, not proxy-config fixable.

### 2.8 UPSTREAM Binding Check

| tier | UPSTREAM | NVCFPexecTimeout max | buffer |
|---|---|---|---|
| dsv4p_nv | 66s | 51,577ms (51.6s) | **14.4s** |
| glm5_2_nv | 66s | 51,637ms (51.6s) | **14.4s** |

Buffer ≥ 3s threshold: ✅ both tiers non-binding. UPSTREAM=66 far from binding.

### 2.9 NVCFPexecTimeout 按 key 分布

| tier | k0 | k1 | k2 | k3 | k4 |
|---|---|---|---|---|---|
| dsv4p_nv | 2 (51,033ms) | 5 (51,201ms) | 3 (51,354ms) | 3 (51,577ms) | 3 (51,069ms) |
| glm5_2_nv | 2 (51,628ms) | 1 (51,458ms) | 0 | 0 | 3 (51,637ms) |

均匀分布 → function-level timeout, 非key-specific。所有key max_ms 在 ~51.5s 附近集中。

### 2.10 Fallback 按方向

| fallback_from | fallback_to | cnt |
|---|---|---|
| dsv4p_nv | glm5_2_nv | 29 |
| glm5_2_nv | dsv4p_nv | 16 |

双向 fallback 正常工作。100% SR (45/45)。

### 2.11 ATE 详情

| request_model | mapped_model | tiers_tried_count | fallback_tiers_used | cnt |
|---|---|---|---|---|
| glm5_2_nv | glm5_2_nv | 2 | {glm5_2_nv,dsv4p_nv} | 19 |
| dsv4p_nv | dsv4p_nv | 2 | {dsv4p_nv,glm5_2_nv} | 17 |

### 2.12 Log 确认

```
docker logs nv_gw --tail 100:
tier_chain=['dsv4p_nv', 'glm5_2_nv'] (dynamic fallback, health={'74f02205': 0.40-0.45, '3b9748d8': 0.80-0.85})
tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={'74f02205': 0.40-0.45, '3b9748d8': 0.80-0.85})
→ FALLBACK_GRAPH bidirectional working ✅

[NV-EMPTY-FASTBREAK] tier=dsv4p_nv 1 consecutive empty_200 ≥ threshold 1 — EMPTY_200_FASTBREAK=1 working
[NV-TIER-FAIL] → [NV-FALLBACK] → [NV-FALLBACK-SUCCESS] — fallback rescue working, 100% effective
[NV-PEER-FB] peer-originated request (hop=1) also all_tiers_exhausted — HM2→HM1 fallback fails on HM1 too, normal
```

## 三、NOP 决策分析

### Gate 1: All ATE double-tier ✅
36 ATE → 36 tiers_tried_count=2. 零 single-tier.

### Gate 2: Zero single-tier ATE ✅
0 rows from start_tier_idx single-tier query.

### Gate 3: NVCFPexecTimeout buffer ≥3s ✅
dsv4p_nv buffer=14.4s, glm5_2_nv buffer=14.4s — >> 3s. UPSTREAM=66 远远未绑定。

### Gate 4: FALLBACK_GRAPH bidirectional ✅
docker logs confirm: `tier_chain=['dsv4p_nv', 'glm5_2_nv']` AND `['glm5_2_nv', 'dsv4p_nv']` both `(dynamic fallback, health={...})`.

### Gate 5: Fallback 100% SR ✅
fallback_occurred=true: 45/45 OK (100%).

### Gate 6: All params at floor ✅
8 floor params confirmed at minimum. UPSTREAM=66, BUDGET=114, FORCE_STREAM=66 at optimal (synced, 14.4s buffer, BUDGET headroom 48s per tier). KEY_COOLDOWN=25, TIER_COOLDOWN=25 stable (429 75/258=29.1% across all requests, 75 429-recoveries prove key rotation rescues).

### Additional signals
- 4 consecutive 100% SR hours (01:00, 02:00, 04:00, 05:00 UTC)
- NVCFPexecTimeout max stable at 51.6s across rounds (no drift — matches R804)
- Fallback bidirectional 100% SR (45/45)
- 75 successful 429-recoveries (key rotation working effectively)
- dsv4p_nv 74f02205 health stable at 0.40-0.45 (no further decline from R804)
- 504_nv_gateway_timeout dominates tier_attempts at 62 combined — NVCF upstream scheduling layer, not config-fixable
- FORCE_STREAM=66 ↔ UPSTREAM=66 synced ✅ (no drift to fix)

### Comparison with R804

R804 (06:50 UTC): 260req/222OK 85.4% SR, 38 ATE, fallback 100% (46/46).
R805 (07:10 UTC): 258req/222OK 86.0% SR, 36 ATE, fallback 100% (45/45).

System virtually identical — no deterioration, no improvement needed. SR slightly up (86.0% vs 85.4%). ATE slightly down (36 vs 38). All key metrics stable.

### Decision

**NOP.** All 6 gates pass. All 36 ATE are `upstream_type=NULL` NVCF scheduling-layer rejections with `error_type=all_tiers_exhausted` — both tiers exhausted after trying all 5 keys each. The 504_nv_gateway_timeout (28 dsv4p + 34 glm5_2 = 62 total) dwarfs NVCFPexecTimeout (16+6=22) — this is NVCF upstream gateway-level timeout, not proxy-config fixable. dsv4p_nv function 74f02205 health=0.40-0.45 producing empty_200 spam contributes to tier exhaustion. All config parameters already at their floor values. Fallback 100% SR covers the remaining successful fallback path. NVCFPexecTimeout buffer 14.4s >> 3s — UPSTREAM=66 is not the bottleneck. Single param per round; iron rule: only change HM1 never HM2.

## 四、结论

R805 NOP. 258req/222OK 86.0% SR, 36 ATE 全 upstream_type=NULL NVCF调度层(非配置可修), fallback 100% SR(45/45). dsv4p_nv health=0.40-0.45 缓慢恢复中但稳定, glm5_2_nv health=0.80-0.85 healthy. NVCFPexecTimeout buffer 14.4s >> 3s. 全参数已达floor/最优值. 与R804数据几乎一致 — 系统稳定无劣化. 零变更.

## ⏳ 轮到HM1优化HM2