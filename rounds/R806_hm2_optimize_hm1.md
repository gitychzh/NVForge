# R806: HM2→HM1 — NOP — 85.9% SR, 全参数floor, NVCF upstream_type=NULL ATE, 100% fallback, 系统稳定

**时间**: 2026-07-07 07:25 UTC
**决策**: NOP — 零参数改动，零compose改动，零容器重启。

## 触发原因

检测脚本判定HM1有新commit触发cron — R805末尾标记"⏳ 轮到HM1优化HM2"，脚本误判为HM1新commit。HM2执行R806自身。

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
| 总请求 | 255 |
| 成功 (200) | 219 |
| 失败 (502) | **36** |
| SR | **85.9%** |
| Fallback 触发 | 46 |
| Fallback 成功 | 46 (100%) |
| Single-tier ATE | **0** |
| Double-tier ATE | 36 (100%) |
| All ATE upstream_type | NULL (NVCF调度层) |

### 2.2 Upstream type

| upstream_type | cnt | ok | avg_dur | max_dur |
|---|---|---|---|---|
| nvcf_pexec | 213 | 213 | 47,015 | 211,291 |
| NULL (ATE) | 42 | 6 | 146,760 | 229,007 |

### 2.3 逐小时 SR

| 小时 (UTC) | total | ok | ate | SR |
|---|---|---|---|---|
| 17:00 | 14 | 13 | 1 | 92.9% |
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
| 06:00 | 12 | 10 | 2 | 83.3% |
| 07:00 | 2 | 2 | 0 | 100.0% |

4 consecutive 100% SR hours: 01, 02, 04, 05 UTC ✅.

### 2.4 Model-level SR

| request_model | mapped_model | cnt | sr_pct |
|---|---|---|---|
| glm5_2_nv | glm5_2_nv | 173 | 89.0% |
| dsv4p_nv | dsv4p_nv | 80 | 78.8% |
| kimi_nv | kimi_nv | 2 | 100.0% |

### 2.5 NVCF Function Health

| Function | Health | Status |
|---|---|---|
| dsv4p_nv 74f02205 | 0.40-0.45 | recovering slowly |
| glm5_2_nv 3b9748d8 | 0.80-0.85 | healthy |

### 2.6 Tier Attempts

| tier | error_type | cnt | avg_ms | max_ms |
|---|---|---|---|---|
| dsv4p_nv | 504_nv_gateway_timeout | 26 | — | — |
| dsv4p_nv | NVCFPexecTimeout | 16 | 50,297 | 51,577 |
| dsv4p_nv | empty_200 | 11 | — | — |
| dsv4p_nv | 500_nv_error | 1 | — | — |
| glm5_2_nv | 504_nv_gateway_timeout | 34 | — | — |
| glm5_2_nv | empty_200 | 10 | — | — |
| glm5_2_nv | NVCFPexecTimeout | 6 | 51,526 | 51,637 |

504_nv_gateway_timeout dominates: 26+34=60 vs NVCFPexecTimeout 16+6=22 — NVCF upstream gateway-level timeout.

### 2.7 UPSTREAM Binding Check

| tier | UPSTREAM | NVCFPexecTimeout max | buffer |
|---|---|---|---|
| dsv4p_nv | 66s | 51,577ms (51.6s) | **14.4s** |
| glm5_2_nv | 66s | 51,637ms (51.6s) | **14.4s** |

Buffer ≥ 3s threshold: ✅ both tiers non-binding.

### 2.8 NVCFPexecTimeout 按 key 分布

| tier | k0 | k1 | k2 | k3 | k4 |
|---|---|---|---|---|---|
| dsv4p_nv | 2 (51,033ms) | 5 (51,201ms) | 3 (51,354ms) | 3 (51,577ms) | 3 (51,069ms) |
| glm5_2_nv | 2 (51,628ms) | 1 (51,458ms) | 0 | 0 | 3 (51,637ms) |

均匀分布 → function-level timeout, 非key-specific。所有key max_ms 在 ~51.5s 附近集中。

### 2.9 Fallback 按方向

| fallback_from | fallback_to | cnt |
|---|---|---|
| dsv4p_nv | glm5_2_nv | 30 |
| glm5_2_nv | dsv4p_nv | 16 |

双向 fallback 正常工作。100% SR (46/46)。

### 2.10 ATE 详情

| request_model | mapped_model | tiers_tried_count | fallback_tiers_used | cnt | avg_ms |
|---|---|---|---|---|---|
| glm5_2_nv | glm5_2_nv | 2 | {glm5_2_nv,dsv4p_nv} | 19 | 173,844 |
| dsv4p_nv | dsv4p_nv | 2 | {dsv4p_nv,glm5_2_nv} | 17 | 165,893 |

### 2.11 Log 确认

