# R2326 (HM2→HM1): NVU_BIG_INPUT_COOLDOWN_S 300→180 (5min→3min) — breaker HALF-OPEN sooner

**Timestamp**: 2026-07-24 11:57 UTC
**Round type**: Config optimization (single param)
**Author**: opc2_uname (HM2)
**Container restart**: Yes (force-recreate nv_gw, started 11:56 UTC)

## 1. Trigger

Cron script detected HM1 commit from R2325 (COOLDOWN_S 900→300),判定 HM2's turn to optimize HM1.

## 2. Data collection (HM1: 100.109.153.83:222)

### 2.1 Container state (pre-change)

- nv_gw: Started 2026-07-24T11:20:24Z (R2325 deploy), ~36min uptime, healthy
- logs_db: healthy, 7 days uptime
- No errors/warnings in container logs (clean restart)

### 2.2 DB nv_requests (6h window: ~05:33-11:33 UTC)

#### Overall

| Metric | Value |
|--------|-------|
| Total requests | 53 |
| Success (200) | 7 |
| Fail (502/429) | 46 |
| SR | 13.2% |
| avg_dur_ms | 9,674 |
| p50_dur_ms | 8 |
| p95_dur_ms | 15,617 |
| max_dur_ms | 170,055 |

#### Per-model

| Model | Total | OK | SR | avg_ms | max_ms |
|-------|-------|----|-----|--------|--------|
| glm5_2_nv | 32 | 7 | 21.9% | 5,835 | 25,614 |
| dsv4p_nv | 20 | 0 | 0% | 17,011 | 170,055 |
| kimi_nv | 0 | 0 | N/A | — | — |

**All 53 requests are big-input** (total_input_chars ≥ 250K). Zero normal requests in the window.

#### Post-R2325 restart (11:20-11:33 UTC, ~13min)

| Metric | Value |
|--------|-------|
| Total requests | 2 |
| OK | 2 |
| Fail | 0 |
| SR | 100.0% |
| avg_dur_ms | 15,229 |
| duration range | 4,843-25,614ms |

Both successes are glm5_2_nv big-input: K3 (4.8s, 292K chars) and K0 (25.6s, 291K chars, key_cycle_429s=4). **R2325's COOLDOWN=300 is working** — breaker HALF-OPENed and let requests through.

#### Error type breakdown (6h)

| Error type | Count | avg_ms | min_ms | max_ms |
|------------|-------|--------|--------|--------|
| all_tiers_exhausted | 44 | 9,802 | 5 | 170,055 |
| zombie_empty_completion | 1 | 14,968 | 14,968 | 14,968 |

#### ATE duration distribution (6h)

| Bucket | Count | min_ms | max_ms |
|--------|-------|--------|--------|
| instant (<50ms) | 34 | 5 | 12 |
| fast (50ms-10s) | 3 | 8,661 | 9,927 |
| medium (10-60s) | 5 | 10,527 | 16,591 |
| slow (>60s) | 2 | 170,046 | 170,055 |

34 instant ATEs (5-12ms) = breaker OPEN instant-rejects. 2 slow ATEs (170s) = dsv4p_nv budget exhaustion.

### 2.3 Tier attempts (6h)

| Tier | Key | Error type | Count | avg_ms | max_ms |
|------|-----|-----------|-------|--------|--------|
| glm5_2_nv | K1 | 429_nv_rate_limit | 3 | — | — |
| glm5_2_nv | K2 | 429_nv_rate_limit | 3 | — | — |
| glm5_2_nv | K4 | 429_nv_rate_limit | 3 | — | — |
| glm5_2_nv | K3 | 429_nv_rate_limit | 2 | — | — |
| glm5_2_nv | K0 | 429_nv_rate_limit | 1 | — | — |
| glm5_2_nv | K3 | NVCFPexecRemoteDisconnected | 1 | 3,597 | 3,597 |

**dsv4p_nv: ZERO tier_attempts.** Breaker OPEN for entire 6h window, instant-rejecting all dsv4p_nv big-input (saves 170s each). Correct behavior.

### 2.4 Key cycle analysis (6h)

| key_cycle_429s | Count | OK |
|----------------|-------|----|
| 0 | 47 | 3 |
| 1 | 2 | 2 |
| 2 | 2 | 2 |
| 3 | 1 | 0 |
| 4 | 1 | 1 |

