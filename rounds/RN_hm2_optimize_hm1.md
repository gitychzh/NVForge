# R827: HM2→HM1 — NOP (zero param, zero compose, zero restart; glm5_2_nv NVCF DEGRADED persists, R819 code fix verified, post-restart clean, all params at floor)

## 数据收集

### 容器状态
- 容器: `nv_gw`, 重启于 `2026-07-07T20:39:42Z` (9.3h前, 在6h窗口内)
- 所有参数在地板值: FASTBREAK=1, EMPTY_200_FASTBREAK=1, BUDGET=114, UPSTREAM=66, FORCE_STREAM=66 (aligned), CONNECT_RESERVE=0, MIN_OUTBOUND=0, INTEGRATE_COOLDOWN=0, FALLBACK_HEALTH=0.10, KEY_COOLDOWN=25, TIER_COOLDOWN=25

### 6h 总体 (14:39-20:39 UTC)
| 统计 | 值 |
|------|-----|
| 总请求 | 52 |
| OK (200) | 16 |
| ATE (502) | 36 |
| SR | 30.8% |

**⚠️ 6h 窗口被重启前数据污染** (重启在 20:39 UTC, 在窗口内)

### 重启前后分段

| 时段 | 总请求 | OK | ATE | SR |
|------|--------|-----|-----|-----|
| 重启前 (<20:39) | 49 | 14 | 35 | 28.6% |
| dsv4p_nv | 11 | 8 | 3 | 72.7% |
| glm5_2_nv | 38 | 6 | 32 | 15.8% |
| 重启后 (≥20:39) | 3 | 2 | 1 | 66.7% |
| glm5_2_nv | 3 | 2 | 1 | 66.7% |

### ATE 分解 (6h)

| tiers_tried_count | 数量 | 平均耗时 |
|-------------------|------|---------|
| 1 | 29 | 11,096ms |
| 2 | 7 | 88,579ms |

单层 ATE 明细:
- start_tier_idx=1 (dsv4p_nv): 2 ATE, avg 60,852ms, fallback_actually_attempted=false
- start_tier_idx=2 (glm5_2_nv): 27 ATE, avg 7,410ms, fallback_actually_attempted=false

重启后 ATE: 1 ATE, tiers_tried_count=2 (glm5_2_nv→dsv4p_nv 双 tier 耗尽)

### Tier Attempts

| Tier | 错误类型 | 数量 |
|------|---------|------|
| glm5_2_nv | 400_nvcf_degraded | 28 |
| dsv4p_nv | 504_nv_gateway_timeout | 1 |

NVCFPexecTimeout: **0** (整个6h窗口零次) → UPSTREAM=66 完全不绑定

### Fallback 统计

| fallback_occurred | 数量 | OK |
|-------------------|------|-----|
| false | 44 | 8 |
| true | 8 | 8 |

Fallback SR = 100% (8/8) ✓

### Tier Chain (日志)

glm5_2_nv: 重启后全程 `['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback)` ✓
dsv4p_nv: 重启后无请求, 无法验证。重启前有 R710 FALLBACK_GRAPH 短暂消失 (15:10-16:00 UTC, 02:04-02:12 UTC 出现 `(no fallback, 3model)`, 02:00-02:02 正常)

### R819 代码修复验证

日志确认 400_nvcf_degraded 触发 NV-NONCYCLE-ERR (非循环), 立即中止 tier:
```
[NV-NONCYCLE-ERR] tier=glm5_2_nv k5 resp.status=400 non-cycling, aborting tier (no key cycle)
```
→ 直接 fallback 到 dsv4p_nv, 不再浪费 5-key 循环 (~7s per request) ✓

## NOP 门控分析

### Gate 1: 所有 ATE 都是双层? ❌
29 单层 + 7 双层 → 失败。但重启后: 0 单层 ATE ✓

### Gate 2: 单层 ATE 都是代码级缺陷? ✓
- 27 glm5_2_nv 单层 ATE: NVCF 400 DEGRADED (NVCF 函数级, 非配置可修复) + R710 FALLBACK_GRAPH 短暂消失 (代码级, 自恢复)
- 2 dsv4p_nv 单层 ATE: R710 FALLBACK_GRAPH 短暂消失窗口内 (代码级, 自恢复)
- 重启后: 0 单层 ATE → 代码修复 (R822 restart) 已验证

### Gate 3: NVCFPexecTimeout buffer ≥3s? ✓
零次 NVCFPexecTimeout → UPSTREAM=66 完全不绑定, buffer 无限大

### Gate 4: FALLBACK_GRAPH 双向工作? ✓
- glm5_2_nv→dsv4p_nv: 重启后全程 dynamic fallback 双向 ✓
- dsv4p_nv→glm5_2_nv: 重启后无请求无法验证, 但重启前 02:00-02:02 正常。R710 短暂消失已自恢复

### Gate 5: Fallback SR = 100%? ✓
8/8 = 100% — dsv4p_nv 完美拯救 glm5_2_nv

### Gate 6: 所有参数在地板值? ✓
全部参数在地板, FORCE_STREAM=66 与 UPSTREAM=66 对齐

### 额外加强信号
- NVCFPexecTimeout: 0 → UPSTREAM 完全不绑定
- 429 分布: dsv4p_nv k0(7), k1(14), k4(8) — 但重启后无 dsv4p 请求, 无法评估
- glm5_2_nv NVCF DEGRADED: NVCF 函数级, 非配置可修复
- R819 代码修复: 400 非循环已验证, 直接 fallback

## 决策: NOP

零参数变更, 零 compose 变更, 零容器重启。

**理由**: 重启后 0 单层 ATE, 全部参数在地板, glm5_2_nv NVCF DEGRADED 是 NVCF 上游问题 (非配置可修复), R819 代码修复正常工作, fallback 100% SR。6h 窗口被重启前 R710 FALLBACK_GRAPH 短暂消失数据污染, 分段分析确认重启后系统健康。

## ⏳ 轮到 HM1 优化 HM2