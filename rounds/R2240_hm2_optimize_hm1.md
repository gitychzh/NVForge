# R2240 (HM2→HM1): NVU_BIG_INPUT_FAIL_N 2→3 (+1)

## 时间
- 触发: cron 2026-07-22 ~14:35 UTC
- 执行: 2026-07-22 ~14:40 UTC
- 数据收集窗口: 6h (08:35-14:35 UTC)

## 数据 (6h, 40req)

```
=== 6H SUMMARY ===
glm5_2_nv: 30req/22OK/8fail, 24,314ms avg_ok
dsv4p_nv: 10req/4OK/6fail, 35,808ms avg_ok
Total: 40req/26OK(65.0%SR)/14fail

=== FAILURE BREAKDOWN ===
glm5_2_nv zombie_empty_completion: 5 (NVCF server-side, 22,769ms avg, 319K input)
glm5_2_nv all_tiers_exhausted: 3 (slow exhaust, 120,892ms avg, BUDGET=34, pre-R2237 BUDGET=28 data)
dsv4p_nv all_tiers_exhausted: 6
  - 1 real ATE: 94,108ms, 5 tier_attempts → all keys busy/exhausted
  - 3 preempted: 5-8ms, 0 tier_attempts → big_input breaker instant reject
  - 2 phantom: 14-15s, status=200 → empty-200 rescue

=== KEY CYCLE ===
glm5_2_nv: 30 total, cycle0=3, cycle1=20, cycle2+=7 → 90% key_cycle>=1
dsv4p_nv: 10 total, cycle0=10 — all no-cycle

=== BIG INPUT ===
38/40 req (95%) > 250K threshold (R2238 raised from 90K)
```

### 根因: FAIL_N=2 导致 zombie→breaker→preempted ATE 链式反应

R2238 将 THRESHOLD 从 90K 提高到 250K, 大幅减少了 blanket-block。但 3/6 dsv4p ATE 仍然
preempted (5-8ms, 0 tier_attempts) — 这是 big_input breaker 在 FALSE POSITIVE 下打开。

**链式反应**:
1. glm5_2 zombie (NVCF content-filter) → `pexec_timeout` 连续 2 次
2. Breaker opens (FAIL_N=2) — 所有 dsv4p 请求 > 250K 被 preempt
3. COOLDOWN=2100s (35min) — breaker 维持打开 35 min
4. 95% traffic > 250K → 在这个窗口内几乎全部 dsv4p 请求被 preempt → ATE

**为什么 FAIL_N=2 不够**:
- glm5_2 zombie 是 NVCF server-side 问题, 非配置可修复
- Zombie 间隔 ~1.5h (5 次在 6h 窗口内)
- 单次 zombie 不足以触发 FAIL_N=2, 但 zombie+zombie pair 就能
- 或是 zombie + real ATE (94s) 也能触发

**FAIL_N=3 的合理性**:
- 需要 3 次连续失败才触发 breaker → 单次 zombie-zombie pair 不会触发
- 5 zombie / 6h = 1 zombie / 1.2h → 3 consecutive 需要 ~3.6h 窗口内连续, 概率低
- 仍然能捕获 sustained zombie storm (3+ consecutive)
- 1 real ATE (94s) + 1 zombie → 不会触发 (只有 2 次)
- 2 zombie + 1 real ATE → 触发 (sustained failure pattern)

### 直接对比
- 旧: FAIL_N=2 → zombie+zombie 或 zombie+ATE → breaker open 35min → 3 preempted ATE
- 新: FAIL_N=3 → zombie+zombie 不触发 → breaker 保持关闭 → preempted ATE 归零
- 仍然保护: zombie×3 consecutive → breaker open → 合法保护

## 优化: NVU_BIG_INPUT_FAIL_N 2→3 (+1)

单参数; 铁律: 只改HM1不改HM2。COOLDOWN=2100s 和 THRESHOLD=250000 维持不变。

## 验证
- compose 行 635: `NVU_BIG_INPUT_FAIL_N: "3"` ✅
- live env: `NVU_BIG_INPUT_FAIL_N=3` (docker exec nv_gw env) ✅
- Health: `curl localhost:40006/health` → 200 ✅
- Container restart: stop → up -d → Recreated → Started ✅

## ⏳ 轮到HM1优化HM2