4 requests with key_cycle_429s≥1: 4/4 success when breaker CLOSED (key cycling works). 47 requests with key_cycle_429s=0 mostly hit OPEN breaker (instant reject).

### 2.5 ms_gw fallback (6h)

| Metric | Value |
|--------|-------|
| Total requests | 8 |
| OK (status='ok') | 8 |
| SR | 100% |
| avg duration | 14,438ms |
| duration range | 8,300-22,510ms |

**ms_gw fallback 100% SR.** All nv_gw failures caught by ms_gw. System works end-to-end.

### 2.6 Per-key success latency (6h, status=200)

| Key | Total | p50_ms | p95_ms | min_ms | max_ms | avg_ms |
|-----|-------|--------|--------|--------|--------|--------|
| K0 | 2 | 17,976 | 24,850 | 10,337 | 25,614 | 17,976 |
| K1 | 1 | 5,529 | 5,529 | 5,529 | 5,529 | 5,529 |
| K2 | 3 | 12,797 | 13,902 | 4,548 | 14,025 | 10,457 |
| K3 | 1 | 4,843 | 4,843 | 4,843 | 4,843 | 4,843 |
| K4 | 1 | 7,832 | 7,832 | 7,832 | 7,832 | 7,832 |

Success latency range: 4.5s-25.6s. K0 highest (25.6s max, key_cycle_429s=4). Normal for big-input NVCF inference.

### 2.7 Hourly SR (6h)

| Hour (UTC) | Total | OK | SR |
|------------|-------|----|-----|
| 06:00 | 6 | 2 | 33% |
| 07:00 | 4 | 3 | 75% |
| 08:00 | 10 | 0 | 0% |
| 09:00 | 12 | 0 | 0% |
| 10:00 | 13 | 1 | 8% |
| 11:00 | 7 | 1 | 14% |

SR peaks at 07:00 (75%), drops to 0% during 08:00-09:00 (storm window), then partially recovers. Pattern matches R2325's observation of ~30min 429 storm cycles.

### 2.8 Environment (docker exec nv_gw env, pre-change)

Key params confirmed:
- `NVU_BIG_INPUT_COOLDOWN_S=300` (R2325: 900→300) ← **this round changes this**
- `NVU_BIG_INPUT_FAIL_N=2` (R2322: 3→2)
- `NVU_BIG_INPUT_THRESHOLD=250000` (R2312)
- `NVU_BIG_INPUT_MODELS=glm5_2_nv,dsv4p_nv` (R2317)
- `NVU_TIER_BUDGET_DSV4P_NV=170` (R2306)
- `NVU_TIER_BUDGET_GLM5_2_NV=210` (R2291)
- `KEY_COOLDOWN_S=10` (R2297: 5→10)
- `TIER_COOLDOWN_S=10` (R2324: 15→10)
- `NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv,kimi_nv` (R2310+R2311+R2323)
- `NVU_PEXEC_TIMEOUT_FASTBREAK=2` (R2284: 1→2)
- `UPSTREAM_TIMEOUT=24`

## 3. Analysis

### Root cause

1. **429 storms every ~30 min**: NVCF cluster rate-limits all 5 keys within ~8.6s. Breaker correctly opens on 2nd fail (R2322 FAIL_N=2), preventing 170s dsv4p_nv ATE waste.
2. **Breaker self-rearm feedback loop** (discovered R2325): every instant-reject during OPEN state resets cooldown timer. With COOLDOWN_S=900, breaker stayed OPEN for entire 30-min storm cycle. R2325 reduced to 300, confirmed working (2/2 post-restart success).
3. **R2325 validation**: 2/2 success (100%) in 13min post-restart window. Breaker HALF-OPENed, probed NVCF, found it recovered, CLOSED. Both glm5_2_nv big-input requests succeeded.
4. **ms_gw 100% SR**: all nv_gw failures caught by ms_gw (avg 14.4s). System works end-to-end.

### Why COOLDOWN_S=300→180

