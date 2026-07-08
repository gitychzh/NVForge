# R903: HM2→HM1 — NOP (false trigger, 20th consecutive, 63/62 98.4% 6h SR, nv_gw at floor, ms_gw idle, no optimization space)

> **触发**: cron 误触发 #20 (R884→R903 连续), double-dispatch 模式, 预运行脚本输出 `"这是我提交的, 不触发"`, 但 cron 仍派遣

## 1. 触发分析

- **cron 脚本输出**: `"这是我提交的, 不触发"`
- **最新 commit**: `c44f7ce R902: HM2→HM1 — NOP (false trigger, 19th consecutive...)`
- **commit author**: `opc2_uname` (HM2 自提交)
- **判定**: FALSE TRIGGER — HM1 未提交任何新内容, 脚本正确检测到自提交
- **double-dispatch 确认**: symlink `RN_hm2_optimize_hm1.md → rounds/R902_hm2_optimize_hm1.md` (已指向最新), 预运行脚本已提交 R902
- **HM1 git 状态**: 停留在 R821 (81 轮落后), 未提交任何新内容

## 2. 数据收集 (改前必有数据)

### 2.1 nv_gw 6h 总体统计

| 指标 | 值 |
|------|-----|
| 总请求 | 63 |
| 成功 (200) | 62 |
| 失败 | 1 |
| 成功率 | **98.4%** |
| ATE (502) | 1 (all_tiers_exhausted) |

### 2.2 ATE 详情

| 字段 | 值 |
|------|-----|
| request_model | glm5_2_nv |
| tiers_tried_count | 2 |
| fallback_occurred | false |
| fallback_actually_attempted | false |
| duration_ms | 121,075 |
| start_tier_idx | 2 (glm5_2_nv) |

→ 双 tier 真正耗尽, 非 config-fixable. BUDGET=114, 2×66=132 > 114 但 duration=121s 接近 BUDGET×2 → 符合 per-tier budget math.

### 2.3 nv_tier_attempts 分析 (6h)

| tier | error_type | count | avg_ms | max_ms |
|------|-----------|-------|--------|--------|
| glm5_2_nv | empty_200 | 6 | — | — |
| glm5_2_nv | 504_nv_gateway_timeout | 3 | — | — |

→ empty200 → fallback → dsv4p_nv rescue 正常工作 (见 log 确认)

### 2.4 日志关键信号

```
[21:34:22.1] [NV-TIER-FAIL] tier=glm5_2_nv all 5 keys failed: 429=0, empty200=1, timeout=0, other=0, elapsed=60619ms
[21:34:22.1] [NV-FALLBACK] Tier glm5_2_nv all-failed → falling back to dsv4p_nv
[21:34:41.9] [NV-FALLBACK-SUCCESS] Success on fallback tier dsv4p_nv after primary glm5_2_nv failed
[23:34:36.5] [NV-TIER-FAIL] tier=glm5_2_nv all 5 keys failed: 429=0, empty200=1, timeout=0, other=0, elapsed=60584ms
[23:34:36.5] [NV-FALLBACK] Tier glm5_2_nv all-failed → falling back to dsv4p_nv
[23:34:49.1] [NV-FALLBACK-SUCCESS] Success on fallback tier dsv4p_nv after primary glm5_2_nv failed
```

→ Fallback chain 双向健康: `tier_chain=['glm5_2_nv', 'dsv4p_nv']` (dynamic fallback)
→ empty200 触发 fallback → dsv4p_nv rescue 成功

### 2.5 ms_gw 状态

| 指标 | 值 |
|------|-----|
| 6h 请求 | 0 |
| EMPTY_200_FASTBREAK_THRESHOLD | 3 (R900 已优化) |
| 状态 | 空闲, 无优化空间 |

### 2.6 nv_gw 当前参数

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | floor |
| TIER_TIMEOUT_BUDGET_S | 114 | floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 1 | floor |
| KEY_COOLDOWN_S | 25 | floor |
| TIER_COOLDOWN_S | 20 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | floor |
| NVU_FORCE_STREAM_UPGRADE | 0 | off |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | off |

## 3. 分析与决策

### 3.1 判定: NOP

- **nv_gw**: 所有参数已到 floor, SR 98.4% 稳定, 1 ATE 为 genuine dual-tier exhaustion (非 config-fixable)
- **ms_gw**: 0 请求, 无优化空间
- **Fallback**: 双向健康, empty200→fallback→success 模式正常工作
- **对比 R902**: 63/62 98.4% → 完全一致, 无变化

### 3.2 为什么不能改

1. 所有参数已到 floor — 进一步降低会破坏系统稳定性
2. 唯一 ATE 是双 tier 真正耗尽 (tiers_tried_count=2, duration=121s), 不是 BUDGET 或 FASTBREAK 问题
3. 为 1 个 ATE 调参违反铁律 (改前必有数据, 数据不支持修改)
4. ms_gw 空闲, R900 已优化 EMPTY_200_FASTBREAK_THRESHOLD 5→3

## 4. 历史累积统计

| 轮次 | 6h SR | 说明 |
|------|-------|------|
| R884-R887 | 67/66 98.5% | NOP streak start |
| R888 | — | 误触发期间 agent 错误修改 TIER_COOLDOWN_S (已纠正) |
| R889-R899 | 65/64 98.5% | NOP streak, 1 ATE all_tiers_exhausted |
| R900 | 65/64 98.5% | ms_gw EMPTY_200_FASTBREAK_THRESHOLD 5→3 |
| R901 | 63/62 98.4% | NOP |
| R902 | 63/62 98.4% | NOP |
| **R903** | **63/62 98.4%** | **NOP (本轮)** |

## 5. 本轮修改

| 参数 | 修改前 | 修改后 | 说明 |
|------|--------|--------|------|
| — | — | — | NOP |

---

## ⏳ 轮到HM1优化HM2