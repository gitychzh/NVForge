# R2238 (HM2→HM1): NVU_BIG_INPUT_THRESHOLD 90000→250000 (+160K)

## 数据(6h窗口, 39req)
```
=== 6H SUMMARY ===
glm5_2_nv|30|22|8|24314ms avg_ok
dsv4p_nv|9|4|5|35808ms avg_ok
Total: 39req/26OK(66.7%SR)/13fail

=== FAILURE BREAKDOWN ===
glm5_2_nv zombie_empty_completion: 5 (NVCF server-side, non-config)
dsv4p_nv all_tiers_exhausted: 5 (all preempted, 0 tier_attempts)
glm5_2_nv all_tiers_exhausted: 3 (all preempted, 0 tier_attempts)

=== KEY CYCLE ===
glm5_2_nv: 30 total, cycle0=3, cycle1=20, cycle2+=7 → 27/30 (90%) key_cycle≥1
dsv4p_nv: 9 total, cycle0=9 — all no-cycle

=== BIG INPUT ===
38/39 req (97%) > 90000 threshold
```

### 根因: BIG_INPUT_THRESHOLD=90000 过激, blanket-block 正常流量

Current: THRESHOLD=90000, FAIL_N=2, COOLDOWN=2100s (35m)
97% 请求 > 90000 chars → 几乎所有流量触发 breaker check
8 ATE 全为 preempted (0 tier_attempts), duration 5-8ms → instant reject by breaker

90000 阈值过低:
- Normal agent context 50-250K chars (cron prompts, code analysis,  multi-round）
- 只有 315K+ 的 zombie-prone 超大输入才应该被拦截
- 90000 连正常 agent 对话都挡 → 虚假告警 → preempted ATE

FAIL_N=2 (R2236) 和 COOLDOWN=2100s (R2059) 提供了正确的 breaker 保护机制 —
但阈值太低导致它们保护的是正常流量而不是 zombie。

### R2236 (FAIL_N 1→2) 未能解决的问题

R2236 时已发现 38/39(97%) > 90000, 但归因于 FAIL_N=1 过于敏感。
FAIL_N 1→2 解决了 single-zombie false positive, 但未触及根本: THRESHOLD=90000
太低了, 仍然覆盖 97% 请求, breaker 频繁触发 → 大量 preempted ATE。

## 优化: NVU_BIG_INPUT_THRESHOLD 90000→250000 (+160K)

250000 = 越过 97% 门槛, 仅拦截真正 zombie-prone 的 315K+ 超大输入:
- glm5_2 zombie 5: 315K chars, 5000-7000ms → 会被 250K 阈值拦截 ✓
- Normal agent requests: 50K-250K → 不会被 breaker 误伤 ✓

FAIL_N=2 + COOLDOWN=2100s 维持: 两次 zombie 触发 → 35min cooldown → 仍然保护
selective break pattern 不变, 仅阈值从 blanket 改为 selective

直接对比:
- 旧: 38/39(97%) 触发 breaker → blanket → 8 preempted ATE + 5 zombie
- 新: 仅 315K+ 触发 → selective → zombie 仍拦截, normal 正常通过

单参数; 铁律: 只改HM1不改HM2

## 验证
- `NVU_BIG_INPUT_THRESHOLD=250000` live env 确认 (docker exec nv_gw env)
- nv_gw health: `{"status": "ok"}`, 5 keys, 3 tier models
- compose 行 634 确认

## ⏳ 轮到HM1优化HM2