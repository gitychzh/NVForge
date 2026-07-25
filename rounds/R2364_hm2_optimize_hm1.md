# R2364: HM2→HM1 — NVU_BIG_INPUT_COOLDOWN_S 180→120 (breaker recovery speedup with HALF-OPEN safety)

## Change
- **Parameter**: `NVU_BIG_INPUT_COOLDOWN_S`
- **Old**: `180` (R2350)
- **New**: `120`
- **Location**: `/opt/cc-infra/docker-compose.yml` line 449 on HM1
- **Single param delta** ✅ (iron law: only HM1)

## Rationale
- 12h DB: glm5_2_nv 36.5% SR (23/63). ATE breakdown:
  - `all_tiers_exhausted` × 36, avg 10.1s — **24 of these are instant ATE (<1s, 8ms)** = breaker OPEN rejects
  - `zombie_empty_completion` × 4, avg 12.5s — legitimate zombie catches
- The big_input breaker (FAIL_N=3, COOLDOWN=180s) has been OPEN for ~180s per trigger, causing 24 instant ATEs.
- After every breaker OPEN, NVCF recovers quickly but the full 180s cooldown keeps rejecting valid requests.
- **R2349 deployed HALF-OPEN probe** — cooldown expiry no longer jumps from OPEN → all 5 keys; it probes 1 key first.
  - If NVCF still bad: ~1 key timeout (24s) → breaker re-OPEN → saves all remaining keys
  - If NVCF healed: 1 key success → breaker CLOSED → full throughput restored
- **120s is safe** because HALF-OPEN probe guards the transition; even if NVCF hasn't healed, we only lose 1 key (24s) not 5 keys (~100s).
- 60s was rolled back in R2348 due to lack of HALF-OPEN. Now with HALF-OPEN (R2349), 120s is a measured 33% reduction.

## Deployment
- nv_gw restarted with `docker compose up -d` on HM1.
- docker exec env: `NVU_BIG_INPUT_COOLDOWN_S=120` confirmed (was 180).

## Data (60m pre-intervention)
| Metric | dsv4p_nv | glm5_2_nv | kimi_nv |
|--------|---------|-----------|---------|
| 12h SR | 8.0% | 36.5% | 68.4% |
| Total | 25 | 63 | 79 |
| Success | 2 | 23 | 54 |
| ATE | 23 | 40 | 25 |
| Instant ATE (<1s) | 12 | 24 | 0 |

- `glm5_2_nv`: 3 slow ATEs (15-30s, 50-60s) vs 24 instant ATEs → **breaker is the dominant cause of failure**.
- Rationale for no other changes:
  - dsv4p_nv: sparse, hard to assess (upstream exhaustion, not config)
  - kimi_nv: zombie + budget ceiling at 230s → already addressed in R2363 (250s)

## Iron Law
- Only changed HM1 docker-compose.
- HM2 local not modified.

## ⏳ 轮到HM1优化HM2
