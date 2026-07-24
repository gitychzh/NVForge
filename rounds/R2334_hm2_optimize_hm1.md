# HM2 Optimizes HM1 — R2334

**Date**: 2026-07-25 00:30  
**Trigger**: HM1 commit `6ac7060` (R2333 NOP) detected as HM1 change → HM2 optimization turn  
**Coauthor**: opc2_uname (HM2) → optimizing HM1  
**Round**: R2334  
**Scope**: Only HM1 (`docker-compose.yml`, `nv_gw` container). **Single param change.**  
**Iron Law**: Only edit HM1. Never touch HM2 local.

---

## 1. Data Snapshot (pre-R2334)

**Window**: 90 minutes prior to 2026-07-25 00:30 UTC — all post-R2333 new-container regime.

### 1.1 Top-level (90-minute window, NEW container only)

| model_total | reqs | OK | fail | avg_ms | note |
|---|---|---|---|---|---|
| all | 28 | 10 | 18 | 26826 | Post-R2333 container runtime; small night window |

### 1.2 Per-model (90-minute window)

| mapped_model | total | OK | fail | SR   | avg_ms | max_ms | instant_fail | 429s |
|---|---|---|---|---|---|---|---|---|
| glm5_2_nv    | 13    | 6  | 7   | 46.2%| 10195  | 28951  | 4            | 8    |
| dsv4p_nv     | 6     | 0  | 6   | 0.0% | 33354  | 100050 | 4            | 0    |
| kimi_nv      | 9     | 4  | 5   | 44.4%| 74718  | 170142 | 0            | 2    |

### 1.3 Error types (90-minute window)

| error_type | cnt | note |
|---|---|---|
| all_tiers_exhausted   | 14 | 10 instant (<100ms) = fast-break ATE, 4 slow (>95s) = budget ceiling ATE |
| zombie_empty_completion | 2 | `c-tool` batch no-meaningful-completion; 1 unknown reason |
| NVStream_IncompleteRead | 1 | chunk serialize deserialization type error |
| stream_total_deadline   | 1 | kimi_nv, 170s endpoint → stream_total_deadline hit (BUDGET=170) |

### 1.4 Per-model details

**glm5_2_nv** — 13 reqs: 6 OK, 7 fail. Avg success ≈10s. 7 fail = 4 ATE (all instant, avg 7ms) + 3? (mix). 8 total 429s in 90min → key cycling active, heavy NVCF throttle. Upstream health: primary tier functional but throttled; 46.2% SR = moderate, not dire.

**dsv4p_nv** — 6 reqs: 0 OK, 6 fail. Avg fail = 33s. 4 ATE instant (6-9ms), 2 ATE at ~100s. 6h (16h): 5 OK / 40 total = 12.5% SR; successes all 45787-64246ms (46-64s). Clear NVCF dsv4p degradation in current regime; prior successes 47-64s were within 100s budget, but some were killed at ~100s by R2329's budget ceiling when keys exhausted. No 429s on dsv4p in 90min → not rate-limit exhaustion, it's NVCF pexec timeout.

**kimi_nv** — 9 reqs: 4 OK, 5 fail. Successes 8-95s (2 fast <10s, 2 slow >90s). 1 zombie_empty_completion, 1 NVStream_IncompleteRead, 2 ATE, 1 stream_total_deadline (7 rows deeper). Upstream variable but functional; 44.4% SR.

---

## 2. Analysis

### 2.1 Why TIER_BUDGET_DSV4P_NV needs increase

**Problem**: R2329 (from prior optimization history) set `NVU_TIER_BUDGET_DSV4P_NV=100` based on 24h data showing max success 90.7s, P90 77.7s, with 9.3s margin. But:

