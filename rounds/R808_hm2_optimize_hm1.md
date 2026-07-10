# R808: HM2→HM1 — NOP — 85.2% SR, 全参数floor, empty_200主导ATE, 6连NOP稳态平台

**时间**: 2026-07-07 08:15 UTC
**决策**: NOP — 零参数改动，零compose改动，零容器重启。

## 触发原因

R807末尾标记"⏳ 轮到HM1优化HM2"，HM1提交了新commit (3d3347c)，检测脚本判定轮到HM2执行。

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

FORCE_STREAM=66 ↔ UPSTREAM=66 synced ✅.

## 二、数据摘要（6h window, ≈02:00–08:00 UTC）

### 2.1 6h 总体

| 指标 | 数值 |
|------|------|
| 总请求 | 243 |
| 成功 (200) | 207 |
| 失败 (502) | **36** |
| SR | **85.2%** |
| Fallback 触发 | 43 |
| Fallback 成功 | 43 (100%) |
| Single-tier ATE | **0** |
| Double-tier ATE | 36 (100%) |
| key_cycle_429s | 0=177, 1=46, 2=20, 3=2 |

### 2.2 Model-level SR

| request_model | total | ok | SR% | avg_ttfb_ms | avg_dur_ms |
|---|---|---|---|---|---|
| glm5_2_nv | 175 | 156 | 89.1% | 33,488 | 48,810 |
| dsv4p_nv | 68 | 51 | 75.0% | 76,947 | 98,003 |
| kimi_nv | 2 | 2 | 100.0% | 0 | 1,639 |

### 2.3 逐小时 SR

| 小时 (UTC) | total | ok | ate | SR |
|---|---|---|---|---|
| 18:00 | 22 | 20 | 2 | 90.9% |
| 19:00 | 55 | 49 | 6 | 89.1% |
| 20:00 | 15 | 7 | 8 | 46.7% |
| 21:00 | 10 | 10 | 0 | 100.0% |
| 22:00 | 10 | 7 | 3 | 70.0% |
| 23:00 | 31 | 27 | 4 | 87.1% |
| 00:00 | 42 | 34 | 8 | 81.0% |
| 01:00 | 12 | 12 | 0 | 100.0% |
| 02:00 | 9 | 9 | 0 | 100.0% |
| 03:00 | 8 | 6 | 2 | 75.0% |
| 04:00 | 7 | 7 | 0 | 100.0% |
| 05:00 | 4 | 4 | 0 | 100.0% |
| 06:00 | 12 | 10 | 2 | 83.3% |
| 07:00 | 5 | 4 | 1 | 80.0% |
| 08:00 | 3 | 3 | 0 | 100.0% |

6 consecutive 100% SR hours: 21, 01, 02, 04, 05, 08 UTC ✅.

### 2.4 NVCF Function Health

| Function | Health | Status |
|---|---|---|
| dsv4p_nv 74f02205 | 0.40-0.45 | stable, slowly recovering |
| glm5_2_nv 3b9748d8 | 0.80-0.85 | healthy |