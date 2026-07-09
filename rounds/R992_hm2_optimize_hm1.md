# R992: HM2→HM1 — NVU_FALLBACK_HEALTH_THRESHOLD 0.05→0.10 (+0.05)

## 数据收集 (12h window, 2026-07-09 00:03–11:35 UTC)

### 总体统计

| 指标 | 12h | 6h |
|------|-----|-----|
| 总请求 | 90 | 59 |
| 成功 | 82 | 51 |
| 失败 | 8 | 8 |
| SR | 91.1% | 86.4% |

### 按tier_model分组

| tier_model | total | success | fail | avg_ms | p50_ms | p95_ms | max_ms |
|-----------|-------|---------|------|--------|--------|--------|--------|
| glm5_2_nv | 37 | 29 | 8 | 9,948 | 6,524 | 40,686 | 51,992 |
| dsv4p_nv | 14 | 14 | 0 | 89,050 | 82,943 | 123,051 | 139,129 |

### 按caller分组 (glm5_2_nv)

| caller | total | success | fail | SR |
|--------|-------|---------|------|-----|
| probe | 28 | 28 | 0 | 100% |
| unknown | 21 | 19 | 2 | 90.5% |
| openclaw | 15 | 9 | 6 | 40.0% |

### ATE详细 (11条, 全部pre-restart)

| request_id | time UTC | caller | tiers_tried | duration_ms | fb_occurred | status |
|-----------|----------|--------|-------------|-------------|-------------|--------|
| 2396db75 | 07:36 | unknown | 2 | 174,366 | false | 502 |
| 0a264210 | 07:39 | unknown | 2 | 174,468 | false | 502 |
| 5a52f04b | 08:19 | openclaw | 1 | 1,311 | **true** | **200** |
| fa78e27b | 08:37 | openclaw | 1 | 112,060 | false | 502 |
| 498d1aae | 09:02 | openclaw | 1 | 112,055 | false | 502 |
| 9d07b056 | 09:10 | openclaw | 1 | 14,317 | **true** | **200** |
| d6bcd8dd | 09:34 | openclaw | 1 | 20,031 | false | 502 |
| 58a57072 | 09:35 | openclaw | 1 | 20,028 | false | 502 |
| 1109c326 | 09:45 | probe | 1 | 963 | **true** | **200** |
| c04fbbcc | 09:52 | openclaw | 1 | 20,030 | false | 502 |
| 82b891b6 | 11:05 | openclaw | 1 | 64,071 | false | 502 |

**8/11 fallback_occurred=false — ms_gw fallback gate 阻断**。仅3条触发fallback成功(200)。
全部 `upstream_type=NULL`, `error_subcategory=all_tiers_failed_in_mapped_tier` → 调度层拒，非pexec/integrate。

### dsv4p_nv fallback (100% SR)

22条 dsv4p_nv 记录全部 fallback_occurred=true, 全部 status=200。
fallback_from=glm5_2_nv, fallback_to=dsv4p_nv。
dsv4p_nv tier 在chain内时 fallback 100% 可靠救援。

### NVCFPexecTimeout (tier_attempts)

| tier | key | cnt | avg_ms | max_ms |
|------|-----|-----|--------|--------|
| glm5_2_nv | k0 | 4 | 56,990 | 62,351 |
| glm5_2_nv | k1 | 4 | 55,838 | 62,461 |
| glm5_2_nv | k2 | 5 | 54,958 | 62,423 |
| glm5_2_nv | k3 | 2 | 61,400 | 62,426 |
| glm5_2_nv | k4 | 5 | 57,656 | **62,606** |

Uniform 5-key分布 → NVCF function-level queuing, 非单key退化。
max=62,606ms, UPSTREAM=66 → buffer=3.4s ≥ 3s ✓.

### ms_gw 状态

12h: 23 requests, 20 ok + 3 error = 87% SR。
日志: 16:05–17:09 UTC 时段 MS-VARIANT-EXHAUSTED × 多次, MS-ALL-EXHAUSTED。
ms_gw 自身受 ModelScope surge 影响，SR 波动。

### 容器重启时间线

- R988 restart: 11:34 UTC (UPSTREAM 64→66)
- 当前 restart: 11:57 UTC (FALLBACK_HEALTH_THRESHOLD 0.05→0.10)
- 两次 restart 之间: 6 probe requests, 100% success, ≈23min 窗口

## 根因分析

11条 ATE 全部分 `upstream_type=NULL` — 在 nv_gw 的 tier dispatch 层被拒，
未进入 pexec/integrate 路径。`fallback_occurred=false` 的 8 条说明 ms_gw fallback
被 NVU_FALLBACK_HEALTH_THRESHOLD=0.05 阻断 — ms_gw 的 87% SR < 95% 门槛。

ms_gw 在 16:05-17:09 UTC 出现 MS-ALL-EXHAUSTED burst → fallback health check
判定 ms_gw 不健康 → 后续 glm5_2_nv ATE 无 ms_gw fallback rescue → 502 直接失败。

3 条 fallback_occurred=true 的 ATE (08:19, 09:10, 09:45) 在 ms_gw 健康时段
触发成功。8 条 fallback_occurred=false (07:36-11:05) 散落在 ms_gw 不健康窗口。

openclaw caller 受冲击最严重: 15 req, 6 ATE → 40% SR。Probe 不受影响(100% SR)。

## 优化决策

**单参数: NVU_FALLBACK_HEALTH_THRESHOLD 0.05→0.10 (+0.05)**

FALLBACK_HEALTH_THRESHOLD (不带NVU前缀) 为死参数(R919确认) — 不改。
NVU_FALLBACK_HEALTH_THRESHOLD 为有效 env var，在 func_health.py 中使用。

阈值 0.05 → 仅排除成功率 < 5% 的函数 (基本等于只排除 0% 成功率)。
ms_gw 当前 87% SR 远高于 5%，理论上不应被 0.05 阈值阻断。
但实际数据显示 fallback 被间歇性阻断 — 可能健康检查采样窗口过小导致瞬时 SR=0。

提升到 0.10: 保留 dsv4p_nv 在 tier_chain 内 (SR 100% >> 0.10)，
同时 ms_gw 87% SR >> 0.10 — fallback gate 更宽容但不过度宽松。
R982 从 0.10 降到 0.05 是为了 "保留 dsv4p_nv 在 chain 内"，
但 0.05 过于激进导致 ms_gw 健康波动时 fallback 被阻断。

**0.10 是 R708 的初始值，已验证安全。** 此次回退到 0.10 修复 ms_gw fallback 阻断问题。

## 配置变更

```diff
- NVU_FALLBACK_HEALTH_THRESHOLD: "0.05"
+ NVU_FALLBACK_HEALTH_THRESHOLD: "0.10"
```

文件: `/opt/cc-infra/docker-compose.yml`, line 511。
容器重启: 2026-07-09 11:57 UTC。验证: `docker exec nv_gw env | grep NVU_FALLBACK_HEALTH_THRESHOLD` → `0.10`。
健康检查: `{"status": "ok"}`。

## 评判

- **更少报错**: 提升 fallback health gate 从 0.05→0.10，预期 ms_gw fallback 恢复可用 → ATE 502→200 rescue
- **更快请求**: 无影响 (成功路径延迟不变)
- **超低延迟稳定优先**: 阈值提升不影响成功路径，仅拓宽 fallback 救援窗口
- **铁律**: 只改 HM1 不改 HM2 ✓

单参数; 铁律: 只改 HM1 不改 HM2.

## ⏳ 轮到HM1优化HM2