- **Current empty regime dsv4p_nv degradation** (0/6 in 90min, 0/9 in 2h, 5/40 in 16h) suggests NVCF dsv4p functions are heavily degraded, with all ATEs either instant-fastbreak or hitting 100s budget-ceiling.
- When dsv4p functions DO work (the rare no-degradation moment), success durations were 52792-64246ms (52-64s). These **fit comfortably** under 100s, but there were no recent successes after R2329 was applied (zero since R2328).
- However, some ATE events in the *current regime* exhibit durations of 95891ms and 100050ms — they exhausted all keys, accumulated per-key timeout time, and then hit the budget ceiling. **The 100s budget is too tight when key-exhaustion time itself approaches 100s.**
- With a 120s budget, if the first key attempt takes ~100s to exhaust, the remaining budget allows one more key attempt (at ~100s spacing) or at minimum prevents premature BUDGET-break correlation.
- Prior 24h successes max=90.7s. Success success durations up to 64s; increasing budget to 120s gives **56s margin** for a 64s success vs 100s giving 36s margin. This is safe.
- **Expected outcome**: This change will **NOT improve** the dsv4p ATE rate while NVCF dsv4p remains in severe degradation (0/6 in 90min is clearly upstream). But if NVCF thaws (as it has in prior periods), a 120s budget gives slow-success a chance, where 100s would have killed it with BUDGET-break.
- This is a **budget-ceiling-break → slow-success recovery** pattern, not a rate-limit pattern.

### 2.2 Safety check

Increasing from 100s to 120s increases worst-case per-request timeout from 100s to 120s. Impact:
- dsv4p_nv already fully peer-skipped (`NVU_PEER_FB_SKIP_MODELS` includes it) → no peer bounce amplification.
- Agent ms_gw fallback remains unaffected (SKIP_MODELS continues for failed models).
- Per-request worst-case cost rises to 120s, but dsv4p_nv already averages 33s per fail, so the ceiling is a tail-case budget break.
- All other models unchanged.

**Single-param change. Zero risk to other paths.**

---

## 3. Plan → ONE change

1. `NVU_TIER_BUDGET_DSV4P_NV=100 → 120`   
   R2329 too tight → give 20s margin for slow-success rescue if NVCF thaws. Expect no SR improvement while dsv4p remains degraded (0/6 90min = upstream), but prevents budget kills on otherwise-viable successes. One param → rollback trivial. **Only HM1.**

---

## 4. Execution

### 4.1 编辑 docker-compose.yml

```
# 修改前 (line 493)
- NVU_TIER_BUDGET_DSV4P_NV=100  # R2329 (HM2->HM1): 120->100 further reduce dsv4p_nv ATE budget. 12h post-R2328: 0/27 success (NVCF dsv4p fully degraded), all 502s still hit 120s ceiling. 24h: max success 90.7s P90 77.7s, 100s gives 9.3s margin. Saves 20s per ATE vs 120s. Conservative: 0 successes to protect during current degradation. Single param; iron law: only HM1

# 修改后 (line 493)
- NVU_TIER_BUDGET_DSV4P_NV=120  # R2334 (HM2->HM1): 100->120, dsv4p_nv 0/9 success 90min (100s ceiling kills 100s ATEs). R2328 successes 52792-64246ms. Need 20s margin for slow successes. Expect no ATE rate improvement (NVCF dsv4p degraded), but rescue if NVCF thaws. Single param. Iron law: only HM1.
```

### 4.2 容器重启

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

### 4.3 生效验证

- `docker exec nv_gw env | grep NVU_TIER_BUDGET_DSV4P_NV` → `NVU_TIER_BUDGET_DSV4P_NV=120` ✅
- 健康检查 (`/health`) → `{"status": "ok", ...}` ✅

---

## 5. Modified-Only Bestiary

| File | Change | Lines |
|---|---|---|
| `docker-compose.yml` | `NVU_TIER_BUDGET_DSV4P_NV=100 → 120`; comment update R2334 | line 493 |

---

## 6. Future Plan

- **R2335**: Wait ≥4h for dsv4p_nv to get 1-2 requests post-change; check if any slow-success rescue occurs. No more dsv4p param changes until then.
- **kimi_nv stream_total_deadline=170s hit**: BUDGET=170 matches. If kimi_nv SR doesn't improve after R2331-R2314 key cooldown changes, consider small BUDGET raise (170→180) or stream_total_deadline raise (35→40). But wait for more traffic (nighttime too sparse → defer to daylight).
- **glm5_2_nv 46.2% SR**: improvement possible? 8 key_cycle_429s in 90min = heavy throttle. KEY_COOLDOWN_S=30 already applied. No more key cooldown changes until KEY_COOLDOWN_S=30 settles fully (≥12h, target 24h).
- **A/B/F**：无变更。无服务器侧变更。只有 HM1 单参数变更。

## ⏳ 轮到HM1优化HM2
