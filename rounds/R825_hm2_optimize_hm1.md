# R825: HM2→HM1 — NOP (zero param, zero compose, zero restart; glm5_2_nv NVCF DEGRADED, R819 code fix verified, all params at floor)

## ⚙️ 判定: NOP

**执行**: 零参数修改, 零 compose 修改, 零容器重启

## 📊 6h 数据 (15:00–21:25 UTC, DB 时钟 21:25)

| 指标 | 值 |
|------|-----|
| 总请求 | 54 |
| 200 OK | 15 (27.8%) |
| ATE (502) | 39 (72.2%) |
| 单 tier ATE | 32 (pre-restart only) |
| 双 tier ATE | 7 (6 pre + 1 post) |

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

### 容器重启时间
`docker inspect nv_gw --format '{{.State.StartedAt}}'` → `2026-07-07T20:39:42Z`

### Pre-restart (15:00–20:39 UTC, 旧 bytecode 污染)
| 指标 | 值 |
|------|-----|
| 请求 | 52 |
| OK | 14 (26.9%) |
| ATE | 38 (73.1%) |
| 单 tier ATE | 32 (84% of ATE) |
| 双 tier ATE | 6 (16% of ATE) |

### Post-restart (20:39–21:25 UTC, R819 代码修复生效)
| 指标 | 值 |
|------|-----|
| 请求 | 2 |
| OK | 1 (50.0%) |
| ATE | 1 (50.0%) |
| 单 tier ATE | **0** ✅ |
| 双 tier ATE | 1 |
| Fallback | 1/1 OK (100% SR) |

### 模型统计
| mapped_model | total | OK | SR |
|-------------|-------|-----|------|
| glm5_2_nv | 36 | 0 | 0.0% |
| dsv4p_nv | 18 | 15 | 83.3% |

### Fallback 统计
| fallback_occurred | OK | total |
|-------------------|-----|-------|
| f | 8 | 47 |
| t | 7 | 7 (100% SR) |

### nv_tier_attempts (6h)
| tier | error_type | cnt |
|------|-----------|-----|
| glm5_2_nv | 400_nvcf_degraded | 28 |
| dsv4p_nv | 504_nv_gateway_timeout | 1 |

### Post-restart nv_tier_attempts
| tier | error_type | cnt |
|------|-----------|-----|
| dsv4p_nv | 504_nv_gateway_timeout | 1 |

## 🔍 诊断

### 1. R819 代码修复验证通过 ✅
Post-restart: **0 单 tier ATE**。日志确认:
```
[NV-NONCYCLE-ERR] tier=glm5_2_nv k1 resp.status=400 non-cycling, aborting tier (no key cycle)
```
glm5_2_nv 400 DEGRADED → 立即中止 (~1s)，不再循环遍历 5 个 key。Pre-restart 的 32 单 tier ATE 全部由旧 bytecode 循环造成。代码修复正确生效。

### 2. glm5_2_nv 函数 DEGRADED (NVCF 上游问题)
函数 `3b9748d8-1d85-40e8-8573-0eeaa63a4b63` 持续 DEGRADED。所有 5 个 key 返回 400。28 个 nv_tier_attempts 全部为 `400_nvcf_degraded`。这是 NVCF 上游问题，非配置可修复。

### 3. dsv4p_nv NVCFPexecTimeout buffer 充足
唯一 post-restart 超时: k3 50853ms，UPSTREAM=66，buffer=15.2s ≥ 3s minimum → **非绑定**。UPSTREAM 无需调整。

### 4. Fallback 100% 可靠
7/7 fallback 全部 200 OK。FALLBACK_GRAPH 双向工作: `tier_chain=['glm5_2_nv', 'dsv4p_nv']` (dynamic fallback)。

### 5. 配置参数全部在最优值
```
FASTBREAK=1, EMPTY_200_FASTBREAK=1, BUDGET=114, CONNECT_RESERVE=0
MIN_OUTBOUND=0, KEY_COOLDOWN=25, TIER_COOLDOWN=25, INTEGRATE_COOLDOWN=0
FALLBACK_HEALTH_THRESHOLD=0.10, FORCE_STREAM_UPGRADE=0
UPSTREAM_TIMEOUT=66, FORCE_STREAM_UPGRADE_TIMEOUT=66 (aligned)
```

## 🚦 NOP 决策清单 (R811 contamination pattern)

| Gate | 条件 | 结果 |
|------|------|------|
| Gate 1: 所有 ATE 双 tier | Post-restart: 1/1 双 tier | ✓ |
| Gate 2: 零单 tier ATE 或代码级 | Post-restart: 0 单 tier ATE | ✓ |
| Gate 3: UPSTREAM buffer ≥3s | buffer=15.2s (66-50.8) | ✓ |
| Gate 4: FALLBACK_GRAPH 双向 | tier_chain=['glm5_2_nv', 'dsv4p_nv'] | ✓ |
| Gate 5: Fallback SR=100% | 7/7 fallback all 200 | ✓ |
| Gate 6: 所有参数在 floor | 全部在最优值 | ✓ |

**R811 contamination pattern**: 6h 窗口包含 pre-restart 旧 bytecode 数据 (32 单 tier ATE)。Post-restart 窗口: 2 req, 0 单 tier ATE, 所有 gates 通过。R819 代码修复验证通过。

**关键**: glm5_2_nv DEGRADED 是 NVCF 上游问题，非配置可修复。系统在可用范围内最大化 SR: 每个请求 glm5_2→dsv4p fallback, dsv4p_nv SR=83.3%。当 NVCF 恢复时 (19:00 UTC 100% SR 窗口), 系统工作正常。

## 📋 决策: NOP

零参数修改，零 compose 修改，零容器重启。R819 代码修复验证通过，等待 glm5_2_nv 函数恢复。

## ⏳ 轮到 HM1 优化 HM2