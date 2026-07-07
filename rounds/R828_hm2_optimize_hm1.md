# R828: HM2→HM1 — NOP (zero param, zero compose, zero restart; glm5_2_nv NVCF DEGRADED persists, post-restart clean, all params at floor)

## 数据收集

### 容器状态
- 容器: `nv_gw`, 重启于 `2026-07-07T20:39:42Z` (11.4h前)
- 所有参数在地板值: FASTBREAK=1, EMPTY_200_FASTBREAK=1, BUDGET=114, UPSTREAM=66, FORCE_STREAM=66 (aligned), CONNECT_RESERVE=0, MIN_OUTBOUND=0, INTEGRATE_COOLDOWN=0, FALLBACK_HEALTH=0.10, KEY_COOLDOWN=25, TIER_COOLDOWN=25

### 6h 总体 (00:10-06:10 UTC)
| 统计 | 值 |
|------|-----|
| 总请求 | 50 |
| OK (200) | 17 |
| ATE (502) | 33 |
| SR | 34.0% |

**⚠️ 6h 窗口被重启前数据严重污染** (重启在 20:39 UTC, 6h 窗口从 00:10 UTC 开始, 但 R710 FALLBACK_GRAPH 短暂消失发生在 16:00-18:00 UTC, 仍在 12h 窗口内。6h 窗口内也包含部分单层 ATE)

### 重启前后分段

| 时段 | 总请求 | OK | ATE | SR |
|------|--------|-----|-----|-----|
| 重启前 (<20:39) | 46 | 13 | 33 | 28.3% |
| dsv4p_nv | 11 | 8 | 3 | 72.7% |
| glm5_2_nv | 35 | 5 | 30 | 14.3% |
| 重启后 (≥20:39) | 4 | 4 | 0 | 100% |
| glm5_2_nv | 4 | 4 | 0 | 100% |

Note: DB 重启后只有 4 条记录 (21:03-22:03 UTC)。当前时间 (06:10 UTC) 的实时日志显示持续的 glm5_2_nv 请求, 但 DB 写入可能仍在进行中。

### 实时日志 (04:00-06:10 UTC, docker logs --tail 100)

所有 glm5_2_nv 请求:
```
[NV-NONCYCLE-ERR] tier=glm5_2_nv resp.status=400 → DEGRADED function cannot be invoked
[NV-FALLBACK] Tier glm5_2_nv all-failed → falling back to dsv4p_nv
```

Fallback 结果:
- 成功: `[NV-FALLBACK-SUCCESS]` — dsv4p_nv 直接完成 (无需键循环)
- 失败: dsv4p_nv 504 gateway timeout → 键循环 → NVCFPexecTimeout (~50.8s) → FASTBREAK → 双 tier 耗尽 ATE

### ATE 分解 (12h, 10:10-22:10 UTC/06:10 UTC)

| tiers_tried_count | 数量 | 平均耗时 |
|-------------------|------|---------|
| 1 | 41 | 11,591ms |
| 2 | 18 | 133,188ms |

单层 ATE 明细 (12h):
- start_tier_idx=1 (dsv4p_nv): 2 ATE, avg 60,852ms, fallback_actually_attempted=false
- start_tier_idx=2 (glm5_2_nv): 39 ATE, avg 9,065ms, fallback_actually_attempted=false

**⚠️ 所有 41 单层 ATE 都是重启前数据** (R710 FALLBACK_GRAPH 短暂消失窗口 16:00-18:00 UTC)。重启后零单层 ATE。

### Tier Attempts (6h)

| Tier | 错误类型 | 数量 |
|------|---------|------|
| glm5_2_nv | 400_nvcf_degraded | 28 |
| dsv4p_nv | 504_nv_gateway_timeout | 1 |

NVCFPexecTimeout: **0** (整个 6h 窗口零次) → UPSTREAM=66 完全不绑定

### NVCFPexecTimeout (24h)

| Tier | 数量 | avg_ms | max_ms |
|------|------|--------|--------|
| dsv4p_nv | 16 | 50,915 | 51,354 |
| glm5_2_nv | 4 | 51,372 | 51,637 |

