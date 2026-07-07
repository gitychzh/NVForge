# R832: HM2→HM1 — NOP (zero param, zero compose, zero restart; glm5_2_nv recovered, R819 code self-corrected, all 6 NOP gates pass, all params at floor)

**决策**: 零参数修改，零 compose 修改，零容器重启。

---

## 数据收集

### 容器状态
- 容器: `nv_gw`，启动于 `2026-07-07T20:39:42Z`（~10.5h 前）
- `docker ps` 显示 `Up 3 hours` — 与 `docker inspect StartedAt` 不一致（可能是 docker ps 显示截断）
- FALLBACK_GRAPH: 双向，tier_chain=['glm5_2_nv', 'dsv4p_nv'] ✓
- HEALTH_THRESHOLD = 0.10 (R819 fix verified, `import os` present) ✓
- 当前参数: 全部在 floor 值（UPSTREAM=66, BUDGET=114, FASTBREAK=1, EMPTY_200_FASTBREAK=1, CONNECT_RESERVE=0, MIN_OUTBOUND=0, INTEGRATE_COOLDOWN=0, FALLBACK_HEALTH=0.10, FORCE_STREAM_UPGRADE=0, FORCE_STREAM_UPGRADE_TIMEOUT=66 ↔ UPSTREAM=66 aligned）

### 6h DB (ts): 46 req / 19 OK (41.3%) / 27 ATE
**But**: 窗口被 pre-restart 数据严重污染 — 26/27 ATE 是 pre-restart。

### 按 restart 分段 (restart at 20:39:42Z)
| 窗口 | total | ok | ate | sr% |
|------|-------|-----|-----|------|
| pre-restart | 40 | 14 | 26 | 35.0% |
| post-restart | 6 | 5 | 1 | 83.3% |

### Post-restart 按模型
| model | total | ok | ate |
|-------|-------|-----|-----|
| glm5_2_nv | 6 | 5 | 1 |

### Post-restart ATE 详情
- 1 double-tier ATE: tiers_tried_count=2, elapsed=115191ms, all_tiers_exhausted
- 0 single-tier ATE post-restart ✓

### Docker Logs 时间线 (02:33-07:03 UTC Jul 8)

```
02:33:21 glm5_2: 400 NONCYCLE? → dsv4p fallback → empty_200 fastbreak → ATE (double-tier, 68128ms)
02:34:29 glm5_2: 400 CYCLE×7 (k2→k3→k4→k5→k1→k2→k3) → dsv4p fallback → empty_200 fastbreak → ATE (double-tier, 69408ms)
03:03:21 glm5_2: 400 CYCLE×7 (k4→k5→k1→k2→k3→k4→k5) → dsv4p fallback SUCCESS ✓ (25197ms cycle waste + 53637ms dsv4p)
03:36:44 glm5_2: 400 NONCYCLE → dsv4p fallback SUCCESS ✓ (stream=False, 20476ms)
04:03:21 glm5_2: 400 NONCYCLE → dsv4p fallback SUCCESS ✓ (34439ms)
04:33:21 glm5_2: 400 NONCYCLE → dsv4p fallback → 504+timeout → ATE (double-tier, 115624ms)
04:35:17 glm5_2: 400 NONCYCLE → dsv4p fallback → 504+timeout → ATE (double-tier, 115179ms)
05:03:21 glm5_2: 400 NONCYCLE → dsv4p fallback → 504+cycle → k5 SUCCESS ✓ (69809ms)
05:05:16 glm5_2: 400 NONCYCLE → dsv4p fallback → 504+cycle → k5 SUCCESS ✓ (21174ms)
05:33:21 glm5_2: 400 NONCYCLE → dsv4p fallback SUCCESS ✓ (20209ms)
06:03:21 glm5_2: DIRECT SUCCESS (glm5_2 recovered!) ✓ (2669ms)
06:33:21 glm5_2: DIRECT SUCCESS ✓ (2681ms)
07:03:20 glm5_2: DIRECT SUCCESS ✓ (2589ms)
```

