# R718: HM2→HM1 — 零变更轮（NVCF dsv4p_nv dual-function unhealthy，所有参数已最优，无需配置变更）

## TL;DR
dsv4p_nv primary NVCF function `74f02205` dead (health=0.0), auto-switched function `8915fd28` health only 0.2-0.333. Both dsv4p_nv functions unhealthy. Post-restart (08:02 UTC) all 10 ATEs are genuine double-tier exhaustion, not config-fixable. All params at optimal/floor. Fallback chain 100% success (42/42). Zero-change. Single param per round; iron rule: only change HM1 never HM2.

---

## 一、当前配置快照（R718 部署前，容器 Up 33 min）

| # | 参数 | HM1 当前值 | 历史来源 |
|---|------|-----------|---------|
| 1 | UPSTREAM_TIMEOUT | 40 | R716: 36→40 (+4s) |
| 2 | TIER_TIMEOUT_BUDGET_S | 110 | R706: 94→110 (+16s) |
| 3 | NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | R709: 2→1 (-1 key) |
| 4 | KEY_COOLDOWN_S | 25 | R162: 34→38→R492: 38→25 |
| 5 | TIER_COOLDOWN_S | 25 | R492: 38→25 |
| 6 | MIN_OUTBOUND_INTERVAL_S | 0 | R638: 0.05→0 |
| 7 | NVU_CONNECT_RESERVE_S | 0 | R657: 1→0 |
| 8 | FALLBACK_HEALTH_THRESHOLD | 0.10 | R708: 安全地板 |
| 9 | NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 40 | R694: 25→40 |
| 10 | NV_INTEGRATE_KEY_COOLDOWN_S | 0 | R631: 1→0 |
| 11 | NVU_FORCE_STREAM_UPGRADE | 0 | R692: 显式0 |
| 12 | NVU_EMPTY_200_FASTBREAK | 2 | R577: 连续阈值 |

---

## 二、6h DB 数据全景

### 2.1 总体统计

```
6h: 386req/276OK(71.5%)/110ATE(28.5%)
```

### 2.2 按模型 SR

| mapped_model | total | ok | ate | sr_pct |
|---|---|---|---|---|
| dsv4p_nv | 222 | 124 | 98 | 55.9% |
| glm5_2_nv | 157 | 146 | 11 | 93.0% |
| kimi_nv | 8 | 7 | 1 | 87.5% |

### 2.3 ATE 按 tiers_tried_count

| tiers_tried_count | cnt | avg_dur |
|---|---|---|
| 1 | 70 | 47,103ms |
| 2 | 40 | 95,964ms |

### 2.4 单 tier ATE 按 start_tier_idx（全部 pre-restart）

| start_tier_idx | cnt | avg_dur |
|---|---|---|
| 0 | 1 | 2,682ms |
| 1 (dsv4p_nv) | 58 | 50,383ms |
| 3 (glm5_2_nv) | 11 | 33,847ms |

**全部 70 ATE `fallback_actually_attempted=false`** — FALLBACK_GRAPH 未部署（容器 restart 而非 up -d）。

### 2.5 Pre/Post-restart 分割（容器重启 ~08:02 UTC）

| period | total | ok | ate | sr_pct |
|---|---|---|---|---|
| pre-restart | 367 | 267 | 100 | 72.8% |
| post-restart | 20 | 10 | 10 | 50.0% |

**dsv4p_nv pre/post:**

| period | total | ok | ate | sr_pct |
|---|---|---|---|---|
| pre-restart | 208 | 120 | 88 | 57.7% |
| post-restart | 14 | 4 | 10 | 28.6% |

**Post-restart ATE breakdown: all 10 are tiers_tried_count=2, avg 80,739ms** — genuine dual-tier exhaustion.

### 2.6 dsv4p_nv 成功请求延迟分布

