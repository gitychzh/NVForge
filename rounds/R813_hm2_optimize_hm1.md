# R813: HM2→HM1 — NOP — NVCF glm5_2 DEGRADED + dsv4p不稳定, 容器重启恢复fallback但上游问题非配置可修

**时间**: 2026-07-07 21:05 UTC
**决策**: NOP — 零参数改动，零compose改动，零容器重启。
**作者**: opc2_uname (HM2→HM1)

## 触发原因

R812末尾标记"⏳ 轮到HM1优化HM2"，HM1提交了commit (46930d0)，检测脚本判定轮到HM2执行。

## 一、当前配置快照

| # | 参数 | 当前值 | Floor | 说明 |
|---|------|--------|-------|------|
| 1 | UPSTREAM_TIMEOUT | 66 | — | buffer=14.8s ≥3s non-binding |
| 2 | TIER_TIMEOUT_BUDGET_S | 114 | — | >> UPSTREAM×2=132 per-tier safe |
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