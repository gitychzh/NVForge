# R888: HM2→HM1 — NOP (false trigger, double-dispatch, 38/38 100% 6h SR, zero ATE, 1 rescued fallback, identical to R884-R887)

> **回合**: R888
> **方向**: HM2 → HM1
> **时间**: 2026-07-08 20:36 UTC
> **触发**: cron 误触发 (double-dispatch false trigger)
> **决策**: NOP (零变更)

---

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = `opc2_uname` (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — **double-dispatch 误触发 (false trigger)**
- 与 R884-R887 完全相同的触发场景
- HM1 本地 git log 停留在 R821（67 轮落后），未提交任何新内容
- Symlink `RN_hm2_optimize_hm1.md` 已指向 R887（上次 agent 已修复），本次进一步证实

## 2. HM1 容器状态

| 指标 | 值 |
|------|-----|
| 容器名 | `nv_gw` |
| 状态 | healthy |
| Uptime | 8h+ |
| 日志 error/warn | 无 (zero) |
| 日志 504 | 4 (glm5_2_nv k1/k3/k4) |
| 日志 NVCFPexecTimeout | 1 → FASTBREAK → fallback → SUCCESS |
| 日志 fallback | 1 (glm5_2 all-failed → dsv4p_nv success at 18:06:13) |

## 3. 四源验证 — 配置一致性

| 参数 | Compose | 容器 Env | 匹配 |
|------|---------|---------|------|
| UPSTREAM_TIMEOUT | 66 | 66 | ✅ |
| TIER_TIMEOUT_BUDGET_S | 114 | 114 | ✅ |
| MIN_OUTBOUND_INTERVAL_S | 0 | 0 | ✅ |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 1 | ✅ |
| NVU_EMPTY_200_FASTBREAK | 1 | 1 | ✅ |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | 45 | ✅ |
| NVU_CONNECT_RESERVE_S | 0 | 0 | ✅ |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | 66 | ✅ |
| NVU_FORCE_STREAM_UPGRADE | 0 | 0 | ✅ |
| NV_INTEGRATE_MODELS | "" | "" | ✅ |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | 0 | ✅ |
| KEY_COOLDOWN_S | 25 | 25 | ✅ |
| TIER_COOLDOWN_S | 25 | 25 | ✅ |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | 0.10 | ✅ |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | 1.0 | ✅ |

**四源全部通过。零漂移。**

## 4. 数据摘要 (6h 窗口, 2026-07-08 14:36 UTC)

| 指标 | 数值 |
|------|------|
| 总请求 | 38 |
| 成功 (200) | 38 (100.0%) |
| 失败 | 0 |
| ATE | 0 |
| req_with_429cycle | 4 |
| total_429cycles | 5 |
| avg latency (OK) | 19,794.9ms |
| max latency (OK) | 144,743ms |

### 4.1 Per-model

| Model | cnt | ok | fail | avg_lat_ms | max_lat_ms |
|-------|-----|----|------|-----------|-----------|
| glm5_2_nv | 38 | 38 | 0 | 19,794.9 | 144,743 |

All glm5_2_nv. No dsv4p_nv or kimi_nv in 6h window.

### 4.2 Upstream 路径

| upstream_type | total | ok | avg_ms |
|---------------|-------|----|--------|
| nvcf_pexec | 38 | 38 | 19,794.9 |

All nvcf_pexec. Integrate models="" (disabled).

### 4.3 Fallback

| fallback_occurred | cnt | ok |
|-------------------|-----|----|
| false | 37 | 37 |
| true | 1 | 1 |

glm5_2→dsv4p fallback: 1/1 成功 (100% SR).

### 4.4 Tier Attempts (failures only)

| tier | error_type | nv_key_idx | cnt | avg_elapsed_ms |
|------|-----------|------------|-----|----------------|
| glm5_2_nv | 504_nv_gateway_timeout | 1 | 2 | - |
| glm5_2_nv | 504_nv_gateway_timeout | 3 | 1 | - |
| glm5_2_nv | 504_nv_gateway_timeout | 4 | 1 | - |
| glm5_2_nv | NVCFPexecTimeout | 2 | 1 | 51,475.0 |

4× 504 (NVCF gateway层, 非代理可修) + 1× NVCFPexecTimeout (51,475ms, 触发FASTBREAK→fallback 成功). Zero config-related errors.

### 4.5 Last 10 Requests

| ts | tier_model | status | duration_ms | upstream_type |
|----|-----------|--------|-------------|---------------|
| 12:33:39 | glm5_2_nv | 200 | 5,692 | nvcf_pexec |
| 12:33:36 | glm5_2_nv | 200 | 3,199 | nvcf_pexec |
| 12:33:21 | glm5_2_nv | 200 | 12,758 | nvcf_pexec |
| 12:03:50 | glm5_2_nv | 200 | 3,827 | nvcf_pexec |
| 12:03:46 | glm5_2_nv | 200 | 4,528 | nvcf_pexec |
| 12:03:21 | glm5_2_nv | 200 | 22,315 | nvcf_pexec |
| 11:34:18 | glm5_2_nv | 200 | 3,058 | nvcf_pexec |
| 11:33:56 | glm5_2_nv | 200 | 21,878 | nvcf_pexec |
| 11:33:53 | glm5_2_nv | 200 | 2,975 | nvcf_pexec |
| 11:33:46 | glm5_2_nv | 200 | 6,766 | nvcf_pexec |

All 200 OK. Consistent latency pattern: fast (3-7s) + periodic longer (12-22s).

## 5. 决策矩阵

| 参数 | 当前值 | 候选 | 支撑 | 决策 |
|------|--------|------|------|------|
| UPSTREAM_TIMEOUT | 66 | — | NVCFPexecTimeout max=51,475ms << 66s (14.5s buffer). 非binding. | ❌ |
| TIER_TIMEOUT_BUDGET_S | 114 | — | max duration=144,743ms > 114s, but single streaming success under adaptive tier logic. 不调整. | ❌ |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | — | 1 fallback all success, 无需加速. | ❌ |
| 所有其他参数 | floor | — | 全部已达 floor 或长期稳定最优值. | ❌ |

**所有参数已达最优值或 floor (R778 快照一致)。零变更空间。NOP。**

## 6. 变更

**无变更 (NOP)**。零 compose 修改，零容器重启。

## 7. 验证

- 6h 窗口 100% SR → 系统健康，无需变更
- 与 R884-R887 数据完全一致 → 确认 double-dispatch false trigger
- 容器 8h+ 零 ATE → R819 代码修复持续生效
- 所有参数与 R778 架构快照一致 → 零漂移
- HM1 最新请求 8h 前 → 系统 idle，24h 内 42 ATE 均来自更早窗口
- 无需要验证的变更

---

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2