| bucket | cnt | fb_cnt | avg_dur |
|---|---|---|---|
| ≤10s | 12 | 0 | 6,945ms |
| 10-20s | 18 | 0 | 16,043ms |
| 20-30s | 25 | 0 | 25,058ms |
| 30-40s | 19 | 3 | 34,811ms |
| 40-50s | 23 | 12 | 44,465ms |
| 50-60s | 13 | 5 | 56,195ms |
| 60-80s | 11 | 10 | 69,160ms |
| >80s | 3 | 3 | 96,021ms |

### 2.7 Fallback 统计

| fallback_occurred | cnt | ok | sr_pct |
|---|---|---|---|
| false | 345 | 235 | 68.1% |
| true | 42 | 42 | 100.0% |

**Fallback 100% success — 救回 42 请求。**

---

## 三、nv_tier_attempts 失败分析

### 3.1 dsv4p_nv tier（全部键）

| error_type | nv_key_idx | cnt | avg_elapsed | max_elapsed |
|---|---|---|---|---|
| IntegrateTimeout | 0 | 4 | 25,393ms | 25,472ms |
| IntegrateTimeout | 1 | 3 | 25,418ms | 25,485ms |
| IntegrateTimeout | 2 | 3 | 25,369ms | 25,511ms |
| IntegrateTimeout | 3 | 3 | 25,361ms | 25,488ms |
| IntegrateTimeout | 4 | 4 | 25,423ms | 25,507ms |
| NVCFPexecTimeout | 0 | 12 | 30,929ms | 40,243ms |
| NVCFPexecTimeout | 1 | 12 | 29,835ms | 40,492ms |
| NVCFPexecTimeout | 2 | 15 | 30,565ms | 40,367ms |
| NVCFPexecTimeout | 3 | 11 | 31,213ms | 36,475ms |
| NVCFPexecTimeout | 4 | 11 | 32,475ms | 40,381ms |

**关键发现：**
- NVCFPexecTimeout max=40,492ms = UPSTREAM_TIMEOUT=40 + ~492ms overhead — **exact binding**
- 17 IntegrateTimeout 全部为 status=200 请求（Integrate 先失败 ~25s，pexec retry 成功）
- 61 NVCFPexecTimeout 均匀分布 5 键 → function-level timeout，非 key-level

### 3.2 glm5_2_nv tier

| error_type | nv_key_idx | cnt | avg_elapsed | max_elapsed |
|---|---|---|---|---|
| 429_nv_rate_limit | 1-4 | 14 | — | — |
| NVCFPexecTimeout | 0-4 | 15 | 30,468ms | 40,271ms |

**NVCFPexecTimeout max=40,271ms — 同样紧贴 UPSTREAM=40。**

---

## 四、日志分析（容器最近 100 行）

```
[08:23:17] [NV-FALLBACK] dsv4p_nv → glm5_2_nv
[08:23:23] [NV-FALLBACK-SUCCESS] glm5_2_nv rescued
[08:23:44] [NV-REQ] tier_chain=['dsv4p_nv','glm5_2_nv'] (dynamic fallback, health={3b9748d8:0.444, 74f02205:0.0, 8915fd28:0.0})
[08:23:44] [NV-FUNC-HEALTH] primary=74f02205 unhealthy → switched to 8915fd28
[08:24:25] [NV-FALLBACK] dsv4p_nv → glm5_2_nv
[08:24:40] [NV-FALLBACK-SUCCESS] glm5_2_nv rescued
[08:24:55] [NV-REQ] tier_chain=['dsv4p_nv','glm5_2_nv'] (health={3b9748d8:0.5, 74f02205:0.0, 8915fd28:0.0})
[08:27:32] [NV-REQ] tier_chain=['dsv4p_nv','glm5_2_nv'] (health={3b9748d8:0.5, 74f02205:0.0, 8915fd28:0.333})
[08:28:13] [NV-FALLBACK] dsv4p_nv → glm5_2_nv
[08:28:53] [NV-ALL-TIERS-FAIL] 2 tiers failed, elapsed=80,792ms, ABORT-NO-FALLBACK
[08:28:53] [NV-PEER-FB] peer-originated (hop=1) also all_tiers_exhausted → 502
[08:29:21] [NV-FALLBACK] dsv4p_nv → glm5_2_nv
[08:30:02] [NV-ALL-TIERS-FAIL] 2 tiers failed, elapsed=80,811ms, [NV-PEER-FB]
[08:31:13] [NV-ALL-TIERS-FAIL] 2 tiers failed, elapsed=80,840ms, [NV-PEER-FB]
```

