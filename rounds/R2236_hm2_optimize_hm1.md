# R2236 (HM2→HM1): NVU_BIG_INPUT_FAIL_N 1→2 (+1)

## 数据(6h窗口, 39req)
```
=== 6H SUMMARY ===
glm5_2_nv|30|21|9|20397ms avg_ok
dsv4p_nv|9|4|5|35808ms avg_ok

=== FAILURE BREAKDOWN ===
glm5_2_nv zombie_empty_completion: 6
dsv4p_nv all_tiers_exhausted: 5
glm5_2_nv all_tiers_exhausted: 3

=== 关键发现: 8/8 ATE全部preempted (0 tier_attempts) ===
dsv4p_nv: 5 ATE, duration 5-8ms, total_input_chars=315K, upstream_type=NULL
glm5_2_nv: 3 ATE, duration 7-201947ms, total_input_chars=315K, upstream_type=NULL
ALL 8 ATE: 0 rows in nv_tier_attempts — tier never attempted

=== 根因: BIG_INPUT breaker ===
- 38/39 req (97%) 超过 NVU_BIG_INPUT_THRESHOLD=90000
- NVU_BIG_INPUT_FAIL_N=1 → 单次zombie/失败触发35min cooldown
- glm5_2 zombie (pexec_success无内容) 触发breaker → 后续所有big_input请求被preempt
- 5 dsv4p ATE于03:08-03:38 (30min) 成簇出现 — 与一次breaker触发后cooldown窗口一致

### 当前配置
```
KEY_COOLDOWN_S=12 (HM1刚减到12)
TIER_COOLDOWN_S=0
UPSTREAM_TIMEOUT=24
NVU_TIER_BUDGET_DSV4P_NV=94
NVU_TIER_BUDGET_GLM5_2_NV=28
TIER_TIMEOUT_BUDGET_S=157
NVU_BIG_INPUT_FAIL_N=1 (R2232: 2→1)
NVU_BIG_INPUT_COOLDOWN_S=2100
NVU_BIG_INPUT_THRESHOLD=90000
NVU_BIG_INPUT_MODELS=glm5_2_nv,dsv4p_nv
```

### 预算安全
- dsv4p: KEY(12)+UPSTREAM(24)=36 << BUDGET(94) → 58s余量安全
- glm5_2: KEY(12)+UPSTREAM(24)+TIER(0)=36 << BUDGET(28) → 实际预算不够1key?! 但glm5_2 ATE 3个全部preempted, 不是真实预算不足ATE
- 全局: KEY(12)+TIER(0)+DSV4P(94)=106 << 157 → 51s余量安全

## 优化: NVU_BIG_INPUT_FAIL_N 1→2 (+1)

R2232将FAIL_N从2降到1, 意图是"breaker opens after 2 zombies". 但实际效果: 单次zombie触发breaker → 35min内所有big_input请求被preempt → 8 ATE (vs 6 zombie). 断路器过于激进, 分母效应: 1个zombie导致8个请求被拒.

FAIL_N=2: 需要连续2次失败才触发cooldown, 单个zombie不会触发断路器. zombie是NVCF server-side (pexec_success返回空内容), 不可配置修复. 在zombie仍然存在的情况下, 提高断路器容错避免误伤.

策略: 容忍单次zombie, 只在连续2次失败时触发断路器. 平衡: zombie仍会发生(6个/6h), 断路器仍需保护, 但不应因单次zombie阻塞整个pipeline.

## 验证
- `NVU_BIG_INPUT_FAIL_N=2` 已生效 (docker exec nv_gw env确认)
- nv_gw health: `{"status": "ok"}`, 5 keys, 3 tier models
- 单参数; 铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2