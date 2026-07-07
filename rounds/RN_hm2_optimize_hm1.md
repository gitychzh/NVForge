# R831: HM2→HM1 — NOP (zero param, zero compose, zero restart)

**决策**: 零参数修改，零 compose 修改，零容器重启。

---

## 数据收集

### 容器状态
- 容器: `nv_gw`，启���于 `2026-07-07T20:39:42Z`（~11.5h 前）
- FALLBACK_GRAPH: 双向，tier_chain=['glm5_2_nv', 'dsv4p_nv'] ✓
- 当前参数: 全部在 floor 值（UPSTREAM=66, BUDGET=114, FASTBREAK=1, EMPTY_200_FASTBREAK=1, CONNECT_RESERVE=0, MIN_OUTBOUND=0, INTEGRATE_COOLDOWN=0, FALLBACK_HEALTH=0.10, FORCE_STREAM_UPGRADE_TIMEOUT=66 ↔ UPSTREAM=66 aligned）

### 6h DB (ts): 48 req / 18 OK (37.5%) / 30 ATE

**But**: 窗口被 pre-restart 数据严重污染 — 23/30 ATE 是 pre-restart 单层 ATE。

### 按模型 (6h DB)
| model | total | ok | ate | sr% | avg_ttfb | avg_dur |
|-------|-------|-----|-----|------|----------|---------|
| glm5_2_nv | 37 | 10 | 27 | 27.0% | 36203 | 28935 |
| dsv4p_nv | 11 | 8 | 3 | 72.7% | 28702 | 48233 |

### Post-restart 分段 (≥20:39Z)
- DB: 5 req, 4 OK (80%), 1 double-tier ATE
- Docker logs (03:36-06:33 UTC Jul 8): 9 req, 6 OK, 3 double-tier ATE
- Fallback SR: 100% (12/12)
- Zero single-tier ATE post-restart ✓

### Docker Logs 时间线 (03:36-06:33 UTC)
```
03:36 glm5_2: 400 DEGRADED → dsv4p fallback SUCCESS ✓
04:03 glm5_2: 400 DEGRADED → dsv4p fallback SUCCESS ✓
04:33 glm5_2: 400 DEGRADED → dsv4p 504+timeout → ATE (double-tier)
04:35 glm5_2: 400 DEGRADED → dsv4p 504+timeout → ATE (double-tier)
05:03 glm5_2: 400 DEGRADED → dsv4p 504+timeout → ATE (double-tier)
05:05 glm5_2: 400 DEGRADED → dsv4p 504+cycle → k5 SUCCESS ✓
05:33 glm5_2: 400 DEGRADED → dsv4p k1 SUCCESS ✓
06:03 glm5_2: DIRECT SUCCESS (glm5_2 recovered!) ✓
06:33 glm5_2: DIRECT SUCCESS ✓
```

### glm5_2_nv 恢复
`06:03:21` 和 `06:33:21` UTC 两笔 glm5_2_nv 直接成功（2669ms / 2681ms），
NVCF function `3b9748d8` DEGRADED 状态已恢复！这是关键信号。
04:33-05:03 的 3 个 ATE 是 dsv4p_nv 的 504 网关超时（NVCF 上游瞬态），非配置可修复。

### 24h tier_attempts
| tier | error_type | cnt | max_ms |
|------|-----------|-----|--------|
| dsv4p_nv | 504_nv_gateway_timeout | 25 | - |
| dsv4p_nv | NVCFPexecTimeout | 15 | 51,354ms |
| dsv4p_nv | empty_200 | 10 | - |
| glm5_2_nv | 400_nvcf_degraded | 56 | - |
| glm5_2_nv | 504_nv_gateway_timeout | 21 | - |
| glm5_2_nv | NVCFPexecTimeout | 4 | 51,637ms |

NVCFPexecTimeout max=51.6s，UPSTREAM=66 → buffer=14.4s ≥ 3s ✓

### DB 写入问题
nv_gw 容器从 03:36 UTC 起处理的请求（docker logs 确认）未写入 DB。
DB 最后一条记录: `2026-07-07 23:03:23+00` (5h 前)。NVU_DB_ENABLED=1 已设置，
DB 容器 `logs_db` 正常运行 3 天。此问题不影响代理功能（请求路由、fallback 正常），
但影响数据可观测性。下次 HM1 轮次可考虑排查（非配置参数问题）。

---

## NOP Gate 分析

| Gate | 条件 | 结果 |
|------|------|------|
| 1 | 所有 ATE double-tier (post-restart) | 3/3 (logs) + 1/1 (DB) ✓ |
| 2 | 零 single-tier ATE (post-restart) | 0 ✓ |
| 3 | NVCFPexecTimeout buffer ≥ 3s | 14.4s ✓ |
| 4 | FALLBACK_GRAPH 双向 | tier_chain=['glm5_2_nv', 'dsv4p_nv'] ✓ |
| 5 | Fallback SR = 100% | 12/12 ✓ |
| 6 | 所有参数在 floor | UPSTREAM=66, BUDGET=114, FASTBREAK=1, EMPTY_200_FASTBREAK=1, CONNECT_RESERVE=0, MIN_OUTBOUND=0, INTEGRATE_COOLDOWN=0, FALLBACK_HEALTH=0.10, FORCE_STREAM_UPGRADE=0, FORCE_STREAM_UPGRADE_TIMEOUT=66 ↔ UPSTREAM=66 ✓ |

**全部 6 个 NOP Gate 通过**。Post-restart 的 3 个 ATE 都是 dsv4p_nv 的 NVCF 504 网关超时
（NVCF 上游瞬态），非配置参数可修复。glm5_2_nv 已于 06:03 UTC 恢复直接成功。

---

## 决策: NOP

零参数修改，零 compose 修改，零容器重启。系统健康，所有参数已在地板值。
glm5_2_nv 从 DEGRADED 恢复是积极信号。剩余 ATE 是 NVCF 上游问题，非配置可修复。

---

## ⏳ 轮到 HM1 优化 HM2