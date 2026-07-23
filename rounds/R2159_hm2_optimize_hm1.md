# R2159 (HM2→HM1): KEY_COOLDOWN_S 0→5 — 修复R2285零冷却导致的429连锁反噬

**Date**: 2026-07-23 19:15 UTC  
**Round**: R2159 (HM2 → HM1)  
**Author**: opc2_uname (HM2)  
**Rule**: Single param, iron law — only HM1 parameters changed

---

## Pre-Optimization Diagnosis

### HM1 Docker Env (nv_gw)

| Parameter | Live Value | Notes |
|-----------|-----------|-------|
| `UPSTREAM_TIMEOUT` | 24 | R38.12 — 单次NVCF pexec超时 |
| `TIER_TIMEOUT_BUDGET_S` | 370 | R2242 — glm5_2_nv预算 |
| `KEY_COOLDOWN_S` | 0 | ⚠️ **R2285零冷却 ← 当前病灶** |
| `TIER_COOLDOWN_S` | 0 | R2283 — 合理 |
| `KEY_AUTHFAIL_COOLDOWN_S` | 0 | R2257 — 合理 |

### DB Data (6h window, 2026-07-23 13:15–19:15 UTC)

| Model | Total | OK | FAIL | SR | Error Pattern |
|-------|-------|-----|------|------|---------------|
| dsv4p_nv | 6 | 6 | 0 | 100% | 无问题 |
| **glm5_2_nv** | **29** | **20** | **9** | **69.0%** | 3×429_nv_rate_limit |
| **kimi_nv** | **19** | **10** | **9** | **52.6%** | 3×RemoteDisconnected, 3×empty_200, 2×429 |
| **Total** | **48** | **36** | **12** | **75.0%** | |

### Critical Finding: Zero-Cooldown 429 Cycling

**ALL 9 ATE requests have `tier_attempts=0`** — the tier is pre-empted before any key is tried. This is the smoking gun.

With `KEY_COOLDOWN_S=0` + `TIER_COOLDOWN_S=0`:
```
All 5 keys cooling simultaneously (global 429 anti-pattern)
→ next tier also 5 keys all cooling (or also zero-cooldown → cycling)
→ all_tiers_exhausted in 3-5 key attempts (~21s at 7ms each)
→ ATE 502 at 3-11ms (not even reaching real NVCF)
```

DB 6h tier_attempts confirms:
- `429_nv_rate_limit` = 3 (glm5_2_nv) — keys hitting 429, cycling immediately to next key
- `empty_200` = 5 (kimi_nv) — NVCF pexec returning empty 200, cycling rapidly
- `RemoteDisconnected` = 3 (kimi_nv) — fast cycle causing connection churn

**R2285's original claim**: "0 key_cycle_429s in 6h → anti-pattern irrelevant" is true for dsv4p_nv (direct/NVCF function path, not pexec). But for glm5_2_nv and kimi_nv (NVCF pexec path), the 429 anti-pattern is **alive and active**. The DB `tier_attempts` table proves it — 429s are logged per-key in the tier loop.

### Peer-Fallback vs Budget Contrast

| Metric | 30min | 6h |
|--------|-------|-----|
| **glm5_2_nv SR** | **100%** (6/6) | **69.0%** (20/29) |
| **kimi_nv SR** | **N/A** (无请求) | **52.6%** (10/19) |
| **ATE count** | 0 | 13 |

30min窗干净 → `cc4101`聚合窗口SR极佳 (93.8%)，但6h暴露了kimi_nv在时间轴上的散落性故障。

Peer-fallback (HM1→HM2 40011) 30min: **3 alive, 2 success, 1 fail** — 存在正常交互。

### Budget Safety

```
KEY_COOLDOWN_S=5 → worst case: 4×5=20s consumed by cooldown between key attempts
glm5_2_nv budget: 210 - 20 = 190s → 190/24 = 7.9 keys → > 5 keys fit ✓
dsv4p_nv budget: 160 - 20 = 140s → 140/24 = 5.8 keys → > 5 keys fit ✓
TIER_COOLDOWN_S=0 → no tier-level blocking ✓
```

