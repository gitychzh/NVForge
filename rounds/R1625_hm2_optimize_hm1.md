# R1625: HM2→HM1 — NVU_TIER_BUDGET_DSV4P_NV 66→72 (+6s, fix R1611 drift)

## 📊 Data Collection

### Container Status
```
nv_gw    Up 54 minutes (healthy)  StartedAt: 2026-07-16T06:23:10Z
```

### 6h Window (32 req / 17 OK, 53.1% SR)
| Model | Total | OK | Fail | Avg OK Dur (ms) | Max Dur (ms) |
|-------|-------|-----|------|-----------------|-------------|
| dsv4p_nv | 15 | 8 | 7 | 18,531 | 66,073 |
| glm5_2_nv | 17 | 9 | 8 | 15,954 | 36,764 |

### dsv4p_nv Failures (7 ATE, upstream_type=NULL)
- 6h: 7 dsv4p_nv ATE, all tier-level failures (no upstream attempt)
- Log: k3 → 504 (64,644ms) → budget remaining 1.4s < 5s minimum → break
- FASTBREAK=1: one timeout kills the tier, no second key chance
- Peer-fb to HM2: 2/2 FAIL (HM2 also degraded by NVCF 504)

### glm5_2_nv Failures (8 zombie)
- All zombie_empty_completion: NVCF content-filter stop+12chars, large input
- Code-level detection, not config-fixable

### ms_gw
- (not queried this round, prior R1624: 7/7 100% SR)

### Key Config (env)
- UPSTREAM_TIMEOUT=66, BUDGET=205, FASTBREAK=1, EMPTY_200=2
- PEER_FALLBACK=72, MIN_OUTBOUND=0, CONNECT=0, KEY_COOLDOWN=25
- TIER_COOLDOWN=15, INTEGRATE_COOLDOWN=0, FALLBACK_HEALTH=0.05
- TIER_BUDGET_DSV4P=66 (was 66, now 72), TIER_BUDGET_GLM5_2=120, TIER_BUDGET_MINIMAX=100
- MS_GW_FALLBACK_TIMEOUT=120, STREAM_FIRST_BYTE=20, STREAM_TOTAL=42

## 🔍 Analysis

### Diagnosis: R1611 never applied — value drift
Compose line 646 had `NVU_TIER_BUDGET_DSV4P_NV: "66"` but the R1611 comment says "66→72 (+6s)". The value was never actually updated to 72. Container env confirmed 66. This is a configuration drift — the comment was written but the value wasn't changed.

### Evidence
- dsv4p_nv ATE: k3 takes 64,644ms, budget=66,000ms, remaining 1,356ms < 5,000ms minimum → can't try second key
- 7 ATE in 6h, all at exactly 64-66s, all with FASTBREAK=1 saving remaining keys
- With BUDGET=72: same 64.6s first attempt → 7.4s remaining > 5s minimum → second key can be attempted
- 72 + 72 (PEER_FALLBACK) = 144 < 205 BUDGET ✓

### Change
**NVU_TIER_BUDGET_DSV4P_NV: 66→72 (+6s)**
- Single parameter, conservative +6s
- Applies the R1611 change that was never actually applied
- Budget: 72 + 72 = 144 < 205 ✓
- Peer-fallback constraint: 72 ≥ HM2_BUDGET_DSV4P(70) + 2s ✓

## ✅ Verification
```
Container env: NVU_TIER_BUDGET_DSV4P_NV=72 ✓
Container status: Up 12 seconds (healthy) ✓
Health: {"status":"ok"} ✓
```

## ⏳ 轮到HM1优化HM2
