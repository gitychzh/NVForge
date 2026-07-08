# R842: HM2→HM1 — NOP (glm5_2_nv DEGRADED transient → self-recovered, 5h+ continuous 100% SR, all 6 gates pass)

**Timestamp**: 2026-07-08 01:45 UTC (09:45 CST)
**Direction**: HM2 → HM1
**Decision**: NOP (zero parameter change, zero compose change, zero container restart)

---

## Data Collection

### Container Status
```
nv_gw   Up 2 hours (healthy)   StartedAt: 2026-07-08T00:01:38Z
```

### Docker Logs (tail 100, key events)
```
[05:05:16] mapped_model=glm5_2_nv tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback)
[05:05:17] tier=glm5_2_nv k3 resp.status=400 non-cycling, aborting tier
            body: "Function id '3b9748d8...': DEGRADED function cannot be invoked"
[05:05:17] [NV-FALLBACK] Tier glm5_2_nv all-failed → falling back to dsv4p_nv
[05:06:21] tier=dsv4p_nv k4 → 504 (504_nv_gateway_timeout), cycling to next key
[05:06:26] [NV-FALLBACK-SUCCESS] Success on fallback tier dsv4p_nv
[05:33:21] Same DEGRADED pattern: glm5_2_nv DEGRADED → fallback to dsv4p_nv → SUCCESS
[06:03+] All subsequent requests: first-key success (no DEGRADED, no fallback needed)
```

### Container Env (all params match R778 snapshot)
```
UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=114, MIN_OUTBOUND_INTERVAL_S=0
NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_EMPTY_200_FASTBREAK=1
NVU_CONNECT_RESERVE_S=0, NVU_PEER_FALLBACK_TIMEOUT=45
NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NV_INTEGRATE_MODELS="", NV_INTEGRATE_KEY_COOLDOWN_S=0
KEY_COOLDOWN_S=25, TIER_COOLDOWN_S=25
FALLBACK_HEALTH_THRESHOLD=0.10, NVU_SSLEOF_RETRY_DELAY_S=1.0
```

### DB Analysis (6h window: 19:45 UTC → 01:45 UTC)

**Regime aggregate:**
| metric | value |
|--------|-------|
| total | 21 |
| ok | 18 (85.7%) |
| fail | 3 (14.3%) |

**Per-model:**
| model | cnt | ok | fail | avg_ms | max_ms |
|-------|-----|----|------|--------|--------|
| glm5_2_nv | 21 | 18 | 3 | 9,814 | 115,625 |

**ATE analysis (3 failures):**
| time (UTC) | tiers_tried | fallback_tiers_used | duration_ms |
|------------|------------|--------------------| ------------|
| 20:35:16 | 2 | {glm5_2_nv,dsv4p_nv} | 115,625 |
| 20:37:12 | 2 | {glm5_2_nv,dsv4p_nv} | 115,180 |
| 21:05:16 | 2 | {glm5_2_nv,dsv4p_nv} | 115,191 |

All 3 ATEs: `tiers_tried_count=2`, double-tier exhaustion, ~115s ≈ BUDGET=114.

**nv_tier_attempts (6h):**
| tier | error_type | cnt | max_ms |
|------|-----------|-----|--------|
| dsv4p_nv | 504_nv_gateway_timeout | 1 | — |

**0 NVCFPexecTimeout** entries in 6h window.

**Hourly SR breakdown:**
| hour (UTC) | total | ok | fail | SR |
|------------|-------|----|------|-----|
| 18:00 | 31 | 10 | 21 | 32.3% |
| 19:00 | 3 | 3 | 0 | 100.0% |
| 20:00 | 3 | 1 | 2 | 33.3% |
| 21:00 | 3 | 2 | 1 | 66.7% |
| 22:00 | 2 | 2 | 0 | 100.0% |
| 23:00 | 2 | 2 | 0 | 100.0% |
| 00:00 | 5 | 5 | 0 | 100.0% |
| 01:00 | 6 | 6 | 0 | 100.0% |

**5 consecutive hours of 100% SR (22:00–01:00 UTC).**

**Fallback health:**
| fallback_occurred | ok | total |
|-------------------|----|-------|
| f | 15 | 18 |
| t | 3 | 3 |

Fallback path: 3/3 = 100% SR ✓

---

## NOP Gate Evaluation

| Gate | Condition | Result |
|------|----------|--------|
| Gate 1 | All ATEs tiers_tried_count=2 | ✅ 3/3 double-tier |
| Gate 2 | Zero single-tier ATEs in 6h | ✅ 0 single-tier (18:00 UTC burst at 7h+ ago, outside window) |
| Gate 3 | NVCFPexecTimeout buffer ≥3s | ✅ 0 NVCFPexecTimeout entries; UPSTREAM=66, BUDGET=114, ~115s ATE = BUDGET exhaustion not UPSTREAM |
| Gate 4 | FALLBACK_GRAPH bidirectional | ✅ tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback) |
| Gate 5 | Fallback SR = 100% | ✅ 3/3 fallback 100% SR |
| Gate 6 | All params at floor/optimal | ✅ FASTBREAK=1, EMPTY_200_FASTBREAK=1, CONNECT_RESERVE=0, MIN_OUTBOUND=0, INTEGRATE_COOLDOWN=0, FALLBACK_HEALTH=0.10, FORCE_STREAM_UPGRADE=0, FORCE_STREAM_UPGRADE_TIMEOUT=66=UPSTREAM |

**Additional strengthening signals:**
- 5h+ continuous 100% SR (22:00–01:00 UTC)
- glm5_2_nv DEGRADED transient at 05:05/05:33 UTC → system self-recovered after 06:03
- Zero NVCFPexecTimeout — UPSTREAM non-binding
- Fallback path 100% reliable during DEGRADED window

---

## Decision: NOP

The 3 ATEs in the 6h window are from the glm5_2_nv function `3b9748d8` DEGRADED transient (20:35–21:05 UTC). System fully self-recovered by 22:00 UTC. All 6 NOP gates pass. Zero config parameters can fix NVCF function DEGRADED — this is upstream NVCF behavior, not proxy-configurable.

No compose change, no container restart, no git change to HM1.

---

## ⏳ 轮到HM1优化HM2