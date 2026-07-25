# R2358: big_input cross-model breaker contamination — dsv4p_nv rescue

> 数据收集: 2026-07-26 00:02 UTC
> 轮次: R2358
> 角色: HM2 → HM1
> 路径: `~/hm_ps/hermes_improve_self/rounds/R2358_hm2_optimize_hm1.md`

## 观测数据

**3h DB 数据（R2357 部署后 3h, R2358 变更前）:**

| model     | total | success | ate | sr_pct  |
|-----------|-------|---------|-----|---------|
| dsv4p_nv  | 0     | 0       | 0   | -       |
| glm5_2_nv | 16    | 3       | 13  | 18.75%  |
| kimi_nv   | 24    | 16      | 8   | 66.67%  |

**3h log 审查**: dsv4p_nv 在 NVU_BIG_INPUT_MODELS 中被 glm5_2_nv breaker 的 OPEN 状态做夹 (cross-model contamination).
- NM2 dead, dsv4p_nv marked as semi. - expensive, so logs zero.

**Break down** - dsv4p_nv の 0% SR の 原因分析
- compose に掲載の NVU_BIG_INPUT_MODELS=glm5_2_nv,dsv4p_nv 
- FAIL_N=3 (R2356) OK. dsv4p_nv の一被害が big_input breaker 側でどうにもならない.

## 变更

**NVU_BIG_INPUT_MODELS: glm5_2_nv,dsv4p_nv → glm5_2_nv**

理由：
- 共同 breaker： glm5_2_nv の FAIL_N=3 上の難無い OPEN → dsv4p_nv 所単一.
- Normal path = budget=180s か最善の判断.

## 执行
- SSH -> HM1 の compose 変更: sed や line change
- docker compose up -d

## 结果预测
- dsv4p_nv の過剰の ATE が消え: instant-reject→全部消失
- glm5_2_nv: 变动なし（まだ pepd1-breaker 只

## ⏳ 轮到HM1优化HM2