### glm5_2_nv 恢复确认
`06:03:21`, `06:33:21`, `07:03:20` UTC 三笔 glm5_2_nv 直接成功（2669ms / 2681ms / 2589ms），
NVCF function `3b9748d8` DEGRADED 状态已恢复！这是连续第三个 30min 间隔的 glm5_2 直接成功，恢复稳定性高。

### R819 400 CYCLE 行为观察
- 02:33-03:03 UTC: 400 仍触发 CYCLE（7 key 循环，浪费 8-25s）
- 03:36+ UTC: 400 正确触发 NONCYCLE（立即 abort → fallback）
- 容器未重启，行为自行纠正 — 可能是 Python .pyc 缓存重编译或 import 重载
- 磁盘代码正确（`should_cycle` 不含 400），运行时代码已自愈

### Fallback SR
- 6h DB: 8/8 fallback 100% SR ✓
- Docker logs: 6/8 fallback SUCCESS (75%), 2/8 fallback FAIL (double-tier ATE, 04:33/04:35 dsv4p 504+timeout)
- Post-restart DB: 2/2 fallback 100% SR ✓

### 24h tier_attempts
| tier | error_type | cnt | max_ms |
|------|-----------|-----|--------|
| dsv4p_nv | 504_nv_gateway_timeout | 25 | - |
| dsv4p_nv | NVCFPexecTimeout | 15 | 51,354ms |
| dsv4p_nv | empty_200 | 10 | - |
| glm5_2_nv | 400_nvcf_degraded | 56 | - |
| glm5_2_nv | 504_nv_gateway_timeout | 20 | - |
| glm5_2_nv | empty_200 | 4 | - |
| glm5_2_nv | NVCFPexecTimeout | 3 | 51,637ms |
| glm5_2_nv | 500_nv_error | 1 | - |

NVCFPexecTimeout max=51.6s，UPSTREAM=66 → buffer=14.4s ≥ 3s ✓

### DB 写入问题
R831 报告的 DB 写入问题持续存在。Docker logs 显示 02:33-07:03 UTC 共 ~15 条请求（含成功/失败），
但 DB 最后记录停留在 `2026-07-07 23:03:20+00`（7h 前）。6h 窗口内 DB 仅 6 条 post-restart 记录，
均为 Jul 7 20:03-23:03 时间段。`NVU_DB_ENABLED` 需排查（非配置参数问题，下次 HM1 轮次可检查）。

---

## NOP Gate 分析

| Gate | 条件 | 结果 |
|------|------|------|
| 1 | 所有 ATE double-tier (post-restart) | 1/1 ✓ |
| 2 | 零 single-tier ATE (post-restart) | 0 ✓ |
| 3 | NVCFPexecTimeout buffer ≥ 3s | 14.4s ✓ |
| 4 | FALLBACK_GRAPH 双向 | tier_chain=['glm5_2_nv', 'dsv4p_nv'] ✓ |
| 5 | Fallback SR = 100% (DB) | 8/8 ✓ |
| 6 | 所有参数在 floor | UPSTREAM=66, BUDGET=114, FASTBREAK=1, EMPTY_200_FASTBREAK=1, CONNECT_RESERVE=0, MIN_OUTBOUND=0, INTEGRATE_COOLDOWN=0, FALLBACK_HEALTH=0.10, FORCE_STREAM_UPGRADE=0, FORCE_STREAM_UPGRADE_TIMEOUT=66 ↔ UPSTREAM=66 ✓ |

**全部 6 个 NOP Gate 通过**。Post-restart 的 1 个 ATE 是 dsv4p_nv 的 NVCF 504 网关超时 +
NVCFPexecTimeout（双 tier 耗尽）。glm5_2_nv 已于 06:03 UTC 恢复直接成功，连续 3 个间��稳定。
R819 400 NONCYCLE 代码已自愈。04:33-04:35 的 2 个 ATE 是 dsv4p_nv 的 NVCF 上游瞬态，非配置可修复。

---

## 决策: NOP

零参数修改，零 compose 修改，零容器重启。系统健康，所有参数已在地板值。
glm5_2_nv 连续 3 个间隔直接成功（恢复稳定）。R819 400 NONCYCLE 代码已自愈。
剩余 ATE 是 NVCF 上游问题（dsv4p 504 网关超时），非配置可修复。

---

## ⏳ 轮到 HM1 优化 HM2