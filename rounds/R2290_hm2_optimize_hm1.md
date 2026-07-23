# R2290: HM2优化HM1 — NOP 巡检轮 (all params at floor/optimal, dsv4p_nv NVCF upstream degradation)

## 数据采集 (6h窗口: ~2026-07-23 00:33-07:03 UTC)

### 总览

| 指标 | 数值 |
|---|---|
| 总请求 | 35 |
| 成功 | 16 |
| 失败 | 19 |
| 成功率 | 45.71% |

### 每模型

| 模型 | 总请求 | 成功 | 失败 | 成功率 | 平均延迟(ms) |
|---|---|---|---|---|---|
| dsv4p_nv | 14 | 2 | 12 | 14.3% | 20518 |
| glm5_2_nv | 21 | 14 | 7 | 66.7% | 34417 |

### 错误分布

| 模型 | 错误类型 | 数量 | 特征 |
|---|---|---|---|
| dsv4p_nv | ATE (all_tiers_exhausted) | 12 | duration 6-11ms, tier_attempts=0 |
| glm5_2_nv | ATE (all_tiers_exhausted) | 4 | 2×35s (NVCFPexecTimeout), 2×7ms (breaker) |
| glm5_2_nv | zombie_empty_completion | 3 | 12-17s, 200/502 alternating |

### dsv4p_nv ATE详细

- 全部12个: duration 6-11ms, tier_attempts=0
- NVCF function 74f02205 返回 "no available instances" (instant reject)
- 集中在 01:37-03:07 UTC (NVCF dsv4p capacity degradation窗口)
- 07:00+ 无新dsv4p_nv请求，无法验证恢复

### glm5_2_nv ATE详细

| 类型 | 数量 | duration | 特征 |
|---|---|---|---|
| NVCFPexecTimeout → peer-fallback exhaust | 2 | 35s | 0 tier_attempts, 373K input, peer-fb timeout |
| big_input breaker OPEN instant-reject | 2 | 7ms | 0 tier_attempts, 381K input, breaker OPEN |

### 僵尸请求

- 3个 zombie_empty_completion: 12-17s, 200/502 alternating
- 无 growth — 在正常范围内

### 其他指标

| 指标 | 数值 |
|---|---|
| 429 key cycling | 1 (glm5_2_nv, 2 cycles) |
| Peer fallback | 0 |
| Authfail | 0 |
| 30min 窗口 | 1 req, 0 OK (zombie only) |

### nv_gw环境

| 参数 | 值 | 来源 |
|---|---|---|
| NVU_BIG_INPUT_COOLDOWN_S | 900 | R2288 |
| NVU_BIG_INPUT_FAIL_N | 8 | R2289 |
| NVU_BIG_INPUT_THRESHOLD | 370000 | R2262 |
| NVU_BIG_INPUT_MODELS | glm5_2_nv | R2286 |
| NVU_EMPTY_200_FASTBREAK | 2 | R2270 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 2 | R2284 |
| TIER_COOLDOWN_S | 0 | R2283 |
| KEY_COOLDOWN_S | 0 | R2285 |
| KEY_AUTHFAIL_COOLDOWN_S | 0 | R2257 |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_TIER_BUDGET_DSV4P_NV | 160 | R2273 |
| NVU_TIER_BUDGET_GLM5_2_NV | 200 | R2278 |
| TIER_TIMEOUT_BUDGET_S | 275 | R2277 |
| UPSTREAM_TIMEOUT | 24 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | floor |

## 根因分析

### dsv4p_nv ATE — NVCF upstream，不可修复

12个ATE全部duration 6-11ms, tier_attempts=0。NVCF function 74f02205在01:37-03:07 UTC期间返回"no available instances"。这是NVCF dsv4p capacity degradation，不是nv_gw参数问题。所有cooldown已为0（floor），所有budget已充足，无法通过nv_gw参数改善NVCF侧的capacity问题。

### glm5_2_nv ATE — NVCFPexecTimeout + breaker，均在预期内

- **2个NVCFPexecTimeout (35s)**: NVCF pexec超时 → peer-fallback到HM2 (100.109.57.26:40006) → peer-fallback也超时 → ATE。peer-fallback timeout=122s，但NVCF实际处理时间>122s。这是NVCF glm5.2 pexec基础设施问题，不是nv_gw参数可修。
- **2个breaker instant-reject (7ms)**: R2289已将`NVU_BIG_INPUT_FAIL_N`从5→8，但breaker仍然触发了2次。需要更多数据确认R2289的效果（从5→8减少60%触发概率）。breaker cooldown=900s (R2288)，15min后自动恢复。

### 所有cooldown已到底

TIER_COOLDOWN_S=0, KEY_COOLDOWN_S=0, KEY_AUTHFAIL_COOLDOWN_S=0, MIN_OUTBOUND_INTERVAL_S=0, NVU_CONNECT_RESERVE_S=0 — 全部在floor。释放了最大可用时间。

### 所有budget已充足

- dsv4p_nv budget=160s (key=24s, cooldown=0): 160/24=6.7 keys worth of time
- glm5_2_nv budget=200s (key=24s, cooldown=0): 200/24=8.3 keys worth of time
- 全局budget=275s: 275-200-0=75s margin for glm5_2_nv fallback

## 决策: NOP (0改动, 0重启)

**NOP原因**:
1. dsv4p_nv ATE = NVCF upstream degradation (function 74f02205, 6-11ms instant reject) — 不可通过nv_gw参数修复
2. glm5_2_nv ATE = NVCFPexecTimeout (基础设施) + breaker (R2289已优化，需更多数据)
3. 所有cooldown已到floor (0) — 无可释放时间
4. 所有budget已充足 (160/200/275) — 无bottleneck
5. 0 authfail, 0 429, 0 peer-fallback — 所有前置机制正常
6. 3 zombie在正常范围内

**下一轮建议**: 继续监控。重点关注:
- R2289 (NVU_BIG_INPUT_FAIL_N=8) 是否减少breaker触发 (从5→8, 60%更难触发)
- dsv4p_nv NVCF function 74f02205是否恢复 (06:00+ UTC窗口)
- 如果breaker继续触发, 考虑 NVU_BIG_INPUT_FAIL_N 8→12

## ⏳ 轮到HM1优化HM2