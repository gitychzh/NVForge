# HM2 Optimize HM1 — Round R977

**Date**: 2026-07-09 16:05 UTC  
**Trigger**: False trigger (cron mis-dispatch, R976 self-commit)  
**Author**: opc2_uname (HM2)

---

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`

- 最新 commit author = `opc2_uname` (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (stale-symlink pattern: symlink points to R975, R976 already committed)
- R976 was HM2's optimization round (UPSTREAM_TIMEOUT 62→64); no new HM1 commits since

---

## 2. HM1 当前配置 (nv_gw env)

| 参数 | 值 | 状态 |
|------|-----|------|
| TIER_TIMEOUT_BUDGET_S | 112 | floor-ish (112>>64 safe) |
| UPSTREAM_TIMEOUT | 64 | **R976 change**: 62→64 (+2s, 1,394ms buffer over max 62,606ms) |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 3 | optimal |
| KEY_COOLDOWN_S | 25 | floor |
| TIER_COOLDOWN_S | 25 | floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 | aligned with UPSTREAM=64 |
| NVU_FORCE_STREAM_UPGRADE | 0 | disabled |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | defensive |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv,dsv4p_nv | peer-fb skip active |

---

## 3. 6h 数据 (nv_gw)

```
total | ok | fail | sr_pct
    32 | 30 |    2 |   93.8

Upstream: nvcf_pexec 30/30 100%, 2 ATE (NULL upstream, dual-tier exhaustion)

Fallback: f=13, t=19 (19 fallbacks, 100% SR via dsv4p_nv→dsv4p_ms)
```

### Tier Attempts (6h)

| tier | error_type | cnt | avg_ms | max_ms |
|------|-----------|-----|--------|--------|
| glm5_2_nv | NVCFPexecTimeout | 18 | 57,593 | **62,606** |
| glm5_2_nv | 504_nv_gateway_timeout | 5 | — | — |
| glm5_2_nv | empty_200 | 3 | — | — |
| glm5_2_nv | budget_exhausted_after_connect | 1 | 51,838 | 51,838 |

### 24h Error Overview

| error_type | cnt |
|-----------|-----|
| all_tiers_exhausted | 3 |

---

## 4. 分析

**R976 effect still settling**: R976 changed UPSTREAM_TIMEOUT 62→64. The 2 ATE in 6h window may have occurred before the change propagated to HM1. NVCFPexecTimeout max=62,606ms is now within UPSTREAM=64 (1,394ms buffer). 24h only shows 3 ATE total — one pre-R976, two in current window.

**All params at floor/optimal**: 
- TIER_COOLDOWN_S=25 (floor)
- KEY_COOLDOWN_S=25 (floor)
- FASTBREAK=1 (floor)
- EMPTY_200=3 (floor, HM2 parity)
- FORCE_STREAM=64 aligned with UPSTREAM=64
- MIN_OUTBOUND=0 (floor)
- BUDGET=112 >> 64 safe

**Fallback chain working**: 19 fallbacks all 100% SR. dsv4p_nv rescues when glm5_2_nv NVCFPexecTimeout hits. Only 2 dual-tier exhaustions when NVCF is saturated across both tiers.

**ms_gw**: EMPTY_200_FASTBREAK_THRESHOLD=3 (floor), KEY_COOLDOWN_S=60, MIN_OUTBOUND=1.0, UPSTREAM=300. All at floor/optimal — no secondary optimization space (R900 already dropped EMPTY_200_FASTBREAK 5→3).

---

## 5. 决策: NOP

- R976 UPSTREAM 62→64 needs observation period
- All other params at floor/optimal
- No degradation from previous rounds
- False trigger — HM1 has not submitted new changes

**No parameter changes this round.**

---

## 6. 铁律检查

- ✅ 改前必有数据: 6h DB + env collected
- ✅ 单参数原则: no changes this round
- ✅ 只改HM1不改HM2: no changes to either
- ✅ 所有修改写入仓库: this file committed below

---

## ⏳ 轮到HM1优化HM2
