# R809: HM2→HM1 — NOP — 86.5% SR, 全参数floor, 双function NVCF 耗尽, 7连NOP稳态平台

**时间**: 2026-07-07 11:15 UTC
**决策**: NOP — 零参数改动，零compose改动，零容器重启。

## 触发原因

R808末尾标记"⏳ 轮到HM1优化HM2"，HM1提交了新commit (3d3347c)，检测脚本判定轮到HM2执行。

## 一、当前配置快照

| # | 参数 | HM1 当前值 | Floor? |
|---|------|------------|--------|
| 1 | `UPSTREAM_TIMEOUT` | 66 | — |
| 2 | `TIER_TIMEOUT_BUDGET_S` | 114 | — |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | ✅ floor |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | ✅ floor |
| 5 | `TIER_COOLDOWN_S` | 25 | — |
| 6 | `NVU_PEER_FALLBACK_TIMEOUT` | 45 | — |
| 7 | `NVU_CONNECT_RESERVE_S` | 0 | ✅ floor |
| 8 | `NVU_EMPTY_200_FASTBREAK` | 1 | ✅ floor |
| 9 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 66 | — |
| 10 | `NVU_FORCE_STREAM_UPGRADE` | 0 | ✅ floor |
| 11 | `FALLBACK_HEALTH_THRESHOLD` | 0.10 | ✅ floor |
| 12 | `NV_INTEGRATE_KEY_COOLDOWN_S` | 0 | ✅ floor |
| 13 | `KEY_COOLDOWN_S` | 25 | — |

FORCE_STREAM=66 ↔ UPSTREAM=66 synced ✅。

## 二、数据摘要（6h window, ≈05:00–11:00 UTC）

### 2.1 6h 总体

| 指标 | 数值 |
|------|------|
| 总请求 | 178 |
| 成功 (200) | 154 |
| 失败 (502) | **24** |
| SR | **86.5%** |
| Fallback 触发 | 33 |
| Fallback 成功 | 33 (100%) |
| Single-tier ATE | **0** |
| Double-tier ATE | 24 (100%) |

### 2.2 Model-level SR

| request_model | total | ok | SR% | avg_ok_dur_ms |
|---|---|---|---|---|
| glm5_2_nv | 122 | 110 | 90.2% | 29,058 |
| dsv4p_nv | 56 | 44 | 78.6% | 92,421 |

### 2.3 逐小时 SR

| 小时 (UTC) | total | ok | ate | SR |
|---|---|---|---|---|
| 05:00 | 4 | 4 | 0 | 100.0% |
| 06:00 | 12 | 10 | 2 | 83.3% |
| 07:00 | 5 | 4 | 1 | 80.0% |
| 08:00 | 12 | 12 | 0 | 100.0% |
| 09:00 | 12 | 10 | 2 | 83.3% |
| 10:00 | 10 | 8 | 2 | 80.0% |
| 11:00 | 1 | 1 | 0 | 100.0% |

### 2.4 NVCF Function Health

| Function | Health | Status |
|---|---|---|
| dsv4p_nv 74f02205 | 0.10–0.15 | 低但未死, NVCF 缓慢恢复中 |
| glm5_2_nv 3b9748d8 | 0.80–0.90 | 健康 |

### 2.5 nv_tier_attempts 错误分解

| tier | error_type | cnt | max_ms |
|---|---|---|---|
| dsv4p_nv | 504_nv_gateway_timeout | 25 | — |
| dsv4p_nv | NVCFPexecTimeout | 17 | 51,354 |
| dsv4p_nv | empty_200 | 9 | — |
| glm5_2_nv | 504_nv_gateway_timeout | 20 | — |
| glm5_2_nv | empty_200 | 4 | — |
| glm5_2_nv | NVCFPexecTimeout | 3 | 51,637 |

NVCFPexecTimeout 均匀分布在5个key上 (dsv4p_nv: 3/2/7/3/2), 是function级超时而非key级。

### 2.6 ATE 结构

| tiers_tried_count | cnt | avg_dur_ms |
|---|---|---|
| 1 (single-tier) | 0 | — |
| 2 (double-tier) | 24 | 171,969 |

start_tier 均衡: start_tier_idx=1 (dsv4p) 12 ATE avg 175s, start_tier_idx=3 (glm5_2) 12 ATE avg 169s。