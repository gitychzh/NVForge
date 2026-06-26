# R69: HM2→HM1 — TIER_TIMEOUT_BUDGET_S 102→104 (+2s)

## Metadata
- **Date**: 2026-06-26
- **Actor**: HM2 (opc2_uname) → HM1 (100.109.153.83)
- **Previous Round**: R68 (HM2→HM1: UPSTREAM 58→60)
- **Commit**: R69: HM2→HM1 — TIER_TIMEOUT_BUDGET_S 102→104

## Data Collection (30-minute window on HM1)

### Current Config (from `docker exec hm40006 env`)
| Parameter | Value | Line (compose) |
|----------|-------|-----------------|
| UPSTREAM_TIMEOUT | 60 | 417 |
| TIER_TIMEOUT_BUDGET_S | 102 | 418 |
| HM_CONNECT_RESERVE_S | 22 | 451 |
| KEY_COOLDOWN_S | 34.0 | 421 |
| MIN_OUTBOUND_INTERVAL_S | 14.5 | 420 |
| TIER_COOLDOWN_S | 82 | 422 |

### Error Distribution (hm_tier_attempts, 30-min)
```
429_nv_rate_limit:             938 (86.0%)
NVCFPexecConnectionResetError:  72 (6.6%)
NVCFPexecTimeout:                47 (4.3%)
NVCFPexecRemoteDisconnected:     7 (0.6%)
budget_exhausted_after_connect: 3 (0.3%)
Total:                        1067
```

### Fallback Rate (hm_requests, 30-min)
- Fallback: 77.9% (857/1100)
- Direct (glm5.1): 22.1% (243)
- glm5.1 direct success rate: 22.8% (250/1097)

### 429 Cycle Distribution (key_cycle_429s)
- 0 cycles: 797 (72.7%)
- 1+ cycles: 299 (27.3%)
- 429 cycle rate: 27.3% (still elevated)

### Deepseek Timeout Buckets (NVCFPexecTimeout, 30-min, 47 total)
```
<20s:      9 (19.1%)
20-25s:    1 (2.1%)
30-35s:    4 (8.5%)
40-55s:   10 (21.3%) — dominant boundary
>55s:      5 (10.6%) — infrastructure-level
Kimi tier: 18 (38.3%)
```

### ConnectionResetError by Key (glm5.1 tier)
```
k0: 20, k1: 16, k2: 15, k3: 11, k4: 10
Total: 72 — even distribution, mihomo proxy-level
```

### 0-Tier Failures
- **0 (zero) — sustained elimination** (R60→R69: 6+ consecutive rounds)

### Per-Key 429 Distribution (glm5.1 tier)
```
k0: 207, k1: 188, k2: 192, k3: 174, k4: 170
Total: 931 — uniform across all keys, function-level rate limit
```

### Latest 10 Requests (latency snapshot)
```
All glm5.1_hm_nv direct successes (no fallback)
avg duration: 13,181ms to 33,597ms
All status=200, no errors in recent 10
```

## Diagnosis

### 1. Budget Math at UPSTREAM=60

```
UPSTREAM=60, BUDGET=102, RESERVE=22
1st = min(60, 102-22=80) = 60s
remain = 102-60 = 42
2nd = max(10, min(60, 42-22=20)) = 20s ← at decision boundary
```

R68 raised UPSTREAM 58→60, pushing 2nd-attempt to 20s — the decision boundary (R56 validated safe at 20s). R68's report predicted: "Next UPSTREAM→62 gives 2nd=18s — R69 MUST expand BUDGET first (102→104, restoring 2nd=22s)."

### 2. ConnectionResetError at 72

- 72 events (6.6% of errors) — the second-largest error category
- Even distribution across all 5 keys (k0-k4: 20-10 range)
- Slight decrease from R68's pre-deploy value of 73
- MIN_INTERVAL at 14.5 (applied R67: 14.0→14.5) is providing adequate protection
- Not yet at trigger level (>60 with 2+ round upward trend) — stable at ~72

### 3. 429 Rate Still Dominant

- 938 events (86.0% of errors) — the primary bottleneck
- 27.3% of requests encounter 429 cycles (299/1096)
- Uniform key distribution confirms function-level rate limit
- glm5.1 direct success at 22.8% — improving but still low
- KEY_COOLDOWN at 34.0 (R65: 36→34) — still 4s above HM2's 30

### 4. Decision: BUDGET Expansion

**Evidence chain**:
- R68 prediction: "R69 MUST expand BUDGET first (102→104)"
- 2nd-attempt at 20s (decision boundary, verified safe per R56 at 20s)
- Next UPSTREAM→62 would give 2nd=18s — below hard limit
- BUDGET expansion creates headroom for future UPSTREAM trajectory

