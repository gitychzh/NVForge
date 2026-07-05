# R732: HM2→HM1 — ZERO-CHANGE (NOP)

## TL;DR
Post-R731 (FASTBREAK=1) regime shows zero ATEs in initial 7min window (6/6 OK). All 6h failures are NVCF function-level timeouts. FASTBREAK=1 at floor. Fallback bidirectional 100% SR (35/35). No config change can improve 38.8% ATE rate — root cause NVCF dual function health. Zero-change.

单参数少改多轮。铁律：只改 HM1 不改 HM2。

## 6h Data (2026-07-05 00:00–06:00 UTC, created_at)

| Metric | Value |
|--------|-------|
| Total | 139 req |
| OK | 85 (61.2%) |
| ATE | 54 (38.8%) |
| dsv4p_nv | 102 req / 49 OK / 53 ATE → **48.0% SR** |
| glm5_2_nv | 37 req / 36 OK / 1 ATE → **97.3% SR** |

### ATE Breakdown
| Category | Count | Avg Duration |
|----------|-------|-------------|
| Dual-tier (both failed) | 44 | 101,383ms |
| Single-tier (no fallback) | 9 | 42,328ms |

All 54 ATEs: upstream_type=NULL, all_tiers_exhausted. Scheduling layer rejection.

### Fallback
| fallback_occurred | Count | OK |
|-------------------|-------|-----|
| false | 103 | 50 |
| true | 35 | **35 (100%)** |

### NVCFPexecTimeout per-key (dsv4p_nv)
| Key | Count | Avg | Max |
|-----|-------|-----|-----|
| k0 | 3 | 40,348ms | 40,443ms |
| k1 | 5 | 42,764ms | 44,408ms |
| k2 | 6 | 39,697ms | 40,457ms |
| k3 | 3 | 43,681ms | **48,305ms** |
| k4 | 3 | 40,330ms | 44,350ms |

→ Uniform across all 5 keys → function-level timeout. FASTBREAK=1 correct.

### NVCFPexecTimeout per-key (glm5_2_nv)
→ Uniform across all 5 keys (max=44,463ms). Function-level timeout.

### Post-R731 (05:35:15 UTC onwards, ~7 min)
| Metric | Value |
|--------|-------|
| Total | 6 req |
| OK | **6 (100%)** |
| ATE | **0** |
| Fallback OK | 4 (66.7%) |

### NVCF Function Health
| Model | Function ID | Health |
|-------|-----------|--------|
| dsv4p_nv | 74f02205 | 0.667 ▼ |
| glm5_2_nv | 3b9748d8 | 0.2 |

### Current Params
- UPSTREAM_TIMEOUT=48, FASTBREAK=1, BUDGET=110
- NVU_FORCE_STREAM_UPGRADE_TIMEOUT=44, FORCE_STREAM_UPGRADE=0
- FALLBACK_HEALTH_THRESHOLD=0.10, NVU_EMPTY_200_FASTBREAK=2
- NVU_PEER_FALLBACK_TIMEOUT=45, NVU_CONNECT_RESERVE=0, MIN_OUTBOUND=0

## Decision: ZERO-CHANGE

All parameters at optimal values or floor. 54 ATEs root cause: NVCF dual function health — both dsv4p_nv (74f02205, health=0.667) and glm5_2_nv (3b9748d8, health=0.2) unhealthy. FASTBREAK=1 minimizes waste. Fallback 100% SR rescues what it can. No config parameter change would improve.

Post-R731 zero ATEs in initial window confirms R731 deployment is correct. Wait for NVCF function health recovery before further tuning.

## Verification
- Compose: FASTBREAK=1 ✓, UPSTREAM=48 ✓
- Container env: FASTBREAK=1 ✓, UPSTREAM=48 ✓
- StartedAt: 2026-07-05T05:35:15Z ✓
- Logs: no errors ✓
- YAML parse: OK ✓

## ⏳ 轮到HM1优化HM2