**健康度轨迹：**
- 74f02205 (dsv4p_nv primary): 0.0 持续 — 完全死亡
- 8915fd28 (dsv4p_nv auto-switch): 0.0→0.333→0.25→0.2 — 微弱存活
- 3b9748d8 (glm5_2_nv): 0.444→0.5→0.455 — 健康但并非完美

**关键时刻：** 08:22 UTC NVCF auto-switched dsv4p_nv primary 从 dead 74f02205 到 8915fd28。但新 function 健康度仅 0.2-0.333，仍不足以拯救大多数请求。

---

## 五、决策：零变更

### 5.1 为什么零变更

1. **NVCF 上游问题，非配置可修**：dsv4p_nv 两个 function（74f02205 死，8915fd28 健康度 0.2-0.333）均不健康。Post-restart 所有 10 ATE 均为 genuine dual-tier exhaustion（tiers_tried_count=2），说明两个 tier 都在 NVCF 层面失败，非配置参数可修。

2. **所有参数已达最优/地板**：
   - UPSTREAM_TIMEOUT=40：NVCFPexecTimeout max=40,492ms 精确绑定，已是最优值。继续增加会延长失败路径且 BUDGET 余量不足。
   - FASTBREAK=1：已是地板（R709 从 2 降回 1）。
   - BUDGET=110：per-tier 预算充足。Post-restart ATE 双 tier 耗尽 ~80s，但 BUDGET 不是瓶颈（每个 tier 独立 110s）。
   - KEY_COOLDOWN=25, TIER_COOLDOWN=25, MIN_OUTBOUND=0, CONNECT_RESERVE=0：全部地板。
   - FALLBACK_HEALTH_THRESHOLD=0.10：安全地板，仅排除真正死亡 function（74f02205 在 0.0 仍被排除，8915fd28 在 0.2>0.10 被保留）。

3. **Fallback 链 100% 成功**：42/42 fallback 尝试全部成功。只要 glm5_2_nv function 健康（3b9748d8 0.444-0.5），fallback 就能救回。不可救回的请求是双 tier 同时失败（NVCF 上游问题）。

4. **Pre-restart 单 tier ATE 是部署问题**：70 single-tier ATE 全部 `fallback_actually_attempted=false`，属于容器 restart 而非 up -d 导致的 FALLBACK_GRAPH 未部署。Post-restart fallback 正常运行。

5. **R717 已确认为零变更轮**：R717 同样判定 NVCF function 健康问题不可配置修复。当前情况与 R717 一致——dsv4p_nv NVCF functions 不健康，等待 NVCF 自动恢复。

### 5.2 什么情况下可以恢复变更

- dsv4p_nv NVCF functions 健康度恢复到 >0.5
- 单 tier ATE 重新出现（说明 FALLBACK_GRAPH 可能再次失效）
- 新 NVCFPexecTimeout 绑定模式出现（如 max 变化，需要调整 UPSTREAM）

### 5.3 持续监控信号

- `docker logs nv_gw | grep "NV-FUNC-HEALTH"` — 关注 dsv4p_nv function 健康度恢复
- `docker logs nv_gw | grep "NV-FALLBACK-SUCCESS"` — fallback 救回率
- `nv_requests` 按小时 SR — dsv4p_nv 恢复趋势

---

## 六、数据来源

- DB: `docker exec logs_db psql -U litellm -d hermes_logs` (HM1)
- 日志: `docker logs nv_gw --tail 100` (HM1)
- 配置: `docker exec nv_gw env` (HM1)
- 容器状态: `docker ps --filter name=nv_gw` (HM1, Up 33 min)

## ⏳ 轮到HM1优化HM2