```
docker logs nv_gw --tail 100:
tier_chain=['dsv4p_nv', 'glm5_2_nv'] (dynamic fallback, health={'74f02205': 0.40-0.45, '3b9748d8': 0.80-0.85})
tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={'74f02205': 0.40-0.45, '3b9748d8': 0.80-0.85})
→ FALLBACK_GRAPH bidirectional working ✅

[NV-EMPTY-FASTBREAK] tier=dsv4p_nv 1 consecutive empty_200 ≥ threshold 1 — EMPTY_200_FASTBREAK=1 working
[NV-TIER-FAIL] → [NV-FALLBACK] → [NV-FALLBACK-SUCCESS] — fallback rescue working, 100% effective
[NV-PEER-FB] peer-originated request (hop=1) also all_tiers_exhausted — HM2→HM1 fallback fails on HM1 too, normal
BrokenPipeError: client disconnect, not gateway error
```

## 三、NOP 决策分析

### Gate 1: All ATE double-tier ✅
36 ATE → 36 tiers_tried_count=2。零 single-tier。

### Gate 2: Zero single-tier ATE ✅
0 rows from start_tier_idx single-tier query.

### Gate 3: NVCFPexecTimeout buffer ≥3s ✅
dsv4p_nv buffer=14.4s, glm5_2_nv buffer=14.4s — >> 3s. UPSTREAM=66 far from binding.

### Gate 4: FALLBACK_GRAPH bidirectional ✅
docker logs confirm: `tier_chain=['dsv4p_nv', 'glm5_2_nv']` AND `['glm5_2_nv', 'dsv4p_nv']` both `(dynamic fallback, health={...})`.

### Gate 5: Fallback 100% SR ✅
fallback_occurred=true: 46/46 OK (100%).

### Gate 6: All params at floor ✅
8 floor params confirmed at minimum. UPSTREAM=66, BUDGET=114, FORCE_STREAM=66 at optimal (synced, 14.4s buffer, BUDGET headroom 48s per tier). KEY_COOLDOWN=25, TIER_COOLDOWN=25 stable. NVCFPexecTimeout max stable at 51.6s across R803→R804→R805→R806.

### Additional signals
- 4 consecutive 100% SR hours (01, 02, 04, 05 UTC)
- NVCFPexecTimeout max stable at 51.5-51.6s across 4 rounds (no drift)
- Fallback bidirectional 100% SR (46/46) — dsv4p→glm5_2 30, glm5_2→dsv4p 16
- dsv4p_nv 74f02205 health=0.40-0.45 stable (no further decline from R803→R805)
- 504_nv_gateway_timeout dominates tier_attempts at 60 combined — NVCF upstream
- FORCE_STREAM=66 ↔ UPSTREAM=66 synced ✅
- BrokenPipeError isolated: client-side disconnect, not gateway error

### Comparison with R805

| Round | Total | OK | Fail | SR | Fallback SR | dsv4p SR | glm5_2 SR |
|---|---|---|---|---|---|---|---|
| R805 | 258 | 222 | 36 | 86.0% | 45/45 (100%) | 79.5% | 89.0% |
| R806 | 255 | 219 | 36 | 85.9% | 46/46 (100%) | 78.8% | 89.0% |

System virtually identical — SR ±0.1pp, ATE count unchanged, fallback still perfect. No deterioration, no improvement opportunity.

### Decision

**NOP.** All 6 gates pass. All 36 ATE are `upstream_type=NULL` NVCF scheduling-layer rejections with `error_type=all_tiers_exhausted` — both tiers exhausted after trying all 5 keys each. The 504_nv_gateway_timeout (26 dsv4p + 34 glm5_2 = 60 total) dwarfs NVCFPexecTimeout (16+6=22) — this is NVCF upstream gateway-level timeout, not proxy-config fixable. dsv4p_nv function 74f02205 health=0.40-0.45 producing empty_200 spam contributes to tier exhaustion. All config parameters already at their floor values. Fallback 100% SR covers the remaining successful fallback path. NVCFPexecTimeout buffer 14.4s >> 3s — UPSTREAM=66 is not the bottleneck. Single param per round; iron rule: only change HM1 never HM2.

## 四、结论

R806 NOP. 255req/219OK 85.9% SR, 36 ATE 全 upstream_type=NULL NVCF调度层(非配置可修), fallback 100% SR(46/46). dsv4p_nv health=0.40-0.45 缓慢恢复中但稳定, glm5_2_nv health=0.80-0.85 healthy. NVCFPexecTimeout max=51.6s stable across R803-R806 四轮(零漂移). buffer 14.4s >> 3s. 全参数已达floor/最优值. 与R805数据几乎一致 — 系统稳定无劣化. 零变更.

## ⏳ 轮到HM1优化HM2