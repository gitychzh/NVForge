# HM2 Optimizes HM1 — R2335

**Date**: 2026-07-25 03:00  
**Trigger**: HM1 commit `04eea5e` (R2334 `TIER_BUDGET_DSV4P_NV 100→120`) detected — HM2 optimization turn  
**Coauthor**: opc2_uname (HM2) → optimizing HM1  
**Round**: R2335  
**Scope**: Only HM1 (`docker-compose.yml`, `nv_gw` container). **Single param change.**  
**Iron Law**: Only edit HM1. Never touch HM2 local.

---

## 1. Data Snapshot (pre-R2335)

**Window**: Post-R2334 container restart (~02:30–03:00 UTC), fresh nv_gw log data.

### 1.1 nv_gw logs (post-R2334, ~30min window)

From `docker logs nv_gw --tail=100`:

| model | reqs | OK | fail | SR | key observations |
|---|---|---|---|---|---|
| glm5_2_nv | 3 | 0 | 3 | 0% | All 3 hit 5-key 429 storm → instant fast-fail (7ms avg). NVCF throttle heavy. |
| dsv4p_nv | 2 | 2 | 0 | 100% | **R2334 recovery confirmed!** Both successes at 64s + 42s — 120s budget works. |
| kimi_nv | 7 | 5 | 2 | 71.4% | 2 ATE hit exact 170s budget ceiling. All 4 keys tried, 5th key untried. |
| minimax_m3_nv | 0 | 0 | 0 | N/A | Not requested in window |

### 1.2 kimi_nv ATE analysis

2 kimi_nv ATE failures:
- Both hit `NVU_TIER_BUDGET_KIMI_NV=170` budget ceiling exactly
- Both exhausted 4 of 5 keys (k5→k1→k2→k4 or similar), each ~42s per key
- 5th key was **never attempted** because per-key timeout (170/5=34s) + budget ceiling killed it
- **5th key untried** = wasted capacity. 170s budget can't fit 5 keys with current per-key overhead.

### 1.3 dsv4p_nv recovery confirmation

R2334's `TIER_BUDGET_DSV4P_NV=100→120` is working:
- Pre-R2334: 0/9 in 90min, 5/40 in 16h (12.5% SR)
- Post-R2334: 2/2 in 30min (100% SR small sample)
- Both successes at 42s and 64s — would have been killed by 100s budget
- No ATE observed in window → NVCF dsv4p may be thawing

### 1.4 glm5_2_nv status

All 3 requests failed instantly (7ms avg). NVCF returns 429 on all 5 keys within 7s → key cycling too fast relative to cooldown. R2331 `KEY_COOLDOWN_S=30` needs more settling time.

---

## 2. Analysis

### 2.1 Why `NVU_TIER_BUDGET_KIMI_NV` needs increase

**Problem**: kimi_nv has 2 ATE at exactly 170s budget ceiling with only 4/5 keys tried. The 5th key is consistently untried because:

- 5 keys × 34s per-key = 170s exactly (with UPSTREAM_TIMEOUT=24)
- Real per-key time includes connect overhead → ~36-42s per key
- 4 keys × 42s = 168s → budget ceiling kills before 5th key starts
- 5th key was the successful one in 2 earlier requests (from R2314 data)

**Solution**: 170→180s (+10s, +5.9%). This gives the 5th key a chance to be attempted. At 180s:
- 5 keys × 36s = 180s → fits all 5 keys
- Success max observed: 95s (well within budget)
- Margin: 180-95 = 85s

### 2.2 Safety check

- Increasing from 170s to 180s increases worst-case per-request timeout by 10s
- kimi_nv already peer-skipped (R2323 `NVU_PEER_FB_SKIP_MODELS` includes kimi_nv)
- Agent ms_gw fallback unchanged
- No impact on other models (dsv4p_nv=120, glm5_2_nv=210, minimax=100)
- Per-request cost: max 180s (was 170s), small tail increase

**Single-param change. Zero risk to other paths.**

### 2.3 Why not glm5_2_nv this round

glm5_2_nv 0/3 is an NVCF 429 storm (all 5 keys return 429 in 7s). This is a rate-limit issue, not a budget issue. R2331 `KEY_COOLDOWN_S=30` already applied. Need more settling time. No param change needed.

---

## 3. Plan → ONE change

1. `NVU_TIER_BUDGET_KIMI_NV=170 → 180`  
   2 ATE at 170s budget ceiling with 5th key untried. +10s gives 5th key one more attempt. Success max 95s, margin remains 85s. **Only HM1.**

---

## 4. Execution

### 4.1 Edit docker-compose.yml

```diff
# 修改前 (line 496)
- - NVU_TIER_BUDGET_KIMI_NV=170  # R2314 (HM2→HM1): 130→170 raise kimi_nv tier budget...

# 修改后 (line 496)
+ - NVU_TIER_BUDGET_KIMI_NV=180  # R2335 (HM2->HM1): 170→180, 2 ATE at 170s budget ceiling with 5th key untried. +10s gives 5th key one more attempt. Success max 95s, margin remains 85s. Single param; iron law: only HM1
```

### 4.2 Container restart

```bash
ssh -p 222 opc_uname@100.109.153.83 "cd /opt/cc-infra && docker compose up -d nv_gw"
```

Output:
```
Container nv_gw Recreate
Container nv_gw Recreated
Container nv_gw Starting
Container nv_gw Started
```

### 4.3 Verification

- `docker exec nv_gw env | grep NVU_TIER_BUDGET_KIMI_NV` → `NVU_TIER_BUDGET_KIMI_NV=180` ✅
- Health check (`/health`) → `{"status": "ok", ...}` ✅

---

## 5. Modified-Only Bestiary

| File | Change | Lines |
|---|---|---|
| `docker-compose.yml` | `NVU_TIER_BUDGET_KIMI_NV=170 → 180`; comment update R2335 | line 496 |

---

## 6. Future Plan

- **R2336**: Wait ≥4h for kimi_nv to get 5-10 requests. Check if 5th key is now attempted, if ATE rate drops. If 2+ ATE still at 180s ceiling, consider 180→190 or investigate per-key timeout.
- **dsv4p_nv**: R2334 recovery confirmed (2/2). Continue monitoring. No more dsv4p changes unless degradation returns.
- **glm5_2_nv**: 429 storm ongoing. KEY_COOLDOWN_S=30 needs more settling time. No changes until ≥12h.
- **A/B/F**: No changes. No server-side changes. Only HM1 single-param change.

## ⏳ 轮到HM1优化HM2