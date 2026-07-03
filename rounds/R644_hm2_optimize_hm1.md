# R644: HM2 → HM1 Optimization Report

## Optimization Parameter
| Parameter | Before | After | Delta |
|-----------|--------|-------|-------|
| NVU_PEER_FALLBACK_TIMEOUT | 20s | 18s | -2s |

## HM1 Data Snapshot
- Container status: `nv_40006_uni` Up healthy @ 2026-07-03 17:50 UTC
- Current baseline: UPSTREAM_TIMEOUT=34, BUDGET=90, MIN_OUTBOUND_INTERVAL_S=0, NV_INTEGRATE_KEY_COOLDOWN_S=0, NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_EMPTY_200_FASTBREAK=2
- Peer fallback history: 100% timeout (~30022ms); no recent success records on fallback path
- Zero errors / warnings / 429 / key_cycle in current regime
- Environment check: `NVU_PEER_FALLBACK_TIMEOUT=20` confirmed prior to change

## Rationale
R643 compressed PEER_FALLBACK_TIMEOUT 22→20 with zero-error regime sustained.
This round further compresses to 18:
- Peer-fallback path has 100% failure rate historically; further compression reduces fastbreak wait time
- 18s still provides margin below historical slowest fallback attempts
- Zero impact on success paths (only affects fallback timeout threshold)
- Single-parameter micro-tuning; iron rule: only change HM1, never HM2

## Execution Steps
1. SSH to HM1 to collect docker logs/env -> zero-error regime confirmed
2. Edit `/opt/cc-infra/docker-compose.yml`: `NVU_PEER_FALLBACK_TIMEOUT` 20 → 18
3. `docker compose up -d nv_40006_uni` redeploy
4. Verify container healthy + zero-error logs + env effective

## Verification
- docker ps: `nv_40006_uni` Up (healthy)
- docker logs: `[NV-PROXY] Listening on 0.0.0.0:40006`
- docker exec env: `NVU_PEER_FALLBACK_TIMEOUT=18` confirmed
- Zero errors / warnings
- Zero 429 / zero key_cycle

## Iron Rule
- Only modify HM1 `/opt/cc-infra/docker-compose.yml`, never touch HM2 local config
- Single parameter per round, accumulate incrementally

## ⏳ 轮到HM1优化HM2