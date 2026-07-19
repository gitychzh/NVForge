# R1941 (HM2→HM1): NOP — false trigger, 0 new data, 0 config-fixable

**作者**: opc2_uname (HM2)
**类型**: HM2 优化 HM1
**铁律**: 只改HM1不改HM2

## 数据采集

### 6h 窗口 (DB)
| 指标 | 值 |
|------|-----|
| 总请求 | 36 |
| 成功 | 27 (75.0% SR) |
| 失败 | 9 zombie_empty_completion |
| 30min | 3req/2OK (66.7%) |
| 1h | 5req/4OK (80.0%) |

### 失败分布
| mapped_model | error_type | cnt |
|--------------|-----------|-----|
| glm5_2_nv | zombie_empty_completion | 9 |

All 9 zombies: glm5_2_nv big_input (131K-145K chars), key_cycle_429s=1, tiers_tried_count=1, fallback_occurred=f.

### 延迟 (成功请求)
| mapped_model | total | avg_ms | min_ms | max_ms |
|--------------|-------|--------|--------|--------|
| glm5_2_nv | 25 | 11276 | 2333 | 27809 |
| dsv4p_nv | 2 | 30487 | 17893 | 43081 |

### Breaker 状态
- BIG_INPUT_FAIL_N=1, COOLDOWN=21600 (6h)
- Container restarted 14:36 UTC → breaker reset → 1 leak zombie at 15:03 before breaker re-opened
- Post-breaker: 2/2 peer-fallback OK (15.8s, 17.8s via HM2)
- Live state: CLOSED (breaker timer expired)

### 配置状态 (全部在floor)
- UPSTREAM_TIMEOUT=30, TIER_TIMEOUT_BUDGET_S=152, KEY_COOLDOWN_S=60, TIER_COOLDOWN_S=60, MIN_OUTBOUND_INTERVAL_S=0
- NVU_BIG_INPUT_FAIL_N=1, NVU_BIG_INPUT_COOLDOWN_S=21600
- No container drift detected (compose == live env)

## 介入判断

| 条件 | 满足? | 说明 |
|------|-------|------|
| 1. 真实中断 | ❌ | 9 zombie 全部 NVCF-degraded (server-side empty200), 非 HM1 配置引起 |
| 2. SR断崖 | ❌ | 75% SR 是 NVCF 侧 glm5_2 大输入退化, breaker 已正确拦截 |
| 3. 参数漂移 | ❌ | 零漂移, 全部 compose==live env |
| 4. 可紧缩参数 | ❌ | 全部在 floor: UPSTREAM=30, BUDGET=152, KEY=60, TIER=60, MIN_OUTBOUND=0 |

## 结论: NOP 无据不改

breaker 机制 (FAIL_N=1, COOLDOWN=21600) 正确运行: 第1个 zombie 触发 breaker OPEN → 后续 big_input 请求直走 peer-fallback → 全成功。容器重启导致 breaker 重置 → 1个 zombie 泄漏是不可避免的 (in-memory state)。所有参数已在 floor, 无进一步紧缩空间。NVCF glm5_2 大输入退化是服务端问题, 非 HM1 配置可修复。

铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
