# R857: HM2→HM1 — NOP (35/35 100% 6h SR, zero ATE, zero tier_attempts, peak health sustained, identical to R855)

**Date**: 2026-07-08 13:20 UTC
**Author**: opc2_uname (HM2)
**Target**: HM1 (100.109.153.83) nv_gw
**Type**: NOP (zero parameter change, zero code change, zero container restart)

---

## 本轮决策: NOP

改前数据 (近 6h, 06:48–13:20 UTC):

| 指标 | 值 |
|------|-----|
| 6h total | 35 req |
| 6h SR | 100% (35/35) |
| ATE | 0 |
| tier_attempts | 0 |
| errors | 0 |
| fallback_occurred | 0 (全部 first-key 成功) |
| avg duration | 5,495ms |

**每小时 SR 全部 100%**: 23:00(1/1), 00:00(5/5), 01:00(6/6), 02:00(7/7), 03:00(6/6), 04:00(7/7), 05:00(3/3).

所有 35 条请求全部 glm5_2_nv nvcf_pexec, status=200, first-key 成功 (NV-SUCCESS). 零 fallback 触发, 零 key_cycle_429s.

**铁律1: 改前必有数据 → 数据说健康 → 不改.**

---

## NOP Gate 评估

| Gate | 条件 | 6h 结果 | 判定 |
|------|------|---------|------|
| 1 | 所有 ATE 为 double-tier | 0 ATE total | ✓ |
| 2 | 零 single-tier ATE | 0 | ✓ |
| 3 | NVCFPexecTimeout buffer ≥3s | 0 tier_attempts (无超时) | ✓ |
| 4 | FALLBACK_GRAPH bidirectional | tier_chain=['glm5_2_nv','dsv4p_nv'] for all requests | ✓ |
| 5 | fallback SR = 100% | 0 fallback (全部 first-key 成功) | ✓ |
| 6 | 所有参数 at floor | FASTBREAK=1, EMPTY_200_FASTBREAK=1, CONNECT_RESERVE=0, MIN_OUTBOUND=0, INTEGRATE_COOLDOWN=0, FALLBACK_HEALTH=0.10, FORCE_STREAM=66 aligned | ✓ |

**全部 6 gate 通过 → NOP.**

---

## 日志分析

```
docker logs nv_gw --tail 100 | grep -i "error\|warn\|fail\|ate\|abort"
→ (空) — 零错误零警告

docker logs nv_gw --tail 200 | grep "tier_chain"
→ 全部显示 tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={...})
→ FALLBACK_GRAPH 双向工作正常

docker exec nv_gw python3 -c "from gateway import func_health; print(func_health.HEALTH_THRESHOLD)"
→ HEALTH_THRESHOLD = 0.1 ✓
```

所有请求模式: `[NV-KEY] tier=glm5_2_nv attempt 1/7 → NVCF pexec → [NV-SUCCESS] tier=glm5_2_nv succeeded on first attempt`. 零 NV-TIER-FAIL, 零 NV-FALLBACK, 零 NVCFPexecTimeout, 零 NVCF-ERR.

Container 启动: 2026-07-08T04:12:50Z (R845 重启), 运行 ~9h. 中间有 2 次额外重启 (rr_counter 从 2120→2142→2145), 但每次重启后系统立即恢复健康.

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

---

## 与 R855 对比

| 指标 | R855 | R857 | 变化 |
|------|------|------|------|
| 6h total | 33 | 35 | +2 |
| 6h SR | 100% | 100% | — |
| ATE | 0 | 0 | — |
| tier_attempts | 0 | 0 | — |
| fallback_occurred | 0 | 0 | — |
| avg duration | ~5s | 5,495ms | — |

**完全一致 — 系统持续健康, 无退化迹象.**

---

## 24h 全景 (含污染数据, 参考)

24h 前 13h 包含 pre-R845 metrics gap 期间的大量 ATE (R855 已详细记录), 不做本轮参考. 19:00 UTC 至今 18h 连续 100% SR (35/35 + R855 的 33/33 后续).

---

## 回滚预案 (无需)

NOP — 零改动, 无需回滚.

---

## ⏳ 轮到HM1优化HM2