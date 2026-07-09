# R957: HM2→HM1 — NOP (false trigger, 74th consecutive, 34/34 100% 6h SR, all params at floor, zero errors, zero ATE)

## 1. 触发分析

**cron 脚本输出**: `"这是我提交的, 不触发"`
- 最新 commit author = `opc2_uname` (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch pattern, R884→R957)
- 74th consecutive false-trigger dispatch

## 2. 改前数据 (2026-07-09 11:00 UTC)

### 2.1 6h 窗口 (nv_gw)

| 指标 | 值 |
|------|-----|
| 总请求 | 34 |
| 成功 (200) | 34 |
| 失败 | 0 |
| SR | **100.0%** |
| 错误类型 | 0 errors |
| upstream_type | 全部 nvcf_pexec |
| avg duration | 22,050ms |
| avg ttfb | 22,049ms |
| max duration | 143,949ms |
| fallback_occurred | 2/34 (5.9%) |
| fallback 均成功 | 2/2 (100%) |
| avg fallback dur | 135,673ms |
| avg_429 | 0.1 |

### 2.2 24h 窗口

| 指标 | 值 |
|------|-----|
| 总请求 | 194 |
| 成功 (200) | 193 |
| 失败 | 1 |
| SR | 99.5% |
| 仅 1 次 ATE | all_tiers_exhausted, 2026-07-08 13:21 UTC, 121s, NVCF upstream transient, not config-fixable |

### 2.3 每小时 SR (6h)

| 小时 (UTC) | 总 | OK | ATE | SR |
|-----------|-----|-----|-----|------|
| 2026-07-08 21:00 | 3 | 3 | 0 | 100.0% |
| 2026-07-08 22:00 | 8 | 8 | 0 | 100.0% |
| 2026-07-08 23:00 | 6 | 6 | 0 | 100.0% |
| 2026-07-09 00:00 | 6 | 6 | 0 | 100.0% |
| 2026-07-09 01:00 | 7 | 7 | 0 | 100.0% |
| 2026-07-09 02:00 | 3 | 3 | 0 | 100.0% |

### 2.4 Docker Logs (最近 200 行)

- tier_chain: `['glm5_2_nv', 'dsv4p_nv']` (dynamic fallback, health={...}) — 双向 fallback 工作正常
- glm5_2_nv 大部分 first-key 成功 (3-22s)，少数空 200 cycle 换 key 救回
- 2 次 10:03-10:05 UTC: glm5_2_nv k4→504 gateway timeout → k5→NVCFPexecTimeout 51,313-51,498ms → fastbreak → fallback to dsv4p_nv → 成功 (13.4-29.9s)
- 2 次 10:33-10:35 UTC: glm5_2_nv k1→504 gateway timeout → k2→NVCFPexecTimeout 51,498ms → fastbreak → fallback to dsv4p_nv → 成功 (13.4s)
- 1 次 09:35-09:37 UTC: glm5_2_nv k3 empty_200 → cycle k4 → 成功 (51.6s total)
- NVCFPexecTimeout max=51,498ms << UPSTREAM=64s — 非绑定约束
- 零 ERROR/WARN，零 ATE 痕迹

### 2.5 容器环境 vs Compose

| 参数 | 容器 env | Compose | 状态 |
|------|---------|---------|------|
| UPSTREAM_TIMEOUT | 64 | 64 | 对齐 |
| TIER_TIMEOUT_BUDGET_S | 114 | 114 | 对齐 |
| MIN_OUTBOUND_INTERVAL_S | 0 | 0 | 对齐 (floor) |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 1 | 对齐 (floor) |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | 45 | 对齐 |
| NVU_EMPTY_200_FASTBREAK | 3 | 3 | 对齐 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 | 64 | 对齐 (与 UPSTREAM=64 一致) |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | 0.05 | 对齐 |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | 60 | 对齐 |
| KEY_COOLDOWN_S | 25 | 25 | 对齐 |
| TIER_COOLDOWN_S | 25 | 25 | 对齐 |
| NVU_CONNECT_RESERVE_S | 0 | 0 | 对齐 (floor) |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | 0 | 对齐 (floor) |

**零漂移**: 所有参数 compose ↔ env 完全一致。

### 2.6 容器状态

```
nv_gw: Up 6 hours (healthy)
```

### 2.7 nv_tier_attempts (6h)

| tier | error_type | cnt | avg_ms | max_ms |
|------|-----------|-----|--------|--------|
| glm5_2_nv | 504_nv_gateway_timeout | 2 | — | — |
| glm5_2_nv | NVCFPexecTimeout | 2 | 51,406 | 51,498 |
| glm5_2_nv | empty_200 | 1 | — | — |

NVCFPexecTimeout max=51,498ms << UPSTREAM=64s — 非绑定约束。仅 2 次超时在 6h 窗口均被 fallback 成功救回。

## 3. 参数状态评估

| 参数 | 当前值 | Floor | 理由 | 决策 |
|------|--------|-------|------|------|
| UPSTREAM_TIMEOUT | 64 | ~25s | NVCFPexecTimeout max=51,498ms << 64s, 非绑定 | 不变 |
| TIER_TIMEOUT_BUDGET_S | 114 | — | 100% SR 零 ATE | 不变 |
| MIN_OUTBOUND_INTERVAL_S | 0 | 0 | 已达 floor | 不变 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 1 | 已达 floor | 不变 |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | 25 | 零 ATE | 不变 |
| NVU_EMPTY_200_FASTBREAK | 3 | 1 | R829 止血设置，零错误期稳定 | 不变 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 | — | 与 UPSTREAM=64 对齐，零漂移 | 不变 |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | 0.0 | 安全地板，零误杀 | 不变 |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | — | 防御性参数，零 auth-fail | 不变 |
| TIER_COOLDOWN_S | 25 | — | KEY=TIER=25 对齐，零 429 | 不变 |
| NVU_CONNECT_RESERVE_S | 0 | 0 | 已达 floor | 不变 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | 0 | 已达 floor | 不变 |

## 4. 决策: NOP

**所有参数已达最优值或 floor。6h 100% SR (34/34)，24h 99.5% SR (193/194)，零错误，零 ATE，零漂移。**

- nv_gw: 100% SR, 零 error, 零 ATE (6h window)
- 每小时 SR: 100.0% 连续 6 小时
- 24h 仅 1 次 ATE (NVCF upstream transient, not config-fixable)
- NVCFPexecTimeout max=51,498ms << UPSTREAM=64s — 非绑定，无需调整
- 所有参数 compose ↔ env 一致，零漂移
- 74th consecutive false-trigger dispatch (R884→R957)
- 无任何优化空间 — 等待 NVCF function 健康度变化或流量模式变化信号

## 5. 参数变更: 无

零参数变更。本轮纯 NOP。

## ⏳ 轮到HM1优化HM2