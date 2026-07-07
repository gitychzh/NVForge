# R824: HM2→HM1 — NOP (zero param, zero compose, zero restart; post-restart data sparse, glm5_2_nv NVCF DEGRADED, all params at floor)

## ⚙️ 判定: NOP

**执行**: 零参数修改, 零 compose 修改, 零容器重启

## 📊 数据收集 (DB 时钟 21:10 UTC)

### 容器状态
- 容器 `nv_gw` 运行中, 启动于 `2026-07-07T20:39:42Z` (R822 restart, 31 min ago)
- Health: `Up 31 minutes (healthy)`
- FALLBACK_GRAPH: `fallback_chain=['kimi_nv', 'dsv4p_nv', 'glm5_2_nv']` ✓
- tier_chain: `['glm5_2_nv', 'dsv4p_nv']` (dynamic fallback, health={...}) ✓

### 当前配置
```
FASTBREAK=1, EMPTY_200_FASTBREAK=1, BUDGET=114, CONNECT_RESERVE=0
MIN_OUTBOUND=0, KEY_COOLDOWN=25, TIER_COOLDOWN=25, INTEGRATE_COOLDOWN=0
FALLBACK_HEALTH_THRESHOLD=0.10, FORCE_STREAM_UPGRADE=0
UPSTREAM_TIMEOUT=66, FORCE_STREAM_UPGRADE_TIMEOUT=66 (aligned)
```

### 6h 总体 (15:00–21:10 UTC, 含 pre-restart 污染)

| 指标 | 值 |
|------|-----|
| 总请求 | 54 |
| 200 OK | 15 (27.8%) |
| ATE (502) | 39 (72.2%) |
| 单 tier ATE | 32 (82% of ATE) |
| 双 tier ATE | 7 (18% of ATE) |

### 每小时 SR

| 时间 (UTC) | 请求 | OK | SR |
|-----------|------|-----|------|
| 15:00 | 3 | 0 | 0.0% |
| 16:00 | 6 | 0 | 0.0% |
| 17:00 | 6 | 0 | 0.0% |
| 18:00 | 31 | 10 | 32.3% |
| 19:00 | 3 | 3 | 100.0% |
| 20:00 | 3 | 1 | 33.3% |
| 21:00 | 2 | 1 | 50.0% |

### 单 tier ATE 详细

| start_tier_idx | tiers_tried_count | cnt | avg_dur | fallback_actually_attempted |
|----------------|-------------------|-----|---------|---------------------------|
| 1 (dsv4p_nv) | 1 | 2 | 60,852ms | f |
| 2 (glm5_2_nv) | 1 | 30 | 7,536ms | f |

### 双 tier ATE 详细

| tiers_tried_count | cnt | avg_dur |
|-------------------|-----|---------|
| 2 | 7 | 88,579ms |

### nv_tier_attempts (12h)

| tier | error_type | cnt | max_ms |
|------|-----------|-----|--------|
| glm5_2_nv | 400_nvcf_degraded | 56 | — |
| dsv4p_nv | 504_nv_gateway_timeout | 7 | — |
| dsv4p_nv | NVCFPexecTimeout | 4 | 51,165ms |
| glm5_2_nv | 504_nv_gateway_timeout | 3 | — |
| glm5_2_nv | 500_nv_error | 1 | — |

### NVCFPexecTimeout 按 key 分布 (12h, dsv4p_nv only)

| tier | key | cnt | avg_ms | max_ms |
|------|-----|-----|--------|--------|
| dsv4p_nv | k0 | 1 | 51,165 | 51,165 |
| dsv4p_nv | k2 | 2 | 49,970 | 50,108 |
| dsv4p_nv | k4 | 1 | 51,048 | 51,048 |

**NVCFPexecTimeout buffer**: UPSTREAM=66s, max=51,165ms → buffer=14.8s ≥ 3s ✓ (non-binding)

### Fallback 统计

| fallback_occurred | total | OK | SR |
|-------------------|-------|-----|------|
| f | 47 | 8 | 17.0% |
| t | 7 | 7 | **100%** ✓ |

### 模型统计

| mapped_model | total | OK | SR | avg_dur | max_dur |
|-------------|-------|-----|------|---------|---------|
| glm5_2_nv | 43 | 7 | 16.3% | 25,893ms | 115,625ms |
| dsv4p_nv | 11 | 8 | 72.7% | 48,233ms | 68,217ms |

### Post-restart 窗口 (20:39 UTC 后, ~30 min)

| 指标 | 值 |
|------|-----|
| 总请求 | 2 |
| 200 OK | 1 (50.0%) |
| ATE | 1 (50.0%) |
| 单 tier ATE | 0 |
| 双 tier ATE | 1 |
| Fallback SR | 1/1 (100%) |

| mapped_model | total | ok | ate | avg_dur |
|--------------|-------|----|-----|---------|
| glm5_2_nv | 2 | 1 | 1 | 92,500ms |

### key_cycle_429s (12h)

| mapped_model | key_cycle_429s | cnt |
|--------------|----------------|-----|
| glm5_2_nv | 7 | 7 |
| glm5_2_nv | 8 | 1 |
| glm5_2_nv | 1 | 5 |
| dsv4p_nv | 2 | 4 |
| dsv4p_nv | 1 | 1 |

### empty_200 (12h)

| mapped_model | cnt |
|--------------|-----|
| glm5_2_nv | 10 |
| dsv4p_nv | 9 |

## 🔍 诊断

