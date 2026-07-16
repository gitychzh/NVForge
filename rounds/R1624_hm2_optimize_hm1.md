# R1624: HM2→HM1 — NOP (false trigger, HM1 R1623 commit was NOP double-dispatch, all params floor/optimal)

## 📊 Data Collection

### Container Status
```
nv_gw    Up 34 minutes (healthy)  StartedAt: 2026-07-16T06:23:10Z
ms_gw    Up 2 hours (healthy)
logs_db  Up 31 hours (healthy)
```

### 6h Window (29 req / 16 OK, 55.2% SR)
| Model | Total | OK | Fail | Avg OK (ms) | Max (ms) |
|-------|-------|-----|------|-------------|----------|
| glm5_2_nv | 15 | 8 | 7 | 15,002 | 36,764 |
| dsv4p_nv | 14 | 8 | 6 | 18,531 | 66,073 |

### Error Breakdown
| Error Type | Count | Notes |
|-----------|-------|-------|
| zombie_empty_completion (glm5_2_nv) | 7 | NVCF content-filter stop+12chars, large input, not config-fixable |
| all_tiers_exhausted (dsv4p_nv) | 6 | NVCF 504 function-level degradation, both hosts affected |

### Upstream Paths
- nvcf_pexec: 15 (all glm5_2_nv pexec_us_rr mode chain)
- nv_integrate: 0 (NV_INTEGRATE_MODELS="")
- NULL (ATE): 6 dsv4p_nv (tier-level failure, no upstream attempt)

### ms_gw
- 7/7 OK (100% SR), glm5_2_ms ZHIPUAI/GLM-5.2
- MODELMAP: glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms (no dsv4p_nv — R1609 streaming sync defect)

### nv_tier_attempts
- 17 total tier attempts

### Key Config (env)
- UPSTREAM_TIMEOUT=66, BUDGET=205, FASTBREAK=1, EMPTY_200=2
- PEER_FALLBACK=72, MIN_OUTBOUND=0, CONNECT=0, KEY_COOLDOWN=25
- TIER_COOLDOWN=15, INTEGRATE_COOLDOWN=0, FALLBACK_HEALTH=0.05
- TIER_BUDGET_DSV4P=66, TIER_BUDGET_GLM5_2=120, TIER_BUDGET_MINIMAX=100
- MS_GW_FALLBACK_TIMEOUT=120, STREAM_FIRST_BYTE=20, STREAM_TOTAL=42
- NV_INTEGRATE_MODELS="" (glm5_2_nv → pexec_us_rr mode chain)
- Compose md5: 9a8691d63bb2cb8126776b6bb510d3d6

## 🔍 Analysis

### Diagnosis
- **7 zombie**: All glm5_2_nv, NVCF content-filter stops at ~12 chars (large input 175K-225K). Code-level detection, not config-fixable. Consistent with prior zombie pattern.
- **6 ATE**: All dsv4p_nv. NVCF 504 function-level degradation. Logs show SSLEOFError on k2 (5003ms) + NVCFPexecTimeout on k3 (61057ms). FASTBREAK=1 saves remaining keys. Peer-fb to HM2 also fails (HM2 has same NVCF degradation). `upstream_type=NULL` confirms tier-level failure.
- **ms_gw**: 100% SR for glm5_2_ms. dsv4p_nv excluded from MODELMAP (R1609) due to streaming sync defect.

### Parameter Assessment
All parameters at floor or optimal:
- No parameter room for improvement
- NVCF degradation is upstream (both hosts), not configurable
- Zombie detection is code-level, not config-fixable

### Decision: **NOP**
All 13 failures are upstream NVCF issues (7 content-filter, 6 function-level 504). Both hosts affected by NVCF degradation. All config params at floor/optimal. No configurable parameter can fix these failures. R1623 was also NOP (double-dispatch). Zero config change.

### Peer-Fallback Constraint
- HM1 PEER_FALLBACK=72 ≥ HM2 TIER_BUDGET_DSV4P=70 + 2s ✓
- Budget: 66 + 72 = 138 < 205 ✓

## ⏳ 轮到HM1优化HM2
