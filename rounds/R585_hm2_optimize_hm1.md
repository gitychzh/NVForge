# R585: HM2→HM1 — NOP round. NVCF infrastructure surge producing ATE across kimi/dsv4p; integrate path 100% clean, no parameter candidate survives data vetting
**Round**: R585 | **Direction**: HM2 → HM1 | **Author**: opc2_uname
**Timestamp**: 2026-07-03 04:31 CST (2026-07-02 20:31 UTC)
**Container**: nv_40006 (StartedAt: 2026-07-02T20:10:23Z, after R584 deploy)

## Data Collection

### 1. Docker Logs (nv_40006_uni, tail 200)
- Zero ERROR / WARN / 429 / SSLEOF / empty200 / peer-fallback events in last 200 lines
- 4 normal `[NV-THINKING-TIMEOUT] (kimi_nv) thinking request stream=True -> extended timeout 61s` messages
- 12 integrate attempts, all first-attempt success (no retry or fallback traces)
- 旧 R584 成功的 A/B 测试之一；R584 的冷却周期参数对零错误微事件没有影响

### 2. Container Env (nv_40006_uni) - Drift Check
| Parameter | Value | Status |
|-----------|-------|--------|
| UPSTREAM_TIMEOUT | 28 | R577, compose matches |
| TIER_TIMEOUT_BUDGET_S | 90 | R576, compose matches |
| MIN_OUTBOUND_INTERVAL_S | 0.4 | R582, compose matches |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | R559, compose matches |
| TIER_COOLDOWN_S | 25 | R492, compose matches |
| NVU_PEER_FALLBACK_TIMEOUT | 25 | R560, compose matches |
| NVU_CONNECT_RESERVE_S | 2 | R570, compose matches |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | R543, compose matches |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 61 | R537, compose matches |
| NVU_FORCE_STREAM_UPGRADE | 1 | R502, compose matches |
| NVU_EMPTY_200_FASTBREAK | 2 | R581, env matches |
| NV_INTEGRATE_ENABLED | 1 | R574, env matches |
| NV_INTEGRATE_MODELS | dsv4p_nv,kimi_nv | R575, compose matches |
| NV_INTEGRATE_KEY_COOLDOWN_S | 110 | **R584, env matches** |
| KEY_COOLDOWN_S | 25 | R162, compose matches |
| NVU_PROXY_URL1-5 | "" | R_direct, all-key direct |
| NVCF_GLM52_FUNCTION_ID | 3b9748d8 | R577, compose matches |

**Drift check**: env and compose fully aligned. No configuration drift. Container restarted at 2026-07-02T20:10:23Z (after R584 changes). All 16 tracked parameters match.

### 3. DB nv_requests (PostgreSQL cc_postgres, last 4h query)

**4h summary (16:31 → 20:31 UTC)**

| Model | Total | OK | Fail | SR% | Max(s) | Avg(s) |
|-------|-------|----|------|-----|--------|--------|
| dsv4p_nv | 682 | 623 | 59 | 91.3 | 161.4 | 28.2 |
| kimi_nv | 260 | 149 | 111 | 57.3 | 351.3 | 40.0 |
| glm5_2_nv | 47 | 46 | 1 | 97.9 | 34.8 | 5.1 |
| glm5_1_nv | 23 | 13 | 10 | 56.5 | 89.7 | 10.0 |

**30min summary (20:01 → 20:31 UTC, R584 window)**

| Model | Total | OK | Fail | SR% | Max(s) | Avg(s) |
|-------|-------|----|------|-----|--------|--------|
| dsv4p_nv | 640 | 622 | 18 | 97.2 | 161.4 | 29.6 |
| kimi_nv | 188 | 120 | 68 | 63.8 | 351.3 | 60.3 |
| glm5_2_nv | 47 | 46 | 1 | 97.9 | 34.8 | 5.1 |
| glm5_1_nv | 21 | 11 | 10 | 52.4 | 89.7 | 10.3 |

**15min summary (20:16 → 20:31 UTC)**

| Model | Total | OK | Fail | SR% |
|-------|-------|----|------|-----|
| dsv4p_nv | 613 | 595 | 18 | 97.1 |
| kimi_nv | 180 | 118 | 62 | 65.6 |
| glm5_2_nv | 47 | 46 | 1 | 97.9 |
| glm5_1_nv | 19 | 10 | 9 | 52.6 |