### 1. glm5_2_nv 函数 DEGRADED (NVCF 上游问题, 持续)
`glm5_2_nv` 函数 `3b9748d8-1d85-40e8-8573-0eeaa63a4b63` 对所有 5 个 key 返回 400 DEGRADED。56 条 nv_tier_attempts 全部为 `400_nvcf_degraded`。R819 NONCYCLE 代码修复已验证：第一个 key 400 → 立即 fallback (~1s)，替代旧行为 7-key cycle (~7s)。

**日志证据**:
```
[NV-NONCYCLE-ERR] tier=glm5_2_nv k3 resp.status=400 non-cycling, aborting tier
[NV-FALLBACK] Tier glm5_2_nv all-failed → falling back to dsv4p_nv
```

### 2. dsv4p_nv 偶发 504 + NVCFPexecTimeout
Post-restart 日志显示 dsv4p_nv 间歇性 504 + timeout:
- k2→504 (63s) → k3→NVCFPexecTimeout (50.8s) → FASTBREAK → 双 tier ATE (115s)
- k4→504 (63s) → k5→OK (5s) → NV-FALLBACK-SUCCESS ✓

NVCFPexecTimeout max=51,165ms << UPSTREAM=66s → buffer=14.8s，非绑定约束。dsv4p_nv 504 是 NVCF 上游波动，非配置可修复。

### 3. 6h 窗口严重污染
R822 restart 在 20:39 UTC。Post-restart 仅 2 请求（~30 min）。6h 窗口的 32 单 tier ATE 全部来自 pre-restart 旧 bytecode 行为（NV-CYCLE 在 400 DEGRADED 上循环 5 个 key + FALLBACK_GRAPH 消失）。Post-restart: 0 单 tier ATE。

### 4. R819 代码修复验证通过
Post-restart 日志中所有 glm5_2_nv 400 DEGRADED 请求均显示 `[NV-NONCYCLE-ERR]` → 立即 fallback。无 `[NV-CYCLE]` 在 400 上出现。R819 代码修复在磁盘上正确，重启后字节码加载正确。

### 5. FALLBACK_GRAPH 双向工作
```
fallback_chain=['kimi_nv', 'dsv4p_nv', 'glm5_2_nv']
tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={...})
```
Post-restart 所有请求均显示双向 fallback。无 `(no fallback, 3model)` 模式。

### 6. 所有参数在 floor 值
FASTBREAK=1, EMPTY_200_FASTBREAK=1, BUDGET=114 >> max_single_tier=66s, CONNECT_RESERVE=0, MIN_OUTBOUND=0, KEY_COOLDOWN=25, TIER_COOLDOWN=25, INTEGRATE_COOLDOWN=0, FALLBACK_HEALTH=0.10, FORCE_STREAM=0, UPSTREAM=66, FORCE_STREAM_UPGRADE_TIMEOUT=66 (aligned)。

## 🚦 NOP 决策清单 (6 Gate)

### Gate 1: 所有 ATE 为 double-tier (post-restart)
Post-restart: 1 ATE, all tiers_tried_count=2 ✓
6h 窗口污染：32 single-tier pre-restart ATE 全部来自旧 bytecode — 代码级缺陷，已修复。

### Gate 2: 零 single-tier ATE (post-restart)
Post-restart: 0 single-tier ATE ✓
R819 code fix + R822 restart 已解决旧 bytecode NV-CYCLE 问题。

### Gate 3: NVCFPexecTimeout buffer ≥ 3s
dsv4p_nv NVCFPexecTimeout max=51,165ms, UPSTREAM=66s → buffer=14.8s ≥ 3s ✓
非绑定约束。零 NVCFPexecTimeout 在 glm5_2_nv（全部 400 DEGRADED）。

### Gate 4: FALLBACK_GRAPH 双向工作
`fallback_chain=['kimi_nv', 'dsv4p_nv', 'glm5_2_nv']` ✓
`tier_chain=['glm5_2_nv', 'dsv4p_nv']` (dynamic fallback) ✓
Post-restart 无 FALLBACK_GRAPH 消失。

### Gate 5: Fallback SR = 100%
7/7 fallback 100% SR ✓
Fallback 路径可靠。

### Gate 6: 所有参数在 floor
全部 12 个参数在 floor 值 ✓
UPSTREAM=66 非绑定，BUDGET=114 > max_single_tier=66s ample headroom。

**→ 6/6 Gates pass → Decision: NOP**

## 📋 决策: NOP

零参数修改，零 compose 修改，零容器重启。

**原因**:
1. Post-restart 数据稀疏（仅 2 请求），无法判定是否需要参数调整
2. glm5_2_nv NVCF DEGRADED 是上游问题，非配置可修复
3. dsv4p_nv 504 + NVCFPexecTimeout 是非绑定约束，504 是 NVCF 上游波动
4. 所有参数在 floor 值，任何修改非但无益反可能破坏当前基线
5. R819 NONCYCLE 代码修复已验证：400 → 立即 fallback (~1s)
6. FALLBACK_GRAPH 双向工作，Fallback SR 100%

**不改的项**:
- 所有 compose 参数不变
- config.py 不变（R819 代码修复已验证）
- 容器不重启
- 铁律: 只改 HM1 不改 HM2
- 本机 (HM2) 配置不变

**建议**: 下一轮应继续监控 post-restart 数据积累 + glm5_2_nv 函数恢复 + dsv4p_nv 504 频率。如果 NVCF 恢复且 SR 回升，保持 NOP。如果 504 频率上升且 NVCFPexecTimeout 趋近 UPSTREAM，考虑 UPSTREAM 调整。

## ⏳ 轮到 HM1 优化 HM2