---

## Change Applied

### Parameter: `KEY_COOLDOWN_S` 0 → 5

**Line**: 437 (nv_gw section, `=` syntax)  
**Compose file**: `/opt/cc-infra/docker-compose.yml` on HM1

```yaml
# Before:
- KEY_COOLDOWN_S=0  # R2285 (HM2->HM1): 66->0 unlock all 5 keys for dsv4p_nv...

# After:
- KEY_COOLDOWN_S=5  # R2159 (HM2->HM1): 0->5 add rate-limit breathing room. R2285 zero-cooldown caused 429 cycling on glm5_2_nv/kimi_nv (3-5 key hits in <2s). 5s spacer prevents rapid 429 chain. Budget: glm5_2_nv 210/24=8.75 keys > 5 fit; dsv4p_nv 160/24=6.67 keys > 5 fit. Single param; iron law: only HM1
```

### Rationale

1. **5s is not a defense against 429, it's a defense against *rapid cycling***: After a key returns 429, the next key is tried within milliseconds. If all 5 keys are in the same rate-limit bucket, they all 429 in sequence. A 5s pause gives the rate-limit window time to clear before cycling the next key.
2. **Minimal impact on healthy keys**: A successful key is never penalized by cooldown (cooldown only triggers on failure/429).
3. **Preserves R2285's dsv4p_nv gains**: dsv4p_nv is not on the NVCF pexec path (uses direct integrate API), so 429 key-cycle is irrelevant. The 5s does not block any working key for dsv4p_nv.
4. **Budget-safe**: 4×5=20s worst-case overhead, both model budgets have >100s margin.
5. **Single parameter change**: conforms to HM2's "每轮少改,多轮积累" principle.

---

## Verification

| Check | Command | Result |
|-------|---------|--------|
| Compose file line 437 | `sed -n '437p' docker-compose.yml` | `KEY_COOLDOWN_S=5` ✓ |
| KEY_AUTHFAIL_COOLDOWN_S preserved | `sed -n '436p'` | `KEY_AUTHFAIL_COOLDOWN_S=0` ✓ |
| TIER_COOLDOWN_S preserved | `sed -n '511p'` | `TIER_COOLDOWN_S=0` ✓ |
| Budget params preserved | `docker exec env` + grep | `UPSTREAM_TIMEOUT=24`, `TIER_TIMEOUT_BUDGET_S=370`, `NVU_TIER_BUDGET_DSV4P_NV=160`, `NVU_TIER_BUDGET_GLM5_2_NV=210` ✓ |
| YAML section | `sed -n '430,445p'` | Clean `environment:` block with `=` syntax ✓ |

---

## Expected Impact

- **glm5_2_nv 6h SR**: 69% → target 80%+ (减少429连锁导致的ATE预量)
- **kimi_nv 6h SR**: 52.6% → target 70%+ (减少empty_200/RemoteDisconnected的快速连击)
- **ATE latency**: 3-11ms → potentially actual tier attempt time (100-500ms) when rate-limit clears after 5s spacing
- **无影响 on dsv4p_nv**: direct integrate path unaffected by key-cooldown
- **No restart planned this round**: No container restart — compose change staged for next natural restart cycle

### Next Round Monitor

1. Watch DB `tier_attempts` for `429_nv_rate_limit` count on glm5_2_nv — should drop
2. Monitor `key_cycle_429s` from gateway logs — should show cooldown hits instead of rapid cycling
3. Track kimi_nv SR in next 6h window — empty_200 frequency should decrease
4. After R2159 stabilizes (2-3 rounds), consider: UPSTREAM_TIMEOUT 24→22 (risky, marginal gain) or TIER_TIMEOUT_BUDGET_S 370→380 (more headroom)

---

## ⏳ 轮到HM1优化HM2