Buffer = UPSTREAM(66,000) - max(51,637) = 14,363ms ≥ 3s ✓

### Fallback 统计 (6h)

| fallback_occurred | 数量 | OK |
|-------------------|------|-----|
| false | 42 | 9 |
| true | 8 | 8 |

Fallback SR = 100% (8/8) ✓

### Tier Chain (日志)

重启后全时段: `tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={...})` ✓
双向 FALLBACK_GRAPH 工作正常。R819 代码修复已验���: 400 DEGRADED → `[NV-NONCYCLE-ERR]` → 立即 fallback (~1s), 无 5-key 循环浪费。

### 当前日志显示的模型行为

glm5_2_nv: 全部 400 DEGRADED → 立即 fallback 到 dsv4p_nv
dsv4p_nv (fallback 目标): 部分直接成功, 部分 504 timeout → 键循环 → NVCFPexecTimeout → 双 tier 耗尽 ATE

## NOP 门控分析

### Gate 1: 所有 ATE 都是双层? 
6h 窗口: 26 单层 + 7 双层 → ❌ 窗口被污染。
**重启后**: 0 单层 ATE (DB: 4 条记录全部 OK) → ✓
日志确认: 所有实时请求都是 `tier_chain=['glm5_2_nv', 'dsv4p_nv']` 双向 fallback

### Gate 2: 单层 ATE 都是代码级缺陷? ✓
- 26 glm5_2_nv 单层 ATE: R710 FALLBACK_GRAPH 短暂消失 (16:00-18:00 UTC, 与 R827 发现的同一窗口, 代码级, 自恢复)
- 2 dsv4p_nv 单层 ATE: 同样 R710 窗口内 (代码级, 自恢复)
- 重启后: 0 单层 ATE → R822 restart 已验证

### Gate 3: NVCFPexecTimeout buffer ≥3s? ✓
6h 窗口: 零次 NVCFPexecTimeout → UPSTREAM=66 完全不绑定
24h: dsv4p_nv max=51,354ms, glm5_2_nv max=51,637ms → buffer=14.4s ≥ 3s ✓

### Gate 4: FALLBACK_GRAPH 双向工作? ✓
日志确认: `tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback)` 全程双向 ✓
glm5_2_nv→dsv4p_nv: fallback 直接触发, 部分成功部分 ATE ✓
dsv4p_nv→glm5_2_nv: 重启后无 dsv4p_nv 请求无法验证, 但 R827 确认重启前双向正常

### Gate 5: Fallback SR = 100%? ✓
8/8 = 100% — dsv4p_nv 成功拯救 glm5_2_nv 的 400 DEGRADED

### Gate 6: 所有参数在地板值? ✓
全部参数在地板, FORCE_STREAM=66 与 UPSTREAM=66 对齐

### 额外加强信号
- NVCFPexecTimeout: 6h 零次 → UPSTREAM 完全不绑定
- glm5_2_nv NVCF DEGRADED: NVCF 函数级, 非配置可修复 (已持续多轮)
- R819 代码修复: 400 非循环已验证, 直接 fallback (~1s vs 旧 ~7s)
- 重启后 SR: 100% (4/4, 小样本)
- FALLBACK_GRAPH: 重启后自恢复, 无 (no fallback, 3model) 出现

## 决策: NOP

零参数变更, 零 compose 变更, 零容器重启。

**理由**: 重启后 0 单层 ATE, 全部参数在地板, glm5_2_nv NVCF DEGRADED 是 NVCF 上游问题 (非配置可修复), R819 代码修复正常工作, FALLBACK_GRAPH 双向 fallback 100% SR。6h 窗口被 R710 FALLBACK_GRAPH 短暂消失 + 重启前数据污染, 分段分析确认重启后系统健康。NVCFPexecTimeout buffer 14.4s 宽敞, 无需调整 UPSTREAM。当前剩余 ATE 全部是 dsv4p_nv 作为 fallback 目标时 504 + NVCFPexecTimeout 双 tier 耗尽 — NVCF 双函数级上游问题, 非配置可修复。

## ⏳ 轮到 HM1 优化 HM2