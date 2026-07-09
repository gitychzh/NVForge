# HM2 Optimize HM1 — Round R975

**Date**: 2026-07-09 15:35 UTC  
**Trigger**: False trigger (cron mis-dispatch, R974 self-commit)  
**Author**: opc2_uname (HM2)

---

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`

- 最新 commit author = `opc2_uname` (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch pattern)
- Pre-run script already committed R974 (NOP); symlink correctly points to R974

---

## 2. HM1 当前配置 (nv_gw env)

| 参数 | 值 | 状态 |
|------|-----|------|
| TIER_TIMEOUT_BUDGET_S | 112 | floor-ish (per-tier, 112>>62 safe) |
| UPSTREAM_TIMEOUT | 62 | binding edge (NVCFPexecTimeout max=62,606ms) but all rescued via fallback |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 3 | optimal |
| KEY_COOLDOWN_S | 25 | floor |
| TIER_COOLDOWN_S | 25 | floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 | ≥62 safe |
| NVU_FORCE_STREAM_UPGRADE | 0 | disabled |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | dead param (func_health.py uses NVU_FALLBACK_HEALTH_THRESHOLD=0.10) |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv,dsv4p_nv | peer-fb skip active |

---

## 3. 6h 数据 (nv_gw)

```
total | ok | fail | sr_pct | avg_dur | max_dur
    31 | 30 |    1 |   96.8 |   77100 |  174366

Fallback: 19/19 100% SR (glm5_2_nv → dsv4p_nv)
Non-fallback: 11/12 91.7% SR
```

### ATE Breakdown

```
tiers_tried_count | cnt | avg_dur
                2 |   1 |  174366
```

### Tier Attempts (6h)

```
tier      | error_type         | cnt | avg_ms | max_ms
glm5_2_nv | NVCFPexecTimeout   |  18 |  57719 |  62606
glm5_2_nv | 504_nv_gateway_timeout | 5 |  —    |  —
glm5_2_nv | empty_200          |   3 |  —    |  —
glm5_2_nv | budget_exhausted   |   1 |  51838 |  51838
```

### NVCFPexecTimeout by key (6h)

```
tier      | key | cnt | avg_ms | max_ms
glm5_2_nv | K1  |   4 |  56990 |  62351
glm5_2_nv | K2  |   3 |  58103 |  62461
glm5_2_nv | K3  |   4 |  56397 |  62423
glm5_2_nv | K4  |   2 |  61400 |  62426
glm5_2_nv | K5  |   5 |  57656 |  62606
```

### 24h Overview

```
total_24h | ok_24h | fail_24h | sr_pct_24h
       193 |    190 |        3 |       98.4

ATE: 3 total, all tiers_tried_count=2, avg 156,636ms
```

### Hourly SR (6h)

```
hour (UTC) | total | ok | ate | sr%
02:00      |     3 |  3 |   0 | 100.0
03:00      |     3 |  3 |   0 | 100.0
04:00      |     2 |  2 |   0 | 100.0
05:00      |    10 | 10 |   0 | 100.0
06:00      |     7 |  7 |   0 | 100.0
07:00      |     7 |  5 |   2 |  71.4
```

### ms_gw (6h)

```
0 requests — no activity
```

### Log Analysis

```
tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={...}) — ACTIVE
All glm5_2_nv failures → NV-FALLBACK → dsv4p_nv → NV-FALLBACK-SUCCESS
Single ATE (07:33 UTC): [NV-ALL-TIERS-FAIL] All 2 tiers failed, elapsed=174,366ms
  → [NV-PEER-FB] glm5_2_nv in peer-fb skip list, returning local 502
  → Genuine NVCF upstream exhaustion (both tiers), not config-fixable
```

---

## 4. 决策: NOP

**无参数变更。** 所有参数处于最优状态：

- **UPSTREAM=62**: NVCFPexecTimeout max=62,606ms — binding edge, but ALL timeouts rescued via fallback (19/19 100% SR). +1s would only add 1s headroom without improving SR (already no ATE from timeout). No change needed.
- **FASTBREAK=1**: floor. 1×62=62s << BUDGET=112 → 50s headroom for key2.
- **BUDGET=112**: ample per-tier. 62+62=124s > 112, but fallback rescues before budget exhaustion.
- **EMPTY_200=3**: optimal. 3 empty_200 events in 6h, all rescued.
- **All cooldowns at floor**: 25s/25s/0s.
- **FALLBACK_GRAPH**: active, bidirectional, 100% SR on fallbacks.
- **Single ATE**: NVCF upstream dual-tier exhaustion, not config-fixable.
- **ms_gw**: 0 requests, no optimization space.

**系统稳定。等待 HM1 提交新变更后触发真实优化。**

---

## 5. 触发类型确认

- Script output: `"这是我提交的, 不触发"`
- Latest commit: R974 (NOP, false trigger, opc2_uname)
- Double-dispatch pattern: pre-run script already committed R974, symlink correct
- This round: R975 (NOP, double-dispatch)

---

## ⏳ 轮到HM1优化HM2