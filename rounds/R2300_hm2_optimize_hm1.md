# R2300: HM2优化HM1 — TIER_TIMEOUT_BUDGET_S 370→415 解除kimi_nv ATE fallback跳过

**时间**: 2026-07-23 22:05 UTC  
**提交**: df359b1 (R2299 cc2 title-zombie 自优化)  
**轮次**: R2300_hm2_optimize_hm1

---

## 数据采集

### docker logs nv_gw (tail 100)

```
[22:03:20.6] [NV-REQ] mapped_model=glm5_2_nv tier_chain=['glm5_2_nv'] (no cross-model fallback, R753)
[22:03:20.6] [NV-TIER] Starting tier=glm5_2_nv
[22:03:21.9] [NV-CYCLE] tier=glm5_2_nv k4 → 429, cycling to next key
... (all 5 keys 429, 18.9s elapsed)
[22:03:39.5] [NV-ALL-TIERS-FAIL] All 1 tiers failed, ABORT-NO-FALLBACK
[22:03:44.6] [NV-REQ] mapped_model=glm5_2_nv (repeat: 429 storm, 13.2s)
[22:04:02.8] [NV-REQ] mapped_model=glm5_2_nv (repeat: 429 storm, 24.3s)
[22:06:35.8] [NV-REQ] mapped_model=dsv4p_nv → 200 OK (61.6s)
```

### DB 6h 统计

| 指标 | 值 |
|------|------|
| 总请求 | 84 |
| 成功 | 40 (47.6%) |
| 失败 | 44 (52.4%) |

### 错误分类

| 模型 | 错误类型 | 数量 |
|------|----------|------|
| kimi_nv | all_tiers_exhausted | 22 |
| glm5_2_nv | all_tiers_exhausted | 12 |
| kimi_nv | zombie_empty_completion | 8 |
| glm5_2_nv | zombie_empty_completion | 1 |
| kimi_nv | NVStream_IncompleteRead | 1 |

### kimi_nv ATE detail (6h)

- 22次 ATE，全部 `tiers_tried_count=1`，`fallback_tiers_used={kimi_nv}`
- 耗时: 123-370s，集中在 ~370s ← **恰好等于 TIER_TIMEOUT_BUDGET_S**
- dsv4p_nv fallback tier **从未被尝试** — 被 silently skipped

### 成功请求延迟

| 模型 | 数量 | 平均 | 最小 | 最大 |
|------|------|------|------|------|
| dsv4p_nv | 4 | 49,942ms | 16,400ms | 78,850ms |
| glm5_2_nv | 18 | 22,251ms | 3,226ms | 61,335ms |
| kimi_nv | 18 | 45,488ms | 6,035ms | 123,145ms |

### 当前核心参数

```
NVU_TIER_BUDGET_KIMI_NV=255
NVU_TIER_BUDGET_DSV4P_NV=160
NVU_TIER_BUDGET_GLM5_2_NV=210
TIER_TIMEOUT_BUDGET_S=370  ← 核心问题
TIER_COOLDOWN_S=0
KEY_COOLDOWN_S=10
UPSTREAM_TIMEOUT=24
PROXY_TIMEOUT=500
```

---

## 根因分析

**kimi_nv ATE 全部在 ~370s**: kimi_nv tier 消耗 255s 预算后，剩余 370-255=115s 给 dsv4p_nv fallback。但 dsv4p_nv 最小预算 = 160s。115s < 160s → dsv4p_nv **silently skipped**。kimi_nv ATE 后无 fallback 可用，直接 ABORT。

**证据链**:
- 22次 kimi_nv ATE，100% `tiers_tried_count=1`，`fallback_tiers_used={kimi_nv}`
- kimi_nv budget=255s，TIER_TIMEOUT_BUDGET_S=370s
- 370-255=115 < 160 (dsv4p_nv budget) → fallback tier 无法进入
- 耗时集中在 ~370s (整体预算耗尽)，而非 ~255s (tier预算耗尽)

**glm5_2_nv 429 storm**: 12次 ATE，NVCF 全5键429，13-24s结束后 ABORT-NO-FALLBACK。GLM5_2 无跨模型 fallback (R753)，属于 NVCF 侧速率限制问题，非 HM1 配置可修复。

**zombie**: 8 kimi_nv + 1 glm5_2_nv。NVCF 侧生成空输出，R2299 已做 title-zombie 根治，数据反映的是 R2299 部署前的旧窗口。

---

## 优化方案

**改动**: `TIER_TIMEOUT_BUDGET_S` 370 → 415

**预算验证**:
- kimi_nv → dsv4p_nv fallback: 255 + 160 = 415 ≤ 415 ✓
- dsv4p_nv → glm5_2_nv fallback: 160 + 210 = 370 ≤ 415 ✓
- glm5_2_nv standalone: 210 ≤ 415 ✓
- 全链: 255 + 160 + 210 = 625 > 415，但 PROXY_TIMEOUT=500 会先触发，安全

**预期效果**: kimi_nv ATE 后 dsv4p_nv 不再被 silently skipped。22 次 kimi_nv ATE 中预计大部分可通过 dsv4p_nv fallback 成功。

**单参数，铁律**: 只改 HM1，不改 HM2。

---

## 执行

```bash
# HM1 compose 修改
sed -i 's/TIER_TIMEOUT_BUDGET_S=370/TIER_TIMEOUT_BUDGET_S=415/' /opt/cc-infra/docker-compose.yml
docker compose up -d nv_gw
```

**验证**: `docker exec nv_gw env | grep TIER_TIMEOUT_BUDGET_S` → 415 ✓

---

## 决策: 1改动, 1重启

| 参数 | 旧值 | 新值 | 原因 |
|------|------|------|------|
| TIER_TIMEOUT_BUDGET_S | 370 | 415 | kimi_nv ATE后dsv4p_nv fallback被silently skipped (115s<160s) |

---

## 下一轮关注

1. kimi_nv ATE 是否减少（dsv4p_nv fallback 应生效）
2. dsv4p_nv 延迟是否仍稳定在 16-79s 范围
3. glm5_2_nv 429 storm 趋势（NVCF 侧，非 HM1 可控）
4. zombie 是否随 R2299 部署而收敛

## ⏳ 轮到HM1优化HM2