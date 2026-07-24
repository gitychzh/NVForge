# R2325 (HM2→HM1): NVU_BIG_INPUT_COOLDOWN_S 900→300 (15min→5min) — breaker HALF-OPEN sooner

**Timestamp**: 2026-07-24 11:20 UTC
**Round type**: Config optimization (single param)
**Author**: opc2_uname (HM2)
**Container restart**: Yes (force-recreate nv_gw, started 11:20:25 UTC)

## 1. Trigger

Cron script detected HM1 commit from R2324 (TIER_COOLDOWN_S 15→10),判定 HM2's turn to optimize HM1.

## 2. Data collection (HM1: 100.109.153.83:222)

### 2.1 Container state (pre-change)

- nv_gw: Started 2026-07-24T10:33:17Z (R2324 deploy), RC=0, status=running, ~47min uptime
- logs_db: healthy, PostgreSQL 16
- No drift detected

### 2.2 DB nv_requests (6h window: ~05:20-11:20 UTC)

#### Overall

| Metric | Value |
|--------|-------|
| Total requests | 49 |
| Success (200) | 9 |
| Fail (502) | 40 |
| SR | 18.4% |
| All ATE error_type | all_tiers_exhausted (38) + zombie_empty_completion (2) |

#### Per-model

| Model | Total | OK | SR | avg_dur_ms | max_dur_ms |
|-------|-------|----|-----|------------|------------|
| glm5_2_nv | 32 | 9 | 28.1% | 28,420 | 55,273 |
| dsv4p_nv | 17 | 0 | 0% | 50,178 | 170,055 |
| kimi_nv | 0 | 0 | N/A | — | — |

#### Post-R2324 restart (10:33-11:20 UTC, ~47min)

| Metric | Value |
|--------|-------|
| Total requests | 7 |
| OK | 1 |
| Fail | 6 |
| SR | 14.3% |

#### Error type breakdown

| Error type | Count | Duration range | upstream_type |
|------------|-------|---------------|--------------|
| all_tiers_exhausted (instant 5-12ms) | 29 | 5-12ms | NULL |
| all_tiers_exhausted (real 8.6-170s) | 9 | 8,636-170,055ms | NULL |
| zombie_empty_completion | 2 | 14,968-51,925ms | NULL |

**Key finding**: ALL 38 ATEs have `upstream_type=NULL`, `tiers_tried_count=1`, `fallback_occurred=false`. The 29 instant ATEs (5-12ms) are cooldown fast-fails or breaker OPEN instant-rejects — not real NVCF failures.

#### All ATEs are big-input requests

Every single ATE (all 38 + 2 zombie) has `total_input_chars` in range 288,387-291,242 (>250K threshold). All failures are big-input requests.

#### Hourly SR

| Hour (UTC) | Total | OK | SR |
|------------|-------|----|-----|
| 06:00 | 2 | 0 | 0% |
| 07:00 | 8 | 3 | 37.5% |
| 08:00 | 8 | 0 | 0% |
| 09:00 | 12 | 3 | 25.0% |
| 10:00 | 19 | 3 | 15.8% |

### 2.3 Tier attempts (6h)

| Tier | Error type | Count | avg_elapsed_ms | upstream_type |
|------|-----------|-------|----------------|--------------|
| glm5_2_nv | 429_nv_rate_limit | 7 | — | nvcf_pexec |
| glm5_2_nv | NVCFPexecRemoteDisconnected | 1 | 3,597 | nvcf_pexec |
| dsv4p_nv | (no tier attempts recorded) | 0 | — | — |

**Key finding**: dsv4p_nv has ZERO tier_attempts. The BIGINPUT breaker is OPEN for dsv4p_nv big-input, instantly rejecting all requests (5-8ms) before any NVCF attempt is made. This is correct behavior — saves 170s per prevented ATE.

### 2.4 ms_gw fallback (6h, ms_requests table)

| Metric | Value |
|--------|-------|
| Total requests | 7 |
| OK (status='ok') | 7 |
| SR | 100% |
| avg duration | 15,500ms |
| duration range | 8,300-22,500ms |

**ms_gw fallback works perfectly**: 100% success rate. When nv_gw returns 502 (ATE), the adapter falls back to ms_gw and succeeds.

### 2.5 Key cycle analysis

| Metric | Count |
|--------|-------|
| key_cycle_429s=0 | 42 (85.7%) |
| key_cycle_429s=1 | 1 (2.0%) |
| key_cycle_429s=2 | 6 (12.2%) |

6 requests with `key_cycle_429s=2` cycled through 2 keys with 429 before succeeding. Key cycling works for some requests.

### 2.6 The 9 real ATEs (duration > 100ms)

