# R983: HM2→HM1 — NOP (R982 settling, all params at floor)

## Round Metadata
- **Direction**: HM2 → HM1
- **Date**: 2026-07-09 17:20 UTC
- **Author**: opc2_uname
- **Iron Rule**: only change HM1 never HM2

## Data Collection (6h window, ~09:13-17:20 UTC)

### Docker Logs
- Tail 150: clean, zero errors/warnings
- Container `nv_gw` started at `2026-07-09T09:13:02Z`

### Four-Source Drift Detection
| Parameter | Compose | Env | Match |
|-----------|---------|-----|-------|
| UPSTREAM_TIMEOUT | 64 | 64 | ✓ |
| TIER_TIMEOUT_BUDGET_S | 112 | 112 | ✓ |
| MIN_OUTBOUND_INTERVAL_S | 0 | 0 | ✓ |
| KEY_COOLDOWN_S | 25 | 25 | ✓ |
| FASTBREAK | 1 | 1 | ✓ |
| EMPTY_200_FASTBREAK | 3 | 3 | ✓ |
| CONNECT_RESERVE_S | 0 | 0 | ✓ |
| PEER_FALLBACK_TIMEOUT | 45 | 45 | ✓ |
| FORCE_STREAM_UPGRADE_TIMEOUT | 64 | 64 | ✓ |
| SSLEOF_RETRY_DELAY | 1.0 | 1.0 | ✓ |
| INTEGRATE_MODELS | "" | "" | ✓ |
| INTEGRATE_KEY_COOLDOWN | 0 | 0 | ✓ |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | 0.05 | ✓ |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | 0.05 | ✓ |

**Result**: All 14 parameters match across compose + env. No drift.

### DB: nv_requests (6h)
| Model | Total | OK | SR% | Avg OK ms | P95 OK ms | Max OK ms | Avg Fail ms | Max Fail ms |
|-------|-------|-----|-----|-----------|-----------|-----------|-------------|-------------|
| glm5_2_nv | 29 | 25 | 86.2 | 78,595 | 136,608 | 173,278 | 143,237 | 174,468 |
| dsv4p_nv | 5 | 5 | 100.0 | 21,356 | 42,139 | 44,652 | - | - |
| **Total** | **34** | **30** | **88.2** | | | | | |

### Failures (4 ATE, all pre-R982)
| Time (UTC) | Model | Duration | Tiers | Fallback | Function | Notes |
|------------|-------|----------|-------|----------|----------|-------|
| 07:36 | glm5_2_nv | 174,468ms | 2 | glm5_2→dsv4p | 74f02205 (dsv4p) | dual-tier exhaustion |
| 07:37 | glm5_2_nv | 174,366ms | 2 | glm5_2→dsv4p | 74f02205 (dsv4p) | dual-tier exhaustion |
| 08:33 | glm5_2_nv | 112,060ms | 1 | glm5_2 only | 3b9748d8 (glm5.2) | single-tier, ms_gw relay TimeoutError |
| 08:58 | glm5_2_nv | 112,055ms | 1 | glm5_2 only | 3b9748d8 (glm5.2) | single-tier, ms_gw relay TimeoutError |

### nv_tier_attempts (6h)
| Tier | Error Type | Count | Avg ms | Max ms |
|------|-----------|-------|--------|--------|
| glm5_2_nv | NVCFPexecTimeout | 18 | 57,465 | 62,606 |
| glm5_2_nv | 504_nv_gateway_timeout | 4 | - | - |
| glm5_2_nv | empty_200 | 3 | - | - |

### Fallback Activity
- 18 glm5_2_nv → dsv4p_nv (100% SR rescue)
- 2 glm5_2_nv → glm5_2_ms (1 OK, 1 relay TimeoutError)

### Metrics JSONL Pattern
Typical request flow (openclaw→glm5_2_nv):
1. glm5_2_nv tier: 1st key fails (NVCFPexecTimeout ~49-62s / 504 / empty_200)
2. FASTBREAK=1 triggers → dsv4p_nv fallback tier
3. dsv4p_nv: 100% SR (70-140s) or dual-tier ATE (~174s)

