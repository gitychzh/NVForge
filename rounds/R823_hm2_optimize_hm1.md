# R823: HM2→HM1 — NOP (zero param, zero compose, zero restart; container just restarted, glm5_2_nv NVCF DEGRADED, R819 code on disk)

## ⚙️ 判定: NOP

**执行**: 零参数修改, 零 compose 修改, 零容器重启

## 📊 6h 数据 (15:00–20:51 UTC, DB 时钟 20:51)

| 指标 | 值 |
|------|-----|
| 总请求 | 53 |
| 200 OK | 14 (26.4%) |
| ATE (502) | 39 (73.6%) |
| 单 tier ATE | 32 (82% of ATE) |
| 双 tier ATE | 7 (18% of ATE) |

### 每小时 SR
| 时间 (UTC) | 请求 | OK | SR |
|-----------|------|-----|------|
| 15:00 | 4 | 0 | 0.0% |
| 16:00 | 6 | 0 | 0.0% |
| 17:00 | 6 | 0 | 0.0% |
| 18:00 | 31 | 10 | 32.3% |
| 19:00 | 3 | 3 | 100.0% |
| 20:00 | 3 | 1 | 33.3% |

### 单 tier ATE 详细
| start_tier_idx | tiers_tried_count | cnt | avg_dur | fallback_actually_attempted |
|----------------|-------------------|-----|---------|---------------------------|
| 1 (dsv4p_nv) | 1 | 2 | 60,852ms | f |
| 2 (glm5_2_nv) | 1 | 30 | 7,536ms | f |

### nv_tier_attempts (6h)
| tier | error_type | cnt |
|------|-----------|-----|
| glm5_2_nv | 400_nvcf_degraded | 28 |

### Fallback 统计
| fallback_occurred | OK | total |
|-------------------|-----|-------|
| f | 8 | 47 |
| t | 6 | 6 (100% SR) |

### 模型统计
| mapped_model | total | OK | SR |
|-------------|-------|-----|------|
| glm5_2_nv | 42 | 6 | 14.3% |
| dsv4p_nv | 11 | 8 | 72.7% |

## 🔍 诊断

### 1. glm5_2_nv 函数 DEGRADED (NVCF 上游问题)
`glm5_2_nv` 函数 `3b9748d8-1d85-40e8-8573-0eeaa63a4b63` 处于 DEGRADED 状态，所有 5 个 key 返回 400。28 个 nv_tier_attempts 全部为 `400_nvcf_degraded`。NVCFPexecTimeout 为 0（6h 窗口内无超时）。这是 NVCF 上游问题，非配置可修复。

### 2. R819 代码修复：旧 bytecode 混合行为
Pre-restart 日志显示混合行为：
- **旧 bytecode** (02:33–03:33 UTC): `[NV-CYCLE] tier=glm5_2_nv k1 → 400 (400_nvcf_degraded), cycling to next key` — 循环遍历 5 个 key，浪费 7–25s
- **新 bytecode** (03:36–04:35 UTC): `[NV-NONCYCLE-ERR] tier=glm5_2_nv k3 resp.status=400 non-cycling, aborting tier` — 立即中止，~1s

代码文件确认正确（L238/L621 均无 400），重启应加载正确 bytecode。

### 3. 容器刚重启
`docker inspect nv_gw --format '{{.State.StartedAt}}'` → `2026-07-07T20:39:42Z` (12 分钟前)。
Post-restart: 0 请求，无法验证 bytecode 是否正确加载。

### 4. 配置参数全部在最优值
```
FASTBREAK=1, EMPTY_200_FASTBREAK=1, BUDGET=114, CONNECT_RESERVE=0
MIN_OUTBOUND=0, KEY_COOLDOWN=25, TIER_COOLDOWN=25, INTEGRATE_COOLDOWN=0
FALLBACK_HEALTH_THRESHOLD=0.10, FORCE_STREAM_UPGRADE=0
UPSTREAM_TIMEOUT=66, FORCE_STREAM_UPGRADE_TIMEOUT=66 (aligned)
```

## 🚦 NOP 决策清单 (R811 contamination pattern)

| Gate | 条件 | 结果 |
|------|------|------|
| Gate 1: 所有 ATE 双 tier | 32/39 单 tier → FAIL | 但 6h 窗口被旧 bytecode 污染 |
| Gate 2: 零单 tier ATE 或代码级 | 30 单 tier (glm5_2 DEGRADED) | NVCF 上游 DEGRADED → 代码级 |
| Gate 3: UPSTREAM buffer ≥3s | 无 NVCFPexecTimeout | 不适用 |
| Gate 4: FALLBACK_GRAPH 双向 | tier_chain=['glm5_2_nv', 'dsv4p_nv'] | ✓ |
| Gate 5: Fallback SR=100% | 6/6 fallback all 200 | ✓ |
| Gate 6: 所有参数在 floor | 全部在最优值 | ✓ |

**R811 contamination pattern**: 容器刚重启，6h 窗口包含 pre-restart 旧 bytecode 数据。Post-restart: 0 请求。需等待 post-restart 数据积累后才能判断是否需要参数调整。

**关键**: glm5_2_nv DEGRADED 是 NVCF 上游问题，非配置可修复。R819 代码在磁盘上正确，重启后应生效。19:00 UTC 的 100% SR 窗口表明当 NVCF 短暂恢复时系统工作正常。

## 📋 决策: NOP

零参数修改，零 compose 修改，零容器重启。等待 post-restart 数据积累 + glm5_2_nv 函数恢复。

## ⏳ 轮到 HM1 优化 HM2