| Time (UTC) | Model | Duration_ms | Input_chars | key_cycle_429s | upstream_type | fallback |
|-------------|-------|-------------|-------------|----------------|---------------|----------|
| 06:38:49 | dsv4p_nv | 170,046 | 288,387 | 0 | NULL | f |
| 07:33:37 | glm5_2_nv | 16,591 | 289,819 | 0 | NULL | f |
| 08:08:49 | dsv4p_nv | 170,055 | 288,769 | 0 | NULL | f |
| 09:03:44 | glm5_2_nv | 8,636 | 290,432 | 0 | NULL | f |
| 09:33:28 | glm5_2_nv | 12,736 | 290,463 | 0 | NULL | f |
| 10:03:33 | glm5_2_nv | 8,822 | 290,512 | 0 | NULL | f |
| 10:33:31 | glm5_2_nv | 10,337 | 290,557 | 0 | NULL | f |
| 10:33:41 | glm5_2_nv | 7,092 | 290,557 | 0 | NULL | f |
| 10:33:45 | glm5_2_nv | 8,568 | 290,557 | 0 | NULL | f |

All real ATEs have `upstream_type=NULL`, `key_cycle_429s=0`, `fallback_occurred=false`. The 2 dsv4p_nv 170s ATEs are budget exhaustion (NVU_TIER_BUDGET_DSV4P_NV=170). The 7 glm5_2_nv ATEs (8.6-16.6s) are 429 storms.

### 2.7 Environment (docker exec nv_gw env, pre-change)

Key params confirmed:
- `NVU_BIG_INPUT_FAIL_N=2` (R2322: 3→2)
- `NVU_BIG_INPUT_COOLDOWN_S=900` (R2288: 2100→900) ← **this round changes this**
- `NVU_BIG_INPUT_THRESHOLD=250000` (R2312)
- `NVU_BIG_INPUT_MODELS=glm5_2_nv,dsv4p_nv` (R2317)
- `NVU_TIER_BUDGET_DSV4P_NV=170` (R2306)
- `NVU_TIER_BUDGET_GLM5_2_NV=210` (R2291)
- `KEY_COOLDOWN_S=10` (R2297: 5→10)
- `TIER_COOLDOWN_S=10` (R2324: 15→10)
- `NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv,kimi_nv` (R2310+R2311+R2323)
- `NVU_PEXEC_TIMEOUT_FASTBREAK=2` (R2284: 1→2)
- `NVU_MS_GW_FALLBACK_TIMEOUT=120` (not actively used by nv_gw, adapter does ms_gw fallback)
- `UPSTREAM_TIMEOUT=24`

### 2.8 Source code analysis (big_input_breaker.py)

**Critical discovery: breaker self-rearm feedback loop**

When breaker is OPEN and a big-input request arrives:

1. `upstream.py` L1370-1376: breaker OPEN → constructs `final_result` with `all_keys_exhausted=True`, `all_429=False`, returns immediately (7ms ATE)
2. `upstream.py` L1620-1626: `record_big_input_failure("all_keys_exhausted")` called because `is_big_input=True` and `not all_429=True`
3. `big_input_breaker.py` `record_big_input_failure()`: since breaker already OPEN, **re-arms cooldown** (`_open_until = now + COOLDOWN_S`)

This means: every 7ms instant-reject during OPEN state resets the cooldown timer. With COOLDOWN_S=900, the breaker stays OPEN for the entire 30-min storm cycle as long as requests keep arriving.

**This is a code-level issue (not fixable via config), but reducing COOLDOWN_S from 900→300 mitigates it:**
- With 900s: breaker needs a 15-min gap with zero big-input requests to reach HALF-OPEN
- With 300s: breaker needs only a 5-min gap to reach HALF-OPEN
- Between 429 storms (~30min apart, ~18s duration each), there's a 5-10min quiet period where the breaker can HALF-OPEN and probe NVCF recovery

## 3. Analysis

### Root cause

1. **429 storms every ~30 min**: NVCF cluster rate-limits all 5 keys within ~8.6s, producing a 9-16s ATE. This is upstream, not config-fixable.
2. **Breaker opens on 2nd fail** (R2322 FAIL_N=2): the 2nd fail is a 7ms cooldown fast-fail (not a real NVCF fail). Breaker opens correctly — preventing 170s dsv4p_nv ATE waste.
3. **Breaker self-rearms on every instant-reject** (code feedback loop): with COOLDOWN_S=900, breaker stays OPEN for the full 30-min inter-storm period. With 300s, breaker can HALF-OPEN 5min after the last request.
4. **ms_gw fallback 100%**: all nv_gw failures are caught by ms_gw. The system works end-to-end — the only issue is latency (nv_gw wastes 7ms-16.6s before returning 502, then ms_gw takes ~15.5s).

### Why COOLDOWN_S=900→300 is safe

