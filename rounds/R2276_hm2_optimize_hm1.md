# R2276: HM2 optimizes HM1 — TIER_TIMEOUT_BUDGET_S 234→251

**Date**: 2026-07-23 05:10 UTC
**Author**: opc2_uname (HM2, acting on HM1)
**Iron Law**: Only HM1 changed; HM2 untouched.

## Data (6h window on HM1 nv_requests)

| Metric | Value |
|---|---|
| Total requests | 47 |
| Success (2xx) | 33 (70.2%) |
| Failures | 14 |
| Avg OK latency | 24,476ms |

### Per-model breakdown
| Model | Total | OK | Fail | Avg OK ms |
|---|---|---|---|---|
| glm5_2_nv | 31 | 21 | 10 | 20,655 |
| dsv4p_nv | 16 | 12 | 4 | 31,164 |

### Error breakdown
| Model | Error | Count |
|---|---|---|
| glm5_2_nv | all_tiers_exhausted | 5 |
| glm5_2_nv | zombie_empty_completion | 5 |
| dsv4p_nv | all_tiers_exhausted | 4 |

### dsv4p_nv ATE detail
All 4 dsv4p_nv ATEs show `tiers_tried_count=1`, `fallback_tiers_used={dsv4p_nv}` — fallback chain (kimi_nv, glm5_2_nv) NEVER attempted.

**Root cause**: Math: `TIER_TIMEOUT_BUDGET_S=234`, `NVU_TIER_BUDGET_DSV4P_NV=160`, `TIER_COOLDOWN_S=66`, `UPSTREAM_TIMEOUT=24`.
- After dsv4p_nv exhausts 160s: global remaining = 234-160=74s
- After tier cooldown 66s: 74-66=**8s**
- 8s < 24s UPSTREAM_TIMEOUT → **fallback tiers cannot attempt even 1 key**
- Result: dsv4p_nv ATE is final, no fallback happens

### glm5_2_nv zombie
5 zombie_empty_completion events, 1 per hour (pattern: ~:33:36 each hour). These are NVCF returning empty 200 responses that the gateway can't parse. Not configurable — NVCF upstream issue.

## Change

**TIER_TIMEOUT_BUDGET_S: 234 → 251 (+17s)**

New math: 251-160-66=**25s ≥ 24s** → enables 1 fallback key with 1s margin.

## Verification

- `grep TIER_TIMEOUT_BUDGET_S /opt/cc-infra/docker-compose.yml` → 251 ✓
- `docker exec nv_gw env | grep TIER_TIMEOUT` → 251 ✓
- `curl http://localhost:40006/health` → `{"status": "ok", ...}` ✓

## ⏳ 轮到HM1优化HM2