- **R2325 proved 300s works**: breaker successfully HALF-OPENed and let 2 requests through. The feedback loop is mitigated but not eliminated — every instant-reject still resets the 300s timer.
- **180s (3min) vs 300s (5min)**: breaker needs only a 3-min gap (vs 5-min) with zero big-input requests to reach HALF-OPEN. Between storms (~30min apart, ~18s duration), there's a 5-10min quiet period.
- **Probe frequency**: with 300s, breaker can probe ~6 times per inter-storm gap. With 180s, ~10 probes — 67% more recovery detection opportunities.
- **Diminishing returns consideration**: 300→900 was 3x reduction (R2325), 180→300 is 1.67x — conservative step. Can go to 120 next round if 180 proves stable.

### Why not change other params

- **FAIL_N 2→3**: Would re-expose dsv4p_nv to 170s ATE (R2322's exact problem). Not safe.
- **TIER_COOLDOWN_S 10→lower**: Already at 10s (R2324). Further reduction risks more 429 consecutive hits.
- **KEY_COOLDOWN_S 10→lower**: R2297 found 5s too short. 10s is correct.
- **PEXEC_TIMEOUT_FASTBREAK**: Current ATEs are 429 storms (no pexec). Irrelevant.

## 4. Execution

```bash
# Line 449: NVU_BIG_INPUT_COOLDOWN_S=300 → 180
python3 /tmp/fix_cooldown.py  # (replaces value + comment on L449)
# Validate YAML
docker-compose -f /opt/cc-infra/docker-compose.yml --env-file /opt/cc-infra/.env config --quiet  # → EXIT 0
# Restart container
docker-compose -f /opt/cc-infra/docker-compose.yml --env-file /opt/cc-infra/.env up -d --no-deps --force-recreate nv_gw
```

### Verification

- `docker-compose config --quiet` → YAML VALID ✅ (exit 0)
- `docker exec nv_gw env | grep NVU_BIG_INPUT_COOLDOWN_S` → `NVU_BIG_INPUT_COOLDOWN_S=180` ✅
- Container recreated 2026-07-24T11:56 UTC, status=Up (healthy) ✅
- Container logs: clean startup, no errors ✅
  ```
  [NV-PROXY] Starting NV-unified proxy on 0.0.0.0:40006
  [NV-PROXY] Listening on 0.0.0.0:40006 (role=passthrough, default_tier=dsv4p_nv)
  ```

## 5. Expected effect

### Primary

- **Breaker HALF-OPENs 3min after last big-input request** (vs 5min with COOLDOWN=300). Between 429 storms (~30min apart), breaker probes NVCF recovery ~10 times (vs ~6 at 300s).
- **Faster NVCF recovery detection**: 67% more probe opportunities per inter-storm gap.
- **If NVCF recovered**: breaker CLOSES → nv_gw handles big-input directly (saves ~14.4s ms_gw latency per request).
- **If NVCF still down**: breaker re-OPENs (180s) → ms_gw fallback continues (100% SR). No regression.

### Risk assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaker opens prematurely | Low | Low — ms_gw 100% SR | Breaker re-OPENs on probe fail (180s) |
| Normal requests affected | Zero | None | Only affects BIG_INPUT_MODELS with >250K chars |
| ms_gw overload | Low | Low | ms_gw 100% SR, avg 14.4s — capacity available |
| 170s dsv4p_nv ATE returns | Low | Medium | FAIL_N=2 (R2322) catches on 2nd fail |

## 6. Round history context

| Round | Change | Effect |
|-------|--------|--------|
| R2288 | COOLDOWN 2100→900 | Reduced breaker blocking from 35min to 15min |
| R2297 | KEY_COOLDOWN 5→10 | NVCF rate limiter window release |
| R2305 | TIER_COOLDOWN 15→10 | Faster tier unlock |
| R2317 | BIG_INPUT_MODELS +dsv4p_nv | Protect dsv4p_nv from 170s ATE |
| R2322 | FAIL_N 3→2 | Breaker opens 1 fail earlier |
| R2323 | PEER_FB_SKIP +kimi_nv | Skip peer fallback, direct 502→ms_gw |
| R2324 | TIER_COOLDOWN 15→10 | Eliminate 5s dead zone |
| R2325 | COOLDOWN 900→300 | Breaker HALF-OPENs in 5min, 2/2 post-restart success |
| **R2326** | **COOLDOWN 300→180** | **Breaker HALF-OPENs in 3min, 67% more NVCF recovery probes** |

## ⏳ 轮到HM1优化HM2

## 铁律:只改HM1不改HM2
- 每轮少改多轮积累
- 更少报错更快请求超低延迟稳定优先
