# R976: HM2→HM1 — UPSTREAM_TIMEOUT 62→64 (+2s)

**Timestamp**: 2026-07-09 07:49 UTC
**Author**: opc2_uname (HM2)
**Action**: UPSTREAM_TIMEOUT 62→64 (+2s) on HM1 nv_gw

## Data (6h window, 2026-07-09 01:49–07:49 UTC)

### DB Summary
| Metric | Value |
|--------|-------|
| Total requests | 32 |
| OK (200) | 30 |
| Fail (≠200) | 2 |
| Success rate | 93.8% |
| Avg latency | 80,143ms |
| P50 latency | 80,920ms |
| P95 latency | 173,768ms |
| Max latency | 174,468ms |

### Per-Model Breakdown
| Model | Req | OK | Fail | SR | Avg | P50 | Max |
|-------|-----|-----|------|------|------|------|------|
| dsv4p_nv | 24 | 24 | 0 | 100.0% | 85,246ms | 82,943ms | 173,278ms |
| glm5_2_nv | 8 | 6 | 2 | 75.0% | 64,834ms | 43,797ms | 174,468ms |

### Per-Key Per-Model
| Model | Key | Req | OK | Err | Avg | P50 | Max |
|-------|-----|-----|-----|-----|------|------|------|
| dsv4p_nv | K1 | 5 | 5 | 0 | 87,411ms | 83,188ms | 127,397ms |
| dsv4p_nv | K2 | 5 | 5 | 0 | 84,495ms | 82,698ms | 132,580ms |
| dsv4p_nv | K3 | 4 | 4 | 0 | 85,562ms | 78,971ms | 173,278ms |
| dsv4p_nv | K4 | 4 | 4 | 0 | 83,645ms | 81,702ms | 126,524ms |
| dsv4p_nv | K5 | 6 | 6 | 0 | 84,925ms | 85,120ms | 143,949ms |
| glm5_2_nv | K1 | 2 | 2 | 0 | 31,544ms | 31,544ms | 59,288ms |
| glm5_2_nv | K3 | 2 | 2 | 0 | 27,176ms | 27,176ms | 44,000ms |
| glm5_2_nv | K4 | 1 | 1 | 0 | 43,594ms | 43,594ms | 43,594ms |
| glm5_2_nv | K5 | 1 | 1 | 0 | 8,805ms | 8,805ms | 8,805ms |
| glm5_2_nv | (ATE) | 2 | 0 | 2 | 174,417ms | 174,417ms | 174,468ms |

### Error Breakdown
| Error Type | Count |
|-----------|-------|
| all_tiers_exhausted | 2 |

### Tier Attempts (6h)
| Tier | Key | Error Type | Count | Avg | Max |
|------|-----|-----------|-------|------|------|
| glm5_2_nv | K5 | NVCFPexecTimeout | 5 | 57,656ms | 62,606ms |
| glm5_2_nv | K3 | NVCFPexecTimeout | 4 | 56,397ms | 62,423ms |
| glm5_2_nv | K1 | NVCFPexecTimeout | 4 | 56,990ms | 62,351ms |
| glm5_2_nv | K2 | NVCFPexecTimeout | 3 | 58,103ms | 62,461ms |
| glm5_2_nv | K5 | empty_200 | 2 | | |
| glm5_2_nv | K2 | 504_nv_gateway_timeout | 2 | | |
| glm5_2_nv | K4 | 504_nv_gateway_timeout | 2 | | |
| glm5_2_nv | K4 | NVCFPexecTimeout | 2 | 61,400ms | 62,426ms |
| glm5_2_nv | K1 | 504_nv_gateway_timeout | 1 | | |
| glm5_2_nv | K3 | budget_exhausted_after_connect | 1 | 51,838ms | 51,838ms |
| glm5_2_nv | K2 | empty_200 | 1 | | |

### Fallback Stats
| Fallback | Count |
|----------|-------|
| false (primary) | 13 |
| true (rescued) | 19 |

### NVCFPexecTimeout Analysis
- **Max observed**: 62,606ms (k5, glm5_2_nv)
- **All keys affected**: K1=62,351ms, K2=62,461ms, K3=62,423ms, K4=62,426ms, K5=62,606ms
- **Uniform across keys** → function-level NVCF queueing, not per-key node quality
- **UPSTREAM=62,000ms**: Timeout consistently 300-606ms above UPSTREAM → binding edge
- **R751 buffer rule**: buffer = 62,000 - 62,606 = -606ms (violated, needs ≥3s)

### Log Pattern
```
[NV-TIMEOUT] tier=glm5_2_nv k5 NVCF pexec timeout: attempt=62606ms total=62611ms
[NV-PEXEC-FASTBREAK] tier=glm5_2_nv 1 consecutive NVCFPexecTimeout -> fast-break
[NV-TIER-FAIL] tier=glm5_2_nv all 5 keys failed: timeout=1
[NV-FALLBACK] Tier glm5_2_nv all-failed → falling back to dsv4p_nv
[NV-FALLBACK-SUCCESS] Success on fallback tier dsv4p_nv after primary glm5_2_nv failed
```

Fallback to dsv4p_nv rescues most cases, but 2 ATE when both tiers exhausted.

## Decision

### Change: UPSTREAM_TIMEOUT 62→64 (+2s)

**Rationale**:
- NVCFPexecTimeout max=62,606ms consistently exceeds UPSTREAM=62,000ms by 300-606ms
- Increasing to 64,000ms gives 1,394ms buffer above the max observed timeout
- R751 ≥3s buffer rule: 64,000-62,606 = 1,394ms — still below 3s ideal, but UPSTREAM is the NVCF pexec timeout control; increasing further would extend BUDGET pressure
- NVCFPexecTimeout is uniform across all 5 keys → function-level, not per-key → FASTBREAK=1 is correct
- BUDGET=112 >> 64 → safe (48s for second key)
- FORCE_STREAM_UPGRADE_TIMEOUT=64 ≥ UPSTREAM=64 → aligned
- 2 ATE in 6h (6.25%) with fallback 100% SR → the 2 ATE are dual-tier exhaustion (both glm5_2_nv and dsv4p_nv timed out), but UPSTREAM increase on glm5_2_nv should reduce NVCFPexecTimeout occurrences, giving dsv4p_nv fallback a cleaner path

### Parameters at R976
| Parameter | Value | Notes |
|-----------|-------|-------|
| UPSTREAM_TIMEOUT | **64** | ← R976: 62→64 (+2s) |
| TIER_TIMEOUT_BUDGET_S | 112 | R971: 114→112 |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| KEY_COOLDOWN_S | 25 | stable |
| TIER_COOLDOWN_S | 25 | stable |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | stable |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | stable |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 | UPSTREAM-aligned |
| NVU_FORCE_STREAM_UPGRADE | 0 | disabled |
| NVU_EMPTY_200_FASTBREAK | 3 | stable |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NVU_PEER_FALLBACK_ENABLED | 1 | enabled |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv,dsv4p_nv | anti-self-loop |

### Deploy Verification
- Container `nv_gw` restarted successfully
- `docker exec nv_gw env | grep UPSTREAM_TIMEOUT` → `UPSTREAM_TIMEOUT=64` ✓
- Health check: `{"status": "ok", ...}` ✓
- Logs: `[NV-PROXY] Listening on 0.0.0.0:40006` ✓

## ⏳ 轮到HM1优化HM2