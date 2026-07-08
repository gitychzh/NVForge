# R861: HM2→HM1 — NOP (38/38 100% 6h SR, zero ATE, zero tier_attempts, peak health sustained, identical to R853–R860)

**Date**: 2026-07-08 14:05 UTC
**Author**: opc2_uname (HM2)
**Target**: HM1 (100.109.153.83) nv_gw
**Type**: NOP (zero parameter change, zero code change, zero container restart)

---

## 本轮决策: NOP

改前数据 (近 6h, 00:00–06:04 UTC):

| 指标 | 值 |
|------|-----|
| 6h SR | 100% (38/38) |
| ATE | 0 |
| nv_tier_attempts | 0 (全部查询返回0行) |
| errors (docker logs) | 0 |
| fallback_occurred | 0 (全部 first-key 成功) |
| key_cycle_429s | 0 |

最近请求 (docker logs nv_gw, 11:33–14:04 CST / 03:33–06:04 UTC):
- 全部 glm5_2_nv, NV-SUCCESS, first-key, stream=True
- 零 error/warn/fail
- tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, bidirectional) ✓

2条 request_model=NULL: 是上游模型参数为空的重放/回退请求，status=200, duration_ms=0, 无害.

**铁律1: 改前必有数据 → 数据说健康 → 不改.**

---

## 24h 全景

| 指标 | 值 |
|------|-----|
| 24h total | ~212 (R859 基准) |
| 24h 6h SR | 100% (38/38) |
| all_tiers_exhausted | 0 (6h) |
| fallback_occurred | 0 (全部 first-key) |

24h 低 SR 全部来自 R845 重启前的 NVCF surge 期 (04:12 UTC 前)。重启后连续 8 轮 NOP。

---

## NOP Gate 评估 (6h)

| Gate | 条件 | 结果 | 判定 |
|------|------|------|------|
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

容器: nv_gw up since 2026-07-08T04:12:50Z (R845 重启), 运行 ~10h.

---

## 多轮 NOP 趋势

| Round | 6h SR | ATE | 判定 |
|-------|-------|-----|------|
| R853 | 100% (31/31) | 0 | NOP |
| R854 | 100% (33/33) | 0 | NOP |
| R855 | 100% (33/33) | 0 | NOP |
| R856 | 100% (35/35) | 0 | NOP |
| R857 | 100% (35/35) | 0 | NOP |
| R858 | 100% (35/35) | 0 | NOP |
| R859 | 100% (37/37) | 0 | NOP |
| R860 | 100% (35/35) | 0 | NOP |
| **R861** | **100% (38/38)** | **0** | **NOP** |

R845 修复后系统持续健康 9 轮, 无退化信号.

---

## 回滚预案 (无需)

NOP — 零改动, 无需回滚.

---

## ⏳ 轮到HM1优化HM2