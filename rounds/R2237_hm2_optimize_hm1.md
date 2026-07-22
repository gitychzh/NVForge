# R2237 (HM2→HM1): NVU_TIER_BUDGET_GLM5_2_NV 28→34 (+6s)

## 数据(6h窗口, 39req)
```
=== 6H SUMMARY ===
glm5_2_nv|30|22|8|21248ms avg_ok
dsv4p_nv|9|4|5|35808ms avg_ok
Total: 39req/26OK(66.7%SR)/13fail

=== FAILURE BREAKDOWN ===
glm5_2_nv zombie_empty_completion: 5
dsv4p_nv all_tiers_exhausted: 5 (all preempted, 0 tier_attempts)
glm5_2_nv all_tiers_exhausted: 3 (all preempted, 0 tier_attempts)

=== KEY CYCLE ===
glm5_2_nv: 30 total, cycle0=3, cycle1=21, cycle2+=6 → 27/30 (90%) key_cycle≥1!
dsv4p_nv: 9 total, cycle0=9 — all no-cycle

=== BIG INPUT ===
38/39 req (97%) > 90000 threshold

=== ATE PREEMPTION ===
8/13 failures are ATE — all 0 tier_attempts, all big_input (315K chars)
BREAKER still OPEN for 2+ intervals from prior zombie triggers
4 dsv4p ATE are status=200 phantom (empty-200 after preemption timeout)

### 根因: BUDGET_GLM5_2 过紧
Current: KEY_COOLDOWN_S=12, UPSTREAM_TIMEOUT=24, BUDGET_GLM5_2=28
KEY(12)+UPSTREAM(24)=36 > BUDGET(28)!
glm5_2 27/30 req key_cycle≥1 — first key almost always in cooldown
key_cycle=1 per request costs at least KEY_COOLDOWN_S(12s)
With BUDGET=28 < KEY+UPSTREAM=36, single key cycle can exhaust budget

R2159 (25→28) was based on 83.8% SR with BUDGET barely > UPSTREAM
Current 90% key cycling strain wasn't in that data

## 优化: NVU_TIER_BUDGET_GLM5_2_NV 28→34 (+6s)

34 = UPSTREAM(24) + 10s high-confidence margin for:
- 1 key cycle (12s KEY_COOLDOWN)
- 1 upstream timeout (24s)  
- 2s buffer

Budget check: KEY(12)+TIER(0)+GLM5_2(34)=46 << TIER_BUDGET(157) → 111s margin ✓
34 ≥ UPSTREAM(24) → fallback tier not silently skipped ✓
6s increase from prior R2159 28 — conservative, single-param discipline

注意: glm5_2 zombie 5 (NVCF server-side empty response) 不可配置修复
dsv4p ATE 5 是从 breaker 预判(preemption)而来，非真实预算不足

## 验证
- `NVU_TIER_BUDGET_GLM5_2_NV=34` live env确认 (docker exec nv_gw env)
- nv_gw health: `{"status": "ok"}`, 5 keys, 3 tier models
- 单参数; 铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2