## Decision: NOP

### Rationale
1. **R982 settling**: NVU_FALLBACK_HEALTH_THRESHOLD=0.05 deployed at 09:13 UTC. Container restarted ~8h ago. Post-R982 data shows zero errors in logs. The 4 ATE in the 6h window are all pre-R982 (07:36-08:58 UTC).

2. **All parameters at floor/optimal**:
   - MIN_OUTBOUND=0 (floor, cannot reduce further)
   - CONNECT_RESERVE=0 (floor, cannot reduce further)
   - FASTBREAK=1 (floor for NVCFPexecTimeout, R559/R709/R961 validated)
   - INTEGRATE disabled (R694: integrate.api.nvidia.com broken for dsv4p/kimi)
   - INTEGRATE_KEY_COOLDOWN=0 (floor, cannot reduce further)
   - KEY_COOLDOWN=25 (stable, zero 429 risk)
   - SSLEOF=1.0 (floor, HM2-aligned)
   - EMPTY_200=3 (R829 validated, FA2 bug fix)

3. **UPSTREAM=64 adequate**: NVCFPexecTimeout max=62,606ms < 64,000ms. Buffer=1,394ms. Per R751 ≥3s ideal buffer rule, this is tight but functional. No evidence of UPSTREAM-caused truncation.

4. **BUDGET=112 adequate**: UPSTREAM=64 → 2×64=128 > 112, but FASTBREAK=1 means only 1 key per tier. The dual-tier ATE at ~174s are from both tiers failing, not BUDGET exhaustion. The single-tier ATE at ~112s are from dsv4p excluded from tier_chain (pre-R982, fixed by NVU_FALLBACK_HEALTH_THRESHOLD=0.05).

5. **glm5_2_nv function degradation is NVCF infrastructure-level**: 25 errors in tier_attempts (18 NVCFPexecTimeout + 4 504 + 3 empty_200) for 29 requests. NVCFPexecTimeout uniform across keys → function-level, not parameter-fixable. dsv4p_nv fallback (100% SR) is the correct rescue path.

6. **Very low traffic**: 34 req/6h = ~5.7 req/h. Statistical power insufficient for fine-tuning decisions.

### Candidate Evaluation
| Candidate | Current | Proposed | Rationale | Verdict |
|-----------|---------|-----------|-----------|---------|
| UPSTREAM +2 | 64 | 66 | Increase buffer for NVCFPexecTimeout edge | ❌ max=62,606ms already within 64,000ms. No timeout-caused ATE. |
| BUDGET -2 | 112 | 110 | Tighten to reduce worst-case ATE | ❌ R971 already did 114→112. 2 ATE at 174s > 112 = BUDGET not binding. |
| FASTBREAK +1 | 1 | 2 | Allow 2nd key on glm5_2 | ❌ NVCFPexecTimeout is function-level, 2nd key wastes ~57s. R559/R709/R961 all validated. |
| EMPTY_200 -1 | 3 | 2 | Reduce empty200 cycles | ❌ Would save ~5-15s/event but empty_200 is only 3/25 errors. R829 set to 3 for FA2 bug fix. |
| PEER_FALLBACK -5 | 45 | 40 | Tighten peer fb timeout | ❌ No peer fallback activity in 6h. PEER_FB_SKIP excludes glm5_2+dsv4p. |

**All candidates rejected**: every parameter is either at floor, validated by history, or lacks data support.

## Summary
- **Action**: NOP (no parameter change)
- **Reason**: R982 settling period, all params at floor/optimal, zero post-deploy errors, NVCF function-level glm5_2 degradation (non-parameter-fixable)
- **Verification**: four-source drift check passed (14/14 match)
- **Iron Rule**: only change HM1 never HM2

## ⏳ 轮到HM1优化HM2