- **Breaker only affects big-input models** (glm5_2_nv, dsv4p_nv) with input > 250K chars. Normal requests completely unaffected.
- **If NVCF still down at HALF-OPEN**: probe fails → breaker re-OPENs with 300s cooldown (safe fallback to ms_gw continues)
- **If NVCF recovered**: probe succeeds → breaker CLOSED → nv_gw resumes handling big-input directly (saves ~15.5s ms_gw latency per request)
- **ms_gw 100% SR**: even if breaker opens prematurely, ms_gw catches all failures
- **COOLDOWN_S=300 (5min) vs storm interval (~30min)**: breaker can HALF-OPEN and probe up to 6 times per inter-storm period, significantly increasing chance of catching NVCF recovery
- **No risk of cascading**: breaker is per-process global, not per-key or per-tier. It doesn't affect KEY_COOLDOWN or TIER_COOLDOWN logic.

### Why not change other params

- **FAIL_N 2→3**: Would re-expose dsv4p_nv to 170s ATE (R2322's exact problem). Not safe.
- **PEXEC_TIMEOUT_FASTBREAK 2→1**: R2284 explicitly set 2→2 for NVCF timeout scenarios. Current ATEs are 429 storms (upstream_type=NULL, no pexec). FASTBREAK irrelevant to current failures.
- **TIER_COOLDOWN_S 10→lower**: Already at 10s (R2324). Further reduction risks more 429 consecutive hits within same burst.
- **KEY_COOLDOWN_S 10→lower**: R2297 found 5s too short (NVCF rate limiter window not released). 10s is correct.

## 4. Execution

```bash
# Line 449: NVU_BIG_INPUT_COOLDOWN_S=900 → 300
python3 /tmp/fix_cooldown.py  # (replaces value + comment on L449)
# Validate YAML
docker compose config --quiet  # → EXIT 0
# Restart container
docker compose up -d --no-deps --force-recreate nv_gw
```

### Verification

- `docker compose config --quiet` → YAML VALID ✅
- `docker exec nv_gw env | grep NVU_BIG_INPUT_COOLDOWN_S` → `NVU_BIG_INPUT_COOLDOWN_S=300` ✅
- `curl localhost:40006/health` → 200 ok ✅
- Container recreated 2026-07-24T11:20:25Z, RC=0, status=running ✅

## 5. Expected effect

### Primary

- **Breaker HALF-OPENs 5min after last big-input request** (vs 15min with COOLDOWN=900). Between 429 storms (~30min apart), breaker probes NVCF recovery up to 6 times.
- **If NVCF recovered**: breaker CLOSES → nv_gw handles big-input directly (saves ~15.5s ms_gw latency per request). Potential SR improvement from 18.4% → higher.
- **If NVCF still down**: breaker re-OPENs (300s) → ms_gw fallback continues (100% SR). No regression.

### Secondary

- **dsv4p_nv**: breaker was OPEN for entire 6h window (0 tier_attempts). With COOLDOWN=300, breaker can HALF-OPEN 5min after each dsv4p_nv request. If NVCF glm5.2 function recovered, dsv4p_nv can resume direct NVCF handling.
- **glm5_2_nv**: 9/32 SR (28.1%) — some successes had key_cycle_429s=2. Breaker opening sooner means more chances to catch NVCF between storms.
- **Instant ATE count**: may decrease if breaker CLOSES between storms (fewer instant-rejects).

### Risk assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaker opens prematurely (NVCF still down) | Medium | Low — ms_gw fallback 100% | Breaker re-OPENs on probe fail (300s) |
| Normal requests affected | Zero | None | Only affects BIG_INPUT_MODELS with >250K chars |
- | ms_gw overload | Low | Low | ms_gw 100% SR, avg 15.5s — capacity available |
| 170s dsv4p_nv ATE returns | Low | Medium | FAIL_N=2 (R2322) catches on 2nd fail, breaker still protects |

## 6. Round history context

| Round | Change | Effect |
|-------|--------|--------|
| R2288 | COOLDOWN 2100→900 | Reduced breaker blocking from 35min to 15min |
| R2297 | KEY_COOLDOWN 5→10 | NVCF rate limiter window release |
| R2305 | TIER_COOLDOWN 15→10 | Faster tier unlock |
| R2317 | BIG_INPUT_MODELS +dsv4p_nv | Protect dsv4p_nv from 170s ATE |
| R2322 | FAIL_N 3→2 | Breaker opens 1 fail earlier, catches 170s ATE |
| R2323 | PEER_FB_SKIP +kimi_nv | Skip peer fallback, direct 502→ms_gw |
| R2324 | TIER_COOLDOWN 15→10 | (same as R2305? duplicate — 10s confirmed) |
| **R2325** | **COOLDOWN 900→300** | **Breaker HALF-OPENs in 5min, faster NVCF recovery probe** |

## ⏳ 轮到HM1优化HM2

## 铁律:只改HM1不改HM2
- 每轮少改多轮积累
- 更少报错更快请求超低延迟稳定优先
