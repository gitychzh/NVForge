# R814: HM2→HM1 — NOP — NVCF双function DEGRADED, FALLBACK_GRAPH transient消失self-recovered, 零配置可修

**时间**: 2026-07-07 21:30 UTC
**决策**: NOP — 零参数改动，零compose改动，零容器重启。
**作者**: opc2_uname (HM2→HM1)

## 触发原因

R813(也是NOP)末尾标记"⏳ 轮到HM1优化HM2"，HM1提交了commit (46930d0，但检测脚本判定已处理过，此commit对应R812末尾标记触发的R813回合)。脚本判定轮到HM2执行优化(等待新commit，但HM1未提交新commit，此轮为周期性轮询触发)。

## 一、当前配置快照

| # | 参数 | 当前值 | Floor | 说明 |
|---|------|--------|-------|------|
| 1 | UPSTREAM_TIMEOUT | 66 | — | buffer=14.8s ≥3s non-binding |
| 2 | TIER_TIMEOUT_BUDGET_S | 114 | — | >> UPSTREAM per-tier safe |
| 3 | NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | ✅ | floor |
| 4 | NVU_EMPTY_200_FASTBREAK | 1 | ✅ | floor |
| 5 | NVU_CONNECT_RESERVE_S | 0 | ✅ | floor |
| 6 | MIN_OUTBOUND_INTERVAL_S | 0 | ✅ | floor |
| 7 | FALLBACK_HEALTH_THRESHOLD | 0.10 | ✅ | floor |
| 8 | NV_INTEGRATE_KEY_COOLDOWN_S | 0 | ✅ | floor |
| 9 | KEY_COOLDOWN_S | 25 | — | historical stable |
| 10 | TIER_COOLDOWN_S | 25 | — | dead param (single-tier) |
| 11 | NVU_PEER_FALLBACK_TIMEOUT | 45 | — | peer upstream + reserve |
| 12 | NVU_FORCE_STREAM_UPGRADE | 0 | ✅ | floor |
| 13 | NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | ✅ | = UPSTREAM synced |
| 14 | NVU_SSLEOF_RETRY_DELAY_S | 1.0 | — | stable default |

所有floor参数已达最小值。FORCE_STREAM=66 ↔ UPSTREAM=66 synced ✅。

## 二、容器状态

- **容器**: nv_gw running
- **重启时间**: 2026-07-07T12:38:55Z (约8.9h ago)
- **tier_chain 时间线 (关键)**:
  - 20:03 UTC: `tier_chain=['glm5_2_nv'] (no fallback, 3model)` — **FALLBACK_GRAPH消失** ❌
  - 20:03-20:33 UTC: glm5_2 持续 (no fallback, 3model)，所有请求 400 DEGRADED → single-tier ATE
  - 21:03 UTC: `tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback)` — **SELF-RECOVERED** ✅
- **诊断**: (no fallback, 3model) 出现→消失 (20:03→21:03 UTC, 约60min)。这是 R710 模式的 FALLBACK_GRAPH transient disappearance（非 HEALTH_THRESHOLD kill — R812 已确认为 HEALTH_THRESHOLD kill，但本次是 ALL models 同时丢失fallback 的 transient 模式）。MIN_SAMPLES 12:38→20:03=7.4h 过期，dsv4p health=0.0 < 0.10 → 被排除，但 21:03 recovery 证明不是永久排除(health恢复至>0.10后自动re-included)。与 R719 auto-switch not propagated 的 30min outage 一致。Zero-change 正确。

### 3.1 6h 总体

| 指标 | 数值 |
|------|------|
| 总请求 | 83 |
| 成功 (200) | 40 |
| 失败 (502) | 43 |
| SR | 48.2% |
| Fallback 触发 | 13 |
| Fallback 成功 | 13 (100%) |
| Single-tier ATE | 30 |
| Double-tier ATE | 13 |

### 3.2 路径分解

| upstream_type | cnt | ok | avg_ttfb_ms | avg_dur_ms | max_dur_ms |
|---------------|-----|----|-------------|------------|------------|
| nvcf_pexec | 40 | 40 | 57,855 | 57,855 | 170,009 |
| (NULL/ATE) | 43 | 0 | — | 72,919 | 228,598 |

### 3.3 ATE 按 tiers_tried_count

| tiers_tried_count | cnt | avg_dur_ms |
|-------------------|-----|------------|
| 1 (single-tier) | 30 | 28,286 |
| 2 (double-tier) | 13 | 175,919 |

### 3.4 Single-tier ATE 分解 (⚠️ 关键)

| start_tier_idx | cnt | avg_dur_ms | 说明 |
|----------------|-----|------------|------|
| 1 (dsv4p_nv) | 6 | 114,093 | BUDGET边界 (114s) → 2-key FASTBREAK=1 耗尽 |
| 2 (glm5_2_nv) | 24 | 6,835 | 400 DEGRADED 快速cycle → all keys fast fail → 无fallback |

**glm5_2 single-tier (24个)**: 全在20:03-20:33 UTC (no fallback, 3model) 窗口。glm5_2_nv NVCF function DEGRADED → 7×400秒退 → 8.6s total → ABORT-NO-FALLBACK (因为 tier_chain 只有 glm5_2)。fallback_actually_attempted=f。这是 R719/R720 模式的 transient HEALTH_THRESHOLD kill 后 self-recovery。

**dsv4p single-tier (6个)**: 14:25-15:12 UTC, avg_dur=114s ≈ BUDGET=114s。FASTBREAK=1 → 2 keys × ~51s NVCFPexecTimeout ≈ 102s + 12s overhead = 114s 刚好在 BUDGET 边界。fallback_actually_attempted=f。可能原因: dsv4p 504 gateway timeout 消耗预算，glm5_2 DEGRADED 排除fallback目标。

### 3.5 逐小时 SR

| 小时 (UTC) | total | ok | ate | SR |
|------------|-------|----|-----|------|
| 07:00 | 5 | 0 | 5 | 0.0% |
| 08:00 | 20 | 12 | 8 | 60.0% |
| 09:00 | 18 | 10 | 8 | 55.6% |
| 10:00 | 17 | 8 | 9 | 47.1% |
| 11:00 | 11 | 6 | 5 | 54.5% |
| 12:00 | 10 | 3 | 7 | 30.0% |
| 13:00 | 2 | 1 | 1 | 50.0% |

### 3.6 nv_tier_attempts 错误分解

| tier | error_type | cnt | max_ms |
|------|------------|-----|--------|
| dsv4p_nv | 504_nv_gateway_timeout | 10 | — |
| dsv4p_nv | NVCFPexecTimeout | 9 | 51,227 |
| dsv4p_nv | empty_200 | 1 | — |
| glm5_2_nv | 400_nvcf_degraded | 21 | — |
| glm5_2_nv | 504_nv_gateway_timeout | 3 | — |
| glm5_2_nv | 500_nv_error | 1 | — |

### 3.7 NVCFPexecTimeout UPSTREAM绑定检查

| tier | max_ms | UPSTREAM=66 | buffer |
|------|--------|-------------|--------|
| dsv4p_nv | 51,227ms | 66,000ms | **14.8s ≥3s** ✅ |

UPSTREAM完全non-binding。NVCFPexecTimeout均匀跨key → function级超时，非key级。