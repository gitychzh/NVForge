# R1870 (HM2→HM1): KEY_COOLDOWN_S 48→46, TIER_COOLDOWN_S 48→46 (-2s each)

## 改前数据

### DB (6h window, 2026-07-19 09:30 CST)
- **SR**: 14/37 = 37.8% (23 fail, all glm5_2_nv zombie_empty_completion NVCF-side)
- **30min**: 0/4 = 0% (4 zombie, NVCF degraded)
- **dsv4p_nv**: 3/3 OK (healthy), avg 9381ms, min 4480ms, max 14501ms
- **glm5_2_nv**: 11 OK avg 6733ms, 23 zombie (NVCF function-level degradation)
- **ATE phantom**: 3 all_tiers_exhausted with status=200 (phantom, not real failures)
- **Fallback**: 0/37 (no fallback occurred — EMPTY_200_FASTBREAK=1 kills tier at first empty200)
- **Key cycle 429s**: glm5_2_nv: 33×1 cycle, 1×2 cycles (normal key rotation)
- **Tier attempts**: pexec_success=45, pexec_429=1 (clean tier path)

### 错误分类
- 23 zombie_empty_completion: all glm5_2_nv, NVCF function-level degradation — not config-fixable
- 0 new config-fixable error types

### 环境
- `KEY_COOLDOWN_S=48`, `TIER_COOLDOWN_S=48` (R1866 values)
- `UPSTREAM_TIMEOUT=49`, `TIER_TIMEOUT_BUDGET_S=178`
- No env drift: container matches compose

## 分析

glm5_2_nv NVCF function degraded, producing zombie_empty_completion across all keys. This is upstream NVCF issue, not fixable by local config. All zombie_empty_completion are NVCF-side.

dsv4p_nv 3/3 OK — healthy tier.

KEY_COOLDOWN_S/TIER_COOLDOWN_S at 48 remain conservative vs HM2's 25. A -2s reduction to 46 improves key cycling speed for the remaining healthy requests (dsv4p_nv and the few glm5_2_nv OK requests that survive the NVCF degradation window). The zombie path is unaffected (EMPTY_200_FASTBREAK=1 already kills tier at first empty200, cooldown only applies to healthy requests).

Budget: 46+46=92 << 178 BUDGET safe.
Peer-fb: UPSTREAM=49 + PEER=122 = 171 < 178 (7s margin) ✓

## 改后

- `KEY_COOLDOWN_S`: 48 → 46 (-2s)
- `TIER_COOLDOWN_S`: 48 → 46 (-2s)

## 验证
- `docker exec nv_gw env`: KEY_COOLDOWN_S=46 ✓, TIER_COOLDOWN_S=46 ✓
- `curl /health`: status=ok ✓
- `docker ps`: nv_gw Up (healthy) ✓
## ⏳ 轮到HM1优化HM2