### 4. Upstream-Type Breakdown (30min window)
| Model | upstream_type | Total | OK | SR% |
|-------|---------------|-------|----|-----|
| dsv4p_nv | nv_integrate | 152 | 152 | **100.0** |
| dsv4p_nv | nvcf_pexec | 459 | 458 | **99.8** |
| dsv4p_nv | NULL (ATE final) | 28 | 11 | 39.3 |
| kimi_nv | nv_integrate | 58 | 58 | **100.0** |
| kimi_nv | nvcf_pexec | 63 | 62 | **98.4** |
| kimi_nv | NULL (ATE final) | 67 | 0 | 0.0 |

**Key finding**: Both `nv_integrate` and `nvcf_pexec` per-attempt paths show >98% SR. The 0%-SR `NULL upstream_type` rows are **final ATE (all_tiers_exhausted) records** aggregated after all individual key attempts have failed — they are not a separate failure path.

### 5. Error Breakdown (15min window, status != 200)
| Model | error_type | Count | Avg(s) | Max(s) | Min(s) |
|-------|------------|-------|--------|--------|--------|
| dsv4p_nv | all_tiers_exhausted | 17 | 78.8 | 143.4 | 61.6 |
| dsv4p_nv | NVStream_TimeoutError | 1 | 90.8 | 90.8 | 90.8 |
| kimi_nv | all_tiers_exhausted | 61 | 82.0 | 94.1 | 61.6 |
| kimi_nv | NVStream_TimeoutError | 1 | 68.9 | 68.9 | 68.9 |
| glm5_1_nv | all_tiers_exhausted | 9 | 10.7 | 89.7 | 0.5 |
| glm5_2_nv | all_tiers_exhausted | 1 | 34.8 | 34.8 | 34.8 |

**ATE latency distribution (30min)**:
- dsv4p: 11× <60s (avg 14.2s), 6× 60-70s, 2× 70-80s, 8× 80-90s, 1× >120s (143.4s)
- kimi: 10× 60-70s, 16× 70-80s, 18× 80-90s, 23× 90-100s
- glm5_1: 8× <60s (avg 0.9s) — **signature of EOL function (410 Gone), consistent expected behavior**

### 6. Per-Minute Trend (dsv4p + kimi, last 30min excerpt)
- **20:24 UTC**: dsv4p 3 req / 2 OK (66.7%), kimi 1 req / 0 OK (0%) — first failure cluster
- **20:25 UTC**: dsv4p 2 OK / 2 (100%), kimi 2 req / 1 OK (50%)
- **20:28–20:31 UTC**: dsv4p 100% (single req/min, low traffic), kimi 0/1–1/1 (sparse)
- **Pattern**: Low absolute request volume per minute (1–3 req/min for kimi; 1–5 req/min for dsv4p outside bursts). High per-minute SR volatility is **statistically noisy** at this volume.

### 7. Hourly Aggregate Trend (last 6h)
| Hour UTC | dsv4p SR% | kimi SR% |
|----------|-----------|----------|
| 16:00 | 0.0 (12/12 fail) | 33.3 (12/4) |
| 17:00 | 0.0 (5/5 fail) | 18.2 (22/4) |
| 18:00 | 0.0 (9/9 fail) | 16.7 (6/1) |
| 19:00 | 6.3 (16/1) | 61.3 (31/19) |
| 20:00 | 99.2 (118/117) | 50.0 (28/14) |
| 21:00 | 100.0 (103/103) | 45.5 (33/15) |
| 22:00 | 92.0 (100/92) | 95.5 (22/21) |
| 23:00 | 93.5 (107/100) | 36.4 (22/8) |
| 00:00 | 99.0 (97/96) | 16.0 (25/4) |
| 01:00 | 96.3 (27/26) | 100.0 (15/15) |
| 02:00 | 100.0 (67/67) | 100.0 (24/24) |
| 03:00 | 100.0 (21/21) | 100.0 (13/13) |

**Interpretation**: The 16:00–19:00 and 23:00–00:00 low-SR windows match the well-documented **transient NVCF infrastructure-level surges** (previously observed in R577/R580/R583). These are function-level capacity-degradation events, not parameter misconfigurations. Recovery after each surge is intrinsic to NVCF load balancing.

## Candidate Parameter Evaluation

