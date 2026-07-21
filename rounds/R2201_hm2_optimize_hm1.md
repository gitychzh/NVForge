# R2201 (HM2→HM1): TIER_COOLDOWN_S 1→3 (+2s) — Course Correction

**Date**: 2026-07-22 00:10 UTC
**Author**: opc2_uname (HM2)
**Iron law**: 只改HM1不改HM2 ✓

## Pre-Change Data (HM1 6h window)

| Metric | Value |
|---|---|
| Total requests | 32 |
| OK | 22 (68.8% SR) |
| Fail | 10 |
| zombie_empty_completion | 10 (9 glm5_2_nv, 1 dsv4p_nv) |
| ATE | 0 |
| OK avg duration | 17816ms |
| Key cycling (cycle1) | 19/32 (59.4%) |
| Key cycling (cycle2+) | 9/32 (28.1%) |
| Total cycling | 28/32 (87.5%) |

**Per-model**:
- glm5_2_nv: 28req/19OK(67.9%)/9zombie, avg 17816ms
- dsv4p_nv: 4req/3OK(75.0%)/1zombie, avg 22823ms

**Recent OK durations (glm5_2_nv)**: 23416, 12695, 93401, 44638, 28337, 13617, 17883, 30772, 15458, 10226, 24072, 11504ms

**30min window**: 2req/1OK(50.0%), 1 zombie, avg 20603ms

## Root Cause Analysis

R2199 reduced TIER_COOLDOWN_S from 2→1, and R2200 reduced KEY_COOLDOWN_S from 12→10. The combined effect: TIER=1s causes the gateway to cycle through ALL 5 keys in rapid succession on every request. With KEY_COOLDOWN_S=10, the fast-cycling keys (K1, K2) get exhausted quickly, forcing each request to cycle 1-2 extra keys (87.5% cycling rate). This exposes slow keys (K3/K4 proxy paths) on every request, degrading OK avg from 13790ms (R2198) to 20139ms (R2200) and further to 17816ms (current).

The zombie pattern is well-known: glm5_2_nv pexec_success with empty content (thinking-only responses). These are upstream NVCF behavior, not config-fixable. The key insight is that TIER=1s is TOO AGGRESSIVE — it eliminates tier-level cooldown entirely, making every request a 5-key race.

## Change

| Parameter | Before | After | Delta |
|---|---|---|---|
| TIER_COOLDOWN_S | 1 | 3 | +2s |

**Rationale**: TIER=3 restores a modest 3s tier cooldown, giving the preferred key (K1/K2) more time to recover between requests. This reduces key cycling frequency and avoids the slow K3/K4 penalty. TIER=3 is still very aggressive (was 38 before R2146-R2199 trajectory), but strikes a balance between the R2199 "no cooldown" extreme and the R2180-era 38s conservative.

**Budget check**: KEY+TIER+GLM5_2 = 10+3+28 = 41 << 153 BUDGET (112s margin). Safe.

## Verification

```bash
# Live env after restart
$ docker exec nv_gw env | grep TIER_COOLDOWN
TIER_COOLDOWN_S=3

# Health check
$ curl -s http://localhost:40006/health
{"status": "ok", "proxy_role": "passthrough", ...}
```

- Container restarted cleanly (stop + up -d)
- Live env confirms TIER_COOLDOWN_S=3
- No other parameters changed
- Only HM1 modified (iron law ✓)

## Post-Change Expectations

- Reduced key cycling rate (target < 50% from 87.5%)
- OK avg duration should decrease (avoiding slow K3/K4 paths)
- Zombie rate unchanged (NVCF upstream behavior, not config-fixable)
- SR should remain stable or improve slightly

## ⏳ 轮到HM1优化HM2