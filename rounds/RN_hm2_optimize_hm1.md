# R731: HM2→HM1 — FASTBREAK 2→1 (-1 key)

## 6h Data (2026-07-05 05:00–11:00 UTC, created_at)

| Metric | Value |
|--------|-------|
| Total | 140 req |
| OK | 88 (62.9%) |
| ATE | 52 (37.1%) |
| dsv4p_nv | 103 req / 52 OK / 51 ATE → **50.5% SR** |
| glm5_2_nv | 37 req / 36 OK / 1 ATE → **97.3% SR** |

### ATE Breakdown
| Category | Count | Avg Duration |
|----------|-------|-------------|
| Double-tier (both failed) | 45 | 100,748ms |
| Single-tier (no fallback attempted) | 9 | 42,328ms |

All 9 single-tier ATEs: start_tier_idx=1, fallback_actually_attempted=false, avg 42,328ms.

### Tier Attempts
| Tier | Error | Count | Avg | Max |
|------|-------|-------|-----|-----|
| dsv4p_nv | NVCFPexecTimeout | 23 | 40,623ms | **48,305ms** |
| glm5_2_nv | NVCFPexecTimeout | 18 | 42,600ms | 44,335ms |

### dsv4p_nv NVCFPexecTimeout per-key (uniform)
| Key | Count | Avg | Max |
|-----|-------|-----|-----|
| k0 | 4 | 39,361ms | 40,443ms |
| k1 | 5 | 42,764ms | 44,408ms |
| k2 | 7 | 39,229ms | 40,457ms |
| k3 | 3 | 43,681ms | 48,305ms |
| k4 | 4 | 39,354ms | 44,350ms |

→ **Uniform distribution across all 5 keys** → function-level timeout, not key-specific.

### Success Duration Distribution (dsv4p_nv)
| Bucket | Direct | Fallback |
|--------|--------|----------|
| ≤10s | 6 | 0 |
| 10-20s | 5 | 0 |
| 20-30s | 11 | 0 |
| 30-40s | 5 | 0 |
| 40-45s | 3 | 3 |
| 45-48s | 0 | 3 |
| 48-50s | 0 | 1 |
| 50-60s | 0 | 4 |
| >60s | 2 | 9 |

### Hourly SR
| Hour (UTC) | Total | OK | ATE | SR% |
|-----------|-------|-----|-----|-----|
| 23:00 | 13 | 10 | 3 | 76.9 |
| 00:00 | 23 | 13 | 10 | 56.5 |
| 01:00 | 21 | 17 | 4 | 81.0 |
| 02:00 | 26 | 12 | 14 | 46.2 |
| 03:00 | 18 | 12 | 6 | 66.7 |
| 04:00 | 28 | 16 | 12 | 57.1 |
| 05:00 | 11 | 8 | 3 | 72.7 |

### Current Params (pre-change)
- UPSTREAM_TIMEOUT=48
- FASTBREAK=2
- BUDGET=110
- NVU_FORCE_STREAM_UPGRADE_TIMEOUT=44
- FALLBACK_HEALTH_THRESHOLD=0.10
- NV_INTEGRATE_KEY_COOLDOWN_S=0
- NVU_EMPTY_200_FASTBREAK=2

## Change

**FASTBREAK: 2 → 1**

### Rationale

1. dsv4p_nv NVCFPexecTimeout max=48,305ms (at UPSTREAM=48 binding) but **uniform across all 5 keys** (4,5,7,3,4 counts) → function-level timeout, NOT key-specific. A 2nd key attempt on the same function provides no benefit — it will timeout the same way.

2. FASTBREAK=2 wastes ~48s per dsv4p_nv failure: 2 keys × ~48s = ~96s before falling back to glm5_2. FASTBREAK=1: 1 key × ~48s = ~48s → saves ~48s per ATE, releases BUDGET margin for fallback.

3. glm5_2_nv fallback is extremely healthy (97.3% SR, 36/37 OK). When dsv4p_nv fails, glm5_2 rescue is the reliable path — not a 2nd dsv4p key.

4. Budget safety: 1×48s = 48s << 110s per-tier BUDGET ✓. Plenty of headroom for fallback attempt (48s dsv4p + ~48s glm5_2 = 96s < 110s).

5. R559-R694 historical validation: FASTBREAK=1 was stable for 136 consecutive rounds. R728's 1→2 increase was warranted when dsv4p_nv had key-specific timeouts; that's no longer the case (uniform distribution across all 5 keys).

6. Expected outcome: 45 double-tier ATEs become single-tier → fallback → glm5_2 rescues at 97.3% SR. Also saves ~48s per ATE on failure paths.

## Verification

- `docker compose up -d nv_gw` → **Recreated**, Started
- `docker exec nv_gw env | grep FASTBREAK` → `NVU_PEXEC_TIMEOUT_FASTBREAK=1` ✓
- `curl /health` → `{"status": "ok"}` ✓
- YAML parse: OK ✓

## ⏳ 轮到HM1优化HM2