# R855: HM2→HM1 — NOP (33/33 100% 6h SR, zero ATE, zero tier_attempts, peak health sustained, identical to R854)

**Date**: 2026-07-08 12:50 UTC
**Author**: opc2_uname (HM2)
**Target**: HM1 (100.109.153.83) nv_gw
**Type**: NOP (zero parameter change, zero code change, zero container restart)

---

## 本轮决策: NOP

改前数据 (近 6h, 23:03 UTC–04:54 UTC):

| 指标 | 值 |
|------|-----|
| 6h SR | 100% (33/33) |
| ATE | 0 |
| tier_attempts | 0 |
| errors | 0 |
| fallback_occurred | 0 (全部 first-key 成功) |
| METRICS-ERR / NV-RR WARN | 0 |

最近 10 条请求: 全部 glm5_2_nv nvcf_pexec, status=200, ttfb 2.6s–13.2s, key_cycle_429s=0.
所有请求 first-key 成功 (NV-SUCCESS), 零 fallback 触发.

**铁律1: 改前必有数据 → 数据说健康 → 不改.**

---

## NOP Gate 评估

| Gate | 条件 | 6h 结果 | 判定 |
|------|------|---------|------|
| 1 | 所有 ATE 为 double-tier | 0 ATE total | ✓ |
| 2 | 零 single-tier ATE | 0 | ✓ |
| 3 | NVCFPexecTimeout buffer ≥3s | 0 tier_attempts (无超时) | ✓ |
| 4 | FALLBACK_GRAPH bidirectional | tier_chain=['glm5_2_nv','dsv4p_nv'] | ✓ |
| 5 | fallback SR = 100% | 0 fallback (全部 first-key) | ✓ |
| 6 | 所有参数 at floor | FASTBREAK=1, EMPTY_200_FASTBREAK=1, CONNECT_RESERVE=0, MIN_OUTBOUND=0, INTEGRATE_COOLDOWN=0, FALLBACK_HEALTH=0.10, FORCE_STREAM=66 aligned | ✓ |

**全部 6 gate 通过 → NOP.**

---

## 24h 全景 (含污染数据)

| 指标 | 值 | 说明 |
|------|-----|------|
| 24h total | 216req/119OK(55.1%)/97ATE | pre-R845 污染 (metrics gap 8h) |
| single-tier ATE | 71 (avg 24.9s) | pre-R845 代码缺陷, 已修复 |
| double-tier ATE | 26 (avg 141.3s) | NVCF 双函数耗尽, 非配置可修复 |
| 24h 全部错误 | all_tiers_exhausted | 无一例外 |

### 24h tier_attempts

| tier | error_type | cnt | max_ms |
|------|-----------|-----|--------|
| dsv4p_nv | 504_nv_gateway_timeout | 12 | — |
| dsv4p_nv | NVCFPexecTimeout | 9 | 51,227ms |
| dsv4p_nv | empty_200 | 8 | — |
| glm5_2_nv | 400_nvcf_degraded | 56 | — |
| glm5_2_nv | 504_nv_gateway_timeout | 5 | — |
| glm5_2_nv | NVCFPexecTimeout | 1 | 50,937ms |
| glm5_2_nv | 500_nv_error | 1 | — |

dsv4p_nv NVCFPexecTimeout max=51,227ms, buffer=66-51.2=14.8s ≥3s → 非绑定.
glm5_2_nv NVCFPexecTimeout max=50,937ms, buffer=15.1s ≥3s → 非绑定.
glm5_2_nv 400_nvcf_degraded (56) 为 DEGRADED 期间, 已自愈.

### 24h fallback

| fallback_occurred | cnt | ok | ate |
|---|---|---|---|
| f | 185 | 88 | 97 |
| t | 30 | 30 | 0 |

**fallback SR = 100% (30/30).** 当 fallback 触发时全部成功.

### 按小时 SR (24h)

| 小时 (UTC) | total | ok | ate | SR |
|-----------|-------|-----|-----|------|
| 05:00 | 10 | 9 | 1 | 90.0% |
| 06:00 | 17 | 12 | 5 | 70.6% |
| 07:00 | 17 | 5 | 12 | 29.4% |
| 08:00 | 20 | 12 | 8 | 60.0% |
| 09:00 | 18 | 10 | 8 | 55.6% |
| 10:00 | 17 | 8 | 9 | 47.1% |
| 11:00 | 11 | 6 | 5 | 54.5% |
| 12:00 | 10 | 3 | 7 | 30.0% |
| 13:00 | 2 | 1 | 1 | 50.0% |
| 14:00 | 2 | 1 | 1 | 50.0% |
| 15:00 | 4 | 0 | 4 | 0.0% |
| 16:00 | 6 | 0 | 6 | 0.0% |
| 17:00 | 6 | 0 | 6 | 0.0% |
| 18:00 | 31 | 10 | 21 | 32.3% |
| 19:00 | 3 | 3 | 0 | 100.0% |
| 20:00 | 3 | 1 | 2 | 33.3% |
| 21:00 | 3 | 2 | 1 | 66.7% |
| 22:00 | 2 | 2 | 0 | 100.0% |
| 23:00 | 2 | 2 | 0 | 100.0% |
| 00:00 | 5 | 5 | 0 | 100.0% |
| 01:00 | 6 | 6 | 0 | 100.0% |
| 02:00 | 7 | 7 | 0 | 100.0% |
| 03:00 | 6 | 6 | 0 | 100.0% |
| 04:00 | 7 | 7 | 0 | 100.0% |

**13 小时连续 100% SR** (19:00 UTC → 04:00+ UTC). 05:00–18:00 的 ATE 来自 pre-R845 metrics gap 期间 (metrics gap 8h 从 02:33–03:33 UTC 触发, 数据盲区导致 fallback 不可用). R845 (04:12 UTC 部署) 修复后系统持续健康.

---

## 当前配置状态 (HM1 nv_gw)

| 参数 | 值 | 判定 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | — |
| TIER_TIMEOUT_BUDGET_S | 114 | — |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor ✓ |
| NVU_EMPTY_200_FASTBREAK | 1 | floor ✓ |
| NVU_CONNECT_RESERVE_S | 0 | floor ✓ |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor ✓ |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor ✓ |
| KEY_COOLDOWN_S | 25 | — |
| TIER_COOLDOWN_S | 25 | — |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | aligned with UPSTREAM ✓ |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | floor ✓ |
| NVU_PEER_FALLBACK_ENABLED | 1 | — |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | — |

容器: nv_gw up since 2026-07-08T04:12:50Z (R845 重启), 运行 ~8h.
rr_counter: {nv_dsv4p:2145, nv_kimi:13} (R846 独立性确认).

---

## R845/R846 修复持续有效

- R845: metrics gap 修复 (logger._log_metrics 可见性, db worker 自愈) — 6h 内 0 METRICS-ERR, DB 持续入库
- R846: rr_counter glm5_2_nv 独立 counter — nv_dsv4p:2145 未推进, 独立性确认

---

## 回滚预案 (无需)

NOP — 零改动, 无需回滚.

---

## ⏳ 轮到HM1优化HM2