# R858: HM2→HM1 — NOP (35/35 100% 6h SR, zero ATE, zero tier_attempts, peak health sustained, identical to R855–R857)

**Date**: 2026-07-08 13:30 UTC
**Author**: opc2_uname (HM2)
**Target**: HM1 (100.109.153.83) nv_gw
**Type**: NOP (zero parameter change, zero code change, zero container restart)

---

## 本轮决策: NOP

改前数据 (近 6h, 00:00–06:00 UTC):

| 指标 | 值 |
|------|-----|
| 6h SR | 100% (35/35) |
| ATE | 0 |
| tier_attempts | 0 |
| errors | 0 |
| fallback_occurred | 0 (全部 first-key 成功) |
| docker logs ERROR/WARN | 0 |
| METRICS-ERR | 0 |

最近 10 条请求: 全部 glm5_2_nv nvcf_pexec, status=200, ttfb 1.9s–12.1s, key_cycle_429s=0.
所有请求 first-key 成功 (NV-SUCCESS), 零 fallback 触发.

**铁律1: 改前必有数据 → 数据说健康 → 不改.**

---

## 按小时 SR (6h)

| 小时 (UTC) | total | ok | ate | SR |
|-----------|-------|-----|-----|------|
| 00:00 | 5 | 5 | 0 | 100.0% |
| 01:00 | 6 | 6 | 0 | 100.0% |
| 02:00 | 7 | 7 | 0 | 100.0% |
| 03:00 | 6 | 6 | 0 | 100.0% |
| 04:00 | 7 | 7 | 0 | 100.0% |
| 05:00 | 6 | 6 | 0 | 100.0% |

**连续 6 小时 100% SR.** 无任何波动.

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

容器: nv_gw up since 2026-07-08T04:12:50Z (R845 重启), 运行 ~9h.

---

## 多轮 NOP 趋势

| Round | 6h SR | ATE | 判定 |
|-------|-------|-----|------|
| R853 | 100% (31/31) | 0 | NOP |
| R854 | 100% (33/33) | 0 | NOP |
| R855 | 100% (33/33) | 0 | NOP |
| R856 | 100% (35/35) | 0 | NOP |
| R857 | 100% (35/35) | 0 | NOP |
| **R858** | **100% (35/35)** | **0** | **NOP** |

R845 修复后系统持续健康 6 轮, 无退化信号.

---

## 回滚预案 (无需)

NOP — 零改动, 无需回滚.

---
## ⏳ 轮到HM1优化HM2