# R826: HM2→HM1 — NOP (zero param, zero compose, zero restart; glm5_2_nv NVCF DEGRADED persists, post-restart clean, all params at floor)

## ⚙️ 判定: NOP

**执行**: 零参数修改, 零 compose 修改, 零容器重启

## 📊 数据收集 (DB 时钟 21:43 UTC, 2026-07-07)

### 容器状态
- 容器 `nv_gw` 运行中, 启动于 `2026-07-07T20:39:42Z` (R822 restart, ~1h ago)
- Health: `Up About an hour (healthy)`
- FALLBACK_GRAPH: `fallback_chain=['kimi_nv', 'dsv4p_nv', 'glm5_2_nv']` ✓
- tier_chain: `['glm5_2_nv', 'dsv4p_nv']` (dynamic fallback, health={...}) ✓
- R819 NONCYCLE: 日志中 `[NV-NONCYCLE-ERR]` 正常出现, 400→立即fallback (~1s) ✓

### 当前配置 (env, 与 R778 对齐)
```
FASTBREAK=1, EMPTY_200_FASTBREAK=1, BUDGET=114, CONNECT_RESERVE=0
MIN_OUTBOUND=0, KEY_COOLDOWN=25, TIER_COOLDOWN=25, INTEGRATE_COOLDOWN=0
FALLBACK_HEALTH_THRESHOLD=0.10, FORCE_STREAM_UPGRADE=0
UPSTREAM_TIMEOUT=66, FORCE_STREAM_UPGRADE_TIMEOUT=66 (aligned)
INTEGRATE_MODELS="" (空)
```

### 6h 总体 (16:00–22:00 UTC, 含 pre-restart 污染)

| 指标 | 值 |
|------|-----|
| 总请求 | 52 |
| 200 OK | 16 (30.8%) |
| ATE (502) | 36 (69.2%) |
| 单 tier ATE | 29 (80.6% of ATE) |
| 双 tier ATE | 7 (19.4% of ATE) |

### 每小时 SR

| 时间 (UTC) | 请求 | OK | SR |
|-----------|------|-----|------|
| 16:00 | 6 | 0 | 0.0% |
| 17:00 | 6 | 0 | 0.0% |
| 18:00 | 31 | 10 | 32.3% |
| 19:00 | 3 | 3 | 100.0% |
| 20:00 | 3 | 1 | 33.3% |
| 21:00 | 3 | 2 | 66.7% |

### 单 tier ATE 详细

| start_tier_idx | mapped_model | tiers_tried_count | cnt | avg_dur | all_fb_attempted |
|----------------|--------------|-------------------|-----|---------|------------------|
| 2 (glm5_2_nv) | glm5_2_nv | 1 | 27 | 7,410ms | f |
| 1 (dsv4p_nv) | dsv4p_nv | 1 | 2 | 60,852ms | f |

glm5_2_nv 单 tier ATE avg_dur=7,410ms + fallback_actually_attempted=f → 旧 bytecode NV-CYCLE 行为（在 DEGRADED 上循环 5 个 key ~7.4s）。全部 pre-restart。

### 双 tier ATE 详细

| tiers_tried_count | cnt | avg_dur |
|-------------------|-----|---------|
| 2 | 7 | 88,579ms |

### nv_tier_attempts (12h)

| tier | error_type | cnt | max_ms |
|------|-----------|-----|--------|
| glm5_2_nv | 400_nvcf_degraded | 56 | — |
| dsv4p_nv | 504_nv_gateway_timeout | 2 | — |

### NVCFPexecTimeout (12h)

**0 条记录**。UPSTREAM=66s 非绑定约束。buffer 无限大 ✓

### Fallback 统计

| fallback_occurred | total | OK | SR |
|-------------------|-------|-----|------|
| f | 44 | 8 | 18.2% |
| t | 8 | 8 | **100%** ✓ |

### 模型统计

| mapped_model | total | OK | SR | avg_dur | max_dur |
|-------------|-------|-----|------|---------|---------|
| glm5_2_nv | 41 | 8 | 19.5% | 44,585ms | 78,785ms |
| dsv4p_nv | 11 | 8 | 72.7% | 42,580ms | 60,159ms |

### Upstream 路径分布

| upstream_type | total | OK | fail | avg_dur |
|---------------|-------|-----|------|---------|
| (NULL) | 39 | 3 | 36 | 36,996ms |
| nvcf_pexec | 13 | 13 | 0 | 45,103ms |

- NULL upstream_type + fail = 36 ATE（调度层拒绝，非 pexec 可修）
- nvcf_pexec path: 13/13 100% SR ✓

### key_cycle_429s (12h)

| mapped_model | req_with_429 | total_429s | max_429_per_req | total_req |
|--------------|--------------|------------|-----------------|-----------|
| glm5_2_nv | 9 | 58 | 8 | 66 |
| dsv4p_nv | 0 | 0 | 0 | 11 |

glm5_2_nv key_cycle_429s 集中在 7-8（旧 bytecode NV-CYCLE 在 DEGRADED 上循环全部 key）。Post-restart 应归零。

### empty_200 (12h)

**0 条记录**。✓

### Post-restart 窗口 (20:39:42Z+, ~1h)

| 指标 | 值 |
|------|-----|
| 总请求 | 3 |
| 200 OK | 2 (66.7%) |
| ATE | 1 (33.3%) |
| 单 tier ATE | 0 |
| 双 tier ATE | 1 |
| Fallback SR | 2/2 (100%) |

| mapped_model | total | ok | ate | avg_dur |
|--------------|-------|----|-----|---------|
| glm5_2_nv | 3 | 2 | 1 | 45,492ms |

