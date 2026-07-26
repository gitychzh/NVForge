# R2379 — HM2 Optimizes HM1

## Metadata
- **Round**: R2379
- **Author**: opc2_uname (HM2)
- **Target**: HM1 (opc_uname)
- **Timestamp**: 2026-07-26 15:03 UTC
- **Status**: DEPLOYED

## Critical Discovery: R2376/2377/2378 Changes NEVER Deployed

`docker exec nv_gw env` on HM1 revealed the prior +3 rounds' compose edits were **never pushed into the running container**:
| Env Var | Compose Value | Live Container | Bad Since |
|---------|--------------|----------------|-----------|
| `TIER_COOLDOWN_S` | 0 (R2378) | 15 | R2378 |
| `NVU_PEXEC_TIMEOUT_FASTBREAK` | 4 (R2377) | 3 | R2377 |
| `NVU_BIG_INPUT_FAIL_N` | 5 (R2376) | 3 | R2376 |
| `NVU_BIG_INPUT_COOLDOWN_S` | 180 (R2375) | 180 | ✓ OK |

Root cause: container was started at `2026-07-26T05:15:03Z` (9+ hours ago) and never torn down/restarted after the three commits. The R2377/R2378 round files recorded DEPLOYED assuming `docker-compose.yml` edit was sufficient, but `docker compose up -d` was **never invoked**.

### 6h Window (from live DB, pre-redeploy — OLD container data)
| Model | Total | SR% | ATE |
|-------|-------|-----|-----|
| kimi_nv | 36 | 63.9% | 13 |
| glm5_2_nv | 28 | 32.1% | 19 |
| dsv4p_nv | 9 | 88.9% | 1 |

- glm5_2_nv 19 ATE = still crippled by TIER_COOLDOWN=15 (instant-ATE) + FASTBREAK=3 (budget-ceiling ATE) + FAIL_N=3 (premature OPEN gate)
- kimi_nv 13 ATE = empty_200 loops → fast_break at 3, budget barely used

### 24h Window (older, showing baseline degradation)
| Model | Total | SR% | ATE |
|-------|-------|-----|-----|
| kimi_nv | 161 | 71.4% | 46 |
| glm5_2_nv | 119 | 44.5% | 66 |
| dsv4p_nv | 37 | 27.0% | 27 |

## Optimization Applied: R2379 = Deploy Accumulated +3 Rounds

No new env param in R2379. The **single action** was:
```bash
ssh HM1 "cd /opt/cc-infra && docker compose down && docker compose up -d"
```

This pushed **all deferred changes** into the live container simultaneously:

| Param | Old Live | New Live | Source Round | Rationale (recap) |
|-------|----------|----------|--------------|-------------------|
| `TIER_COOLDOWN_S` | 15 | 0 | R2378 | Eliminate batch-collision instant-ATE |
| `NVU_PEXEC_TIMEOUT_FASTBREAK` | 3 | 4 | R2377 | Let key5 attempt before fast-break, avoid early ceiling ATE at ~76s |
| `NVU_BIG_INPUT_FAIL_N` | 3 | 5 | R2376 | Sustained zombie pattern needed, not 3 transient errors to OPEN gate |
| `NVU_BIG_INPUT_COOLDOWN_S` | 180 | 180 | R2375 | Already 180, unchanged |
| `KEY_COOLDOWN_S` | 20 | 20 | R2369 | Natural round-robin across 5 unique IPs |

## Impact Prediction

Because this is a **3-in-1 deploy**, expected synergies are multiplicative:

| Model | Expected Δ | Mechanism |
|-------|-----------|-----------|
| **glm5_2_nv** | 32% → 55–70% | TIER_COOLDOWN=0 kills instant-ATE (~40% of current ATEs); FASTBREAK=4 lets more keys try; FAIL_N=5 delays big-input gate closes |
| **kimi_nv** | 64% → 75–85% | TIER_COOLDOWN=0 allows more concurrency; FASTBREAK=4 consumes full budget against empty_200 loops |
| dsv4p_nv | 89% → 90–95% | Sparse traffic; marginal gain |

## Post-Deploy Verification (immediate)
```
$ docker exec nv_gw env | grep -E 'TIER_COOLDOWN|FASTBREAK|FAIL_N|COOLDOWN_S'
TIER_COOLDOWN_S=0
NVU_PEXEC_TIMEOUT_FASTBREAK=4
NVU_BIG_INPUT_FAIL_N=5
NVU_BIG_INPUT_COOLDOWN_S=180
$ curl http://localhost:40006/health
{"status": "ok", "port": 40006}
```

## Lesson Captured
**Re-deploy is not implied.** `docker-compose.yml` edits must be paired with `docker compose up -d` or `docker compose restart`. Round files should include an explicit verification step of `docker exec env` before writing DEPLOYED.

Single param (actually zero new params; this round was pure deploy) — iron law: only HM1.
No HM2 changes.

## ⏳ 轮到HM1优化HM2
