# R955: HM2→HM1 — NOP (false trigger, 72nd consecutive, 34/34 100% 6h SR, all params at floor, zero errors, zero ATE)

## 1. 触发分析

**cron 脚本输出**: `"这是我提交的, 不触发"`
- 最新 commit author = `opc2_uname` (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch pattern, R884→R955)
- 72nd consecutive false-trigger dispatch

## 2. 改前数据 (2026-07-09 10:40 UTC)

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
| max duration | 143,949ms |
| fallback_occurred | 2/34 (5.9%) |
| fallback 均成功 | 2/2 (100%) |
| avg fallback dur | 135,673ms |

### 2.2 24h 窗口

| 指标 | 值 |
|------|-----|
| 总 ATE | 1 (all_tiers_exhausted) |
| 非配置可修复 | 是 (NVCF upstream transient) |

### 2.3 ms_gw

| 指标 | 值 |
|------|-----|
| 总请求 | 0 |
| 零流量 | 是 |

### 2.4 Docker Logs (最近 100 行)

- tier_chain: `['glm5_2_nv', 'dsv4p_nv']` (dynamic fallback, health={...}) — 双向 fallback 工作正常
- 2 次 NV-TIER-FAIL → NV-FALLBACK → NV-FALLBACK-SUCCESS (glm5_2_nv→dsv4p_nv)
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
| ms_gw EMPTY_200_FASTBREAK_THRESHOLD | — | 3 | 对齐 |

**零漂移**: 所有参数 compose ↔ env 完全一致。

### 2.6 容器状态

```
nv_gw: Up 6 hours (healthy)
```

## 3. 参数状态评估

| 参数 | 当前值 | Floor | 理由 | 决策 |
|------|--------|-------|------|------|
| UPSTREAM_TIMEOUT | 64 | ~25s | 零 ATE，glm5_2_nv max=143,949ms 走 fallback 成功 | 不变 |
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
| ms_gw EMPTY_200_FASTBREAK_THRESHOLD | 3 | 1 | R900 floor，零流量 | 不变 |

## 4. 决策: NOP

**所有参数已达最优值或 floor。6h 100% SR (34/34)，零错误，零 ATE，零漂移。**

- nv_gw: 100% SR, 零 error, 零 ATE (6h window)
- ms_gw: 0 req (零流量), 零 error
- 24h 仅 1 次 ATE (NVCF upstream transient, not config-fixable)
- 所有参数 compose ↔ env 一致，零漂移
- 72nd consecutive false-trigger dispatch (R884→R955)
- 无任何优化空间 — 等待 NVCF function 健康度变化或流量模式变化信号

## 5. 参数变更: 无

零参数变更。本轮纯 NOP。

## ⏳ 轮到HM1优化HM2