**Alternative considered**: KEY_COOLDOWN reduction (34→32)
- 429 cycle rate at 27.3% suggests key cooldown could help
- But R68's prediction is explicit about BUDGET expansion being needed
- The alternating pattern (UPSTREAM → BUDGET → UPSTREAM) takes priority
- KEY_COOLDOWN can be addressed in next round after BUDGET headroom is restored

## Optimization

| Parameter | Before | After | Change | Rationale |
|----------|--------|-------|--------|-----------|
| TIER_TIMEOUT_BUDGET_S | 102 | 104 | +2s | R68 prediction: BUDGET expansion needed at UPSTREAM=60, 2nd=20s. +2s restores 2nd=22s, enables future UPSTREAM→62 |

### Budget Math (post-change)
```
UPSTREAM=60, BUDGET=104, RESERVE=22
1st = min(60, 104-22=82) = 60s
remain = 104-60 = 44
2nd = max(10, min(60, 44-22=22)) = 22s (+2s restored)
```

### BUDGET Trajectory
```
R58:  96→98  (UPSTREAM=54, 2nd=22s)
R61:  98→100 (UPSTREAM=56, 2nd=22s)
R65: 100→102 (UPSTREAM=58, 2nd=22s)
R69: 102→104 (UPSTREAM=60, 2nd=22s) ← current
```

## Execution Record

```bash
# Backup
ssh -p 222 opc_uname@100.109.153.83 'cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak.R69'

# Value change (line 418)
ssh -p 222 opc_uname@100.109.153.83 'cd /opt/cc-infra && sed -i "418s/\"102\"/\"104\"/" docker-compose.yml'

# Deploy
ssh -p 222 opc_uname@100.109.153.83 'cd /opt/cc-infra && docker compose up -d hm40006'

# Verify (post-deploy env values match)
docker exec hm40006 env | grep -E "TIER_TIMEOUT_BUDGET|UPSTREAM|KEY_COOLDOWN|MIN|TIER_COOLDOWN|RESERVE"
→ TIER_TIMEOUT_BUDGET_S=104, UPSTREAM=60, RESERVE=22, KEY=34.0, MIN=14.5, TIER_COOLDOWN=82
```

## Expected Effects

1. **2nd-attempt headroom**: 20s → 22s (+2s restored)
   - Directly benefits deepseek fallback completions (40-55s boundary bucket)
   - Enables future UPSTREAM→62 expansion (2nd=20s, still safe at boundary)

2. **429 cycle overhead**: No direct impact from BUDGET expansion
   - 429 rate at 27.3% requires separate KEY_COOLDOWN or MIN_INTERVAL tuning
   - BUDGET expansion does not address 429 — it addresses fallback headroom

3. **0-tier stability**: 0-tier=0 expected to persist
   - RESERVE=22 is saturated, no further 0-tier improvement from BUDGET
   - The 0-tier=0 streak (R60→R69) is sustained by UPSTREAM expansion, not BUDGET

4. **ConnectionResetError**: Expected stable at 70-75 range
   - MIN_INTERVAL=14.5 is providing adequate pacing
   - No further MIN_INTERVAL increase unless upward trend continues

## Observations

- **429 cycle rate at 27.3%**: Remains elevated. Each 429 cycle adds ~15s latency (32,798ms TTFB for 429 victims vs 17,472ms for non-429). The alternating UPSTREAM/BUDGET pattern is correct, but future rounds should evaluate whether KEY_COOLDOWN reduction (34→32) can complement the BUDGET expansion to address both 429 and timeout bottlenecks simultaneously.

- **ConnectionResetError at 72**: Stable but still significant. MIN_INTERVAL=14.5 (applied R67) is providing adequate protection. Monitor for upward trend — if >75 in next 30-min window, consider MIN_INTERVAL 14.5→15.0.

- **Deepseek per-key timeout distribution**: 40-55s bucket has 10 events — the dominant boundary group. But >55s bucket (5 events, infrastructure-level) and <20s (9 events) suggest the distribution is not heavily skewed. BUDGET expansion to 104 will primarily benefit the 40-55s group.

- **R69 is first BUDGET expansion at UPSTREAM=60**: All previous BUDGET rounds (R58, R61, R65) were at lower UPSTREAM values. The +2s at this high UPSTREAM value may have different effects than at UPSTREAM=54 or 58.

- **glm5.1 direct success at 22.8%**: Actually improving — was 17.3% at R65. The upward trend suggests KEY_COOLDOWN reduction (R63: 38→36, R65: 36→34) is working. Next round should evaluate whether further KEY_COOLDOWN reduction (34→32) can push this above 25%.

## ⏳ 轮到HM1优化HM2  ← 脚本检测此标记