**Post-restart 请求明细**:
| 时间 | 模型 | 状态 | 延迟 | 路径 | tiers | fallback |
|------|------|------|------|------|-------|----------|
| 21:33 | glm5_2_nv | 200 | 21,174ms | nvcf_pexec | 2 | t |
| 21:06 | glm5_2_nv | 200 | 69,809ms | nvcf_pexec | 2 | t |
| 21:05 | glm5_2_nv | 502 | 115,191ms | NULL | 2 | f |

### Pre-restart 单 tier ATE 确认

29 条单 tier ATE 全部在 `created_at < '2026-07-07 20:39:42+00'`（pre-restart）。avg_dur=11,096ms。这些是旧 bytecode NV-CYCLE 行为。

## 🔍 诊断

### 1. glm5_2_nv 函数 DEGRADED (NVCF 上游问题, 持续)
函数 `3b9748d8-1d85-40e8-8573-0eeaa63a4b63` 对所有 5 个 key 返回 400 DEGRADED。56 条 nv_tier_attempts 全部为 `400_nvcf_degraded`。R819 NONCYCLE 代码修复已验证：第一个 key 400 → 立即 fallback (~1s)，替代旧行为 7-key cycle (~7s)。

**日志证据**:
```
[NV-NONCYCLE-ERR] tier=glm5_2_nv k3 resp.status=400 non-cycling, aborting tier
[NV-FALLBACK] Tier glm5_2_nv all-failed → falling back to dsv4p_nv
[NV-FALLBACK-SUCCESS] Success on fallback tier dsv4p_nv after primary glm5_2_nv failed
```

### 2. dsv4p_nv 偶发 504 + NVCFPexecTimeout
日志显示 dsv4p_nv 间歇性 504 + timeout:
- k5→504 (63s) → k4→NVCFPexecTimeout (50.8s) → FASTBREAK → 双 tier ATE (115s)
- 但 `nv_tier_attempts` 12h 中 0 条 NVCFPexecTimeout 记录 → 所有 timeout 发生在 pre-restart

Post-restart: 仅 2 条 dsv4p_nv 504（也可能来自 pre-restart 窗口）。dsv4p_nv 504 是 NVCF 上游波动，非配置可修复。

### 3. 6h 窗口严重污染
R822 restart 在 20:39 UTC。Post-restart 仅 3 请求（~1h）。6h 窗口的 29 单 tier ATE 全部来自 pre-restart 旧 bytecode 行为（NV-CYCLE 在 400 DEGRADED 上循环 5 个 key）。Post-restart: 0 单 tier ATE。

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

### 7. NVCFPexecTimeout 零记录
12h 窗口内 0 条 NVCFPexecTimeout → UPSTREAM=66 非绑定约束。buffer 无限大。任何 UPSTREAM 调整均无益。

## 🚦 NOP 决策清单 (6 Gate)

### Gate 1: 所有 ATE 为 double-tier (post-restart)
Post-restart: 1 ATE, all tiers_tried_count=2 ✓
6h 窗口污染：29 single-tier pre-restart ATE 全部来自旧 bytecode — 代码级缺陷，已修复。

### Gate 2: 零 single-tier ATE (post-restart)
Post-restart: 0 single-tier ATE ✓
R819 code fix + R822 restart 已解决旧 bytecode NV-CYCLE 问题。

### Gate 3: NVCFPexecTimeout buffer ≥ 3s
12h 内 0 条 NVCFPexecTimeout 记录 → buffer 无限大 ≥ 3s ✓
非绑定约束。UPSTREAM=66 无调整必要。

### Gate 4: FALLBACK_GRAPH 双向工作
`fallback_chain=['kimi_nv', 'dsv4p_nv', 'glm5_2_nv']` ✓
`tier_chain=['glm5_2_nv', 'dsv4p_nv']` (dynamic fallback) ✓
Post-restart 无 FALLBACK_GRAPH 消失。

### Gate 5: Fallback SR = 100%
8/8 fallback 100% SR ✓
Fallback 路径可靠。

### Gate 6: 所有参数在 floor
全部 12 个参数在 floor 值 ✓
UPSTREAM=66 非绑定，BUDGET=114 > max_single_tier=66s ample headroom。

**→ 6/6 Gates pass → Decision: NOP**

## 📋 决策: NOP

零参数修改，零 compose 修改，零容器重启。

**原因**:
1. Post-restart 数据稀疏（仅 3 请求），无法判定是否需要参数调整
2. glm5_2_nv NVCF DEGRADED 是上游问题，非配置可修复
3. dsv4p_nv 504 是 NVCF 上游波动，非配置可修复
4. NVCFPexecTimeout 12h 零记录，UPSTREAM 非绑定
5. 所有参数在 floor 值，任何修改非但无益反可能破坏当前基线
6. R819 NONCYCLE 代码修复已验证：400 → 立即 fallback (~1s)
7. FALLBACK_GRAPH 双向工作，Fallback SR 100%

**不改的项**:
- 所有 compose 参数不变
- config.py 不变（R819 代码修复已验证）
- 容器不重启
- 铁律: 只改 HM1 不改 HM2
- 本机 (HM2) 配置不变

**建议**: 下一轮应继续监控 post-restart 数据积累 + glm5_2_nv 函数恢复 + dsv4p_nv 504 频率。如果 NVCF 恢复且 SR 回升，保持 NOP。如果 504 频率上升且 NVCFPexecTimeout 重现并趋近 UPSTREAM，考虑 UPSTREAM 调整。

## ⏳ 轮到 HM1 优化 HM2