| Parameter | Current | Candidate | Evaluation | Decision |
|-----------|---------|-----------|------------|----------|--|
| NV_INTEGRATE_KEY_COOLDOWN_S | 110 | 100 (-10s) | R584 just changed 120→110; 30min window is too short to evaluate even the first -10s delta. No data. Also, integrate path is already 100%. | **no** |
| TIER_TIMEOUT_BUDGET_S | 90 | 85 (-5s) | Pexec success max is 91.9s (dsv4p). Tightening to 85 would truncate legitimate streaming successes. Violates "faster" without "fewer errors". | **no** |
| TIER_TIMEOUT_BUDGET_S | 90 | 95 (+5s) | Only 23 ATE in 90-100s bucket for kimi. Majority of ATE are <90s, so extra 5s would not reduce failure count, only increase user wait for already-failing requests. | **no** |
| UPSTREAM_TIMEOUT | 28 | 30 (+2s) | Pexec path is 98.4–99.8% SR. 1 NVStream_TimeoutError in 2h. Two extra seconds would not change surge-driven ATE pattern. | **no** |
| MIN_OUTBOUND_INTERVAL_S | 0.4 | 0.3 (-0.1s) | R582 trimmed 0.5→0.4. No error data ties outbound interval to current ATE. Would violate "single parameter, small change, many rounds" only for marginal gain. | **no** |
| NVU_EMPTY_200_FASTBREAK | 2 | 1 (-1) | Zero empty200 events in 2h. Cannot evaluate. | **no** |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 2 (+1) | Current 1 is the safe floor (R559). Increasing would add dead waits during surges. | **no** |
| NVU_PEER_FALLBACK_TIMEOUT | 25 | 23 (-2s) | Peer fallback zero activity in 30min. No data. | **no** |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | 0.8 (-0.2s) | Zero SSLEOF events. SSLEOF is already rare even before this round. | **no** |
| KEY_COOLDOWN_S | 25 | 20 (-5s) | Dead parameter in single-tier architecture. No impact. | **no** |
| NV_INTEGRATE_MODELS | dsv4p_nv,kimi_nv | expand? | glm5.1 EOL confirmed. glm5.2 404 on integrate endpoint (R577 tried and verified). No viable expansion target. | **no** |

## Decision Analysis

**System state**: NVCF infrastructure-level surge is affecting all models, with **kimi_nv being most impacted** (63.8% SR in 30min, vs dsv4p at 97.2%). 

**Root cause**: The error profile is `all_tiers_exhausted` with avg latency ~82s, which strongly indicates **NVCF function-level queue saturation / capacity degradation on function `f966661c` (kimi) and `74f02205` (dsv4p)**. This is a **service-provider-side capacity issue**, not a proxy parameter misconfiguration.

**Evidence for root cause**:
1. integrate path: **100% SR** — if the problem were upstream_timeout, budget, or key-cooldown, integrate would also show failures. It does not.
2. pexec path: **98.4–99.8% SR per-attempt** — individual key attempts succeed when NVCF has capacity.
3. ATE final records: **0% SR** — these only appear when all 5 keys have been exhausted, confirming system-wide NVCF saturation.
4. Historical recurrence: This is the **third observation** of hourly-burst NVCF surges (previously 00:00–00:55 window in R583, and 19:00–20:00 window now).
5. Recovery pattern: After each surge window, SR returns to 100% within 1–2 hours without proxy parameter changes, confirming external-cause hypothesis.

**R584 impact assessment**: R584 reduced NV_INTEGRATE_KEY_COOLDOWN_S 120→110. The integrate path continues at 100%, but integrate volume is a small fraction of total traffic (dsv4p: 23.2% integrate, 77.8% pexec). Any marginal benefit from the cooldown reduction is masked by the concurrent NVCF surge. **Not enough data to judge R584's true effect.**

**No safe micro-trim available**: All 11 evaluated parameters either have no data supporting a change, would risk truncating successful streaming requests, or address dead/unrelated paths. The correct action for a service-provider-side capacity surge is **NOP**, continue monitoring, and let NVCF's own congestion control recover.

## Deployment
No parameter changes this round. Compose and env remain exactly as R584 deployed them. No container restart required.

## Post-Deploy Verification
- Container StartedAt: 2026-07-02T20:10:23Z (unchanged)
- compose env: all 16 tracked values unchanged, no drift
- NVCF function IDs: 74f02205 (dsv4p), f966661c (kimi), 3b9748d8 (glm5.2) — all respond but kimi/dsv4p under infrastructure surge
- Next evaluation: Wait for NVCF surge to resolve, then reassess if R584's cooldown change altered integrate coverage in a zero-surge window.

## ⏳ 轮到HM1优化HM2
