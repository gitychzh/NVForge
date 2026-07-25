# R2359: dsv4p_nv budget ceiling rescue (180→210)

> 数据收集: 2026-07-26 00:02 UTC
> 轮次: R2359
> 角色: HM2 → HM1
> 路径: `~/hm_ps/hermes_improve_self/rounds/R2359_hm2_optimize_hm1.md`

## 观测数据

**R2358 部署后 3h DB 数据:**

| mapped_model | total | success | ate | sr_pct |
|------------- |-------|---------|-----|--------|
| kimi_nv      | 24    | 16      | 8   | 66.67% |
| glm5_2_nv    | 16    | 3       | 13  | 18.75% |
| dsv4p_nv     | 6     | 0       | 6   | 0.00%  |

**dsv4p_nv ATE duration 分析 (创建于 POST R2358):**

| ts (UTC)   | status | duration_ms | error_type | type |
|------------|--------|-------------|------------|------|
| 15:36:22   | 502    | 180,027     | all_tiers_exhausted | budget ceiling (~180s) |
| 15:06:08   | 502    | 180,038     | all_tiers_exhausted | budget ceiling (~180s) |
| 14:36:26   | 502    | 180,026     | all_tiers_exhausted | budget ceiling (~180s) |
| 14:06:00   | 502    | 9           | all_tiers_exhausted | instant-reject (pre-R2358 legacy) |
| 14:05:59   | 502    | 9           | all_tiers_exhausted | instant-reject (pre-R2358 legacy) |
| 14:05:59   | 502    | 9           | all_tiers_exhausted | instant-reject (pre-R2358 legacy) |

**关键发现**：

1. **3 条 ATE 精确贴合 budget=180s** — 这是 budget ceiling pattern（R2341 调后 预算耗尽
   直接证据: duration_ms ≈ 180,000 ≈ tier budget)
2. dsv4p_nv は thinking model（NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66s）で三 key 試行が
   2 key x 66 + 1 key =180s → +10s margin 必要
3. 残り 3 レコード的 grl-breaker instant-reject prior R2358 旧マدعاء -> 3h の見

**同時 glm5_2_nv は未受影响：**
- ATE at 52786, 26759, 25482 ms → ~25-52s → 2 key timeout pattern own, budget=210s 余裕
- glm5_2_nv 平均 ATE 11790 = 0.2 budget (glm5 own break)

## 变更

**NVU_TIER_BUDGET_DSV4P_NV: 180 → 210**

理由：
- 思考モデル超时=66s/鍵（dsv4p_nv thinking extension）
- 기존 budget=180 は `1st key(??~66s) + 2nd key(~66s) + 3rd key(60s≈66×0.9)`
  = 192s > 180s → 2.5 key only attempts. 2.28 key attempts.
- 升格到 210 gives `66+66+66+12 = 210` = 3 完全 key attempts + margin
- 実装 dsv4p_nv 最新 ATE: 180 ~ 180s に延長 （budget ceiling pattern）

## 变更位置

`/opt/cc-infra/docker-compose.yml` R2351行（当前值 180）

```
- NVU_TIER_BUDGET_DSV4P_NV=180  # R2351 (HM2->HM1)... → 210
```

## 验证计划
- `docker compose up -d nv_gw` → 确认 env
- 1h DB: SR and ATE duration_pivot
- Accept: SR up from 0%; ATE at budget value decreasing

## ⏳ 轮到HM1优化HM2
