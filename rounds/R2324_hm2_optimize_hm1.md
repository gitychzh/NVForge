# R2324 (HM2→HM1): TIER_COOLDOWN_S 15→10, eliminate 5s dead zone

**Timestamp**: 2026-07-24 18:33 UTC
**Round type**: Config optimization (single param)
**Author**: opc2_uname (HM2)

## 1. 触发分析

cron 脚本检测到 HM1 有新 commit (cf19691 R2323), 判定轮到 HM2 执行优化。

## 2. 数据采集 (HM1: 100.109.153.83)

### 2.1 Container state

- nv_gw: Up healthy, started 10:13 UTC (R2323 deploy)
- Health: 200 ✅
- All containers: healthy

### 2.2 Docker logs (nv_gw --tail 100)

Clean restart, no errors in recent logs:
```
[NV-GLM52-IDX] restored from /app/logs/glm52_mode_idx.json: idx=0
[NV-RR] restored from /app/logs/rr_counter.json: {'nv_dsv4p': 2761, 'nv_kimi': 145, 'nv_glm5_2': 1538, ...}
[NV-PROXY] Starting NV-unified proxy on 0.0.0.0:40006
[NV-PROXY] PROXY_ROLE=passthrough NVU_NUM_KEYS=5 tiers=['kimi_nv', 'dsv4p_nv', 'glm5_2_nv'] default=dsv4p_nv
[NV-PROXY] Listening on 0.0.0.0:40006 (role=passthrough, default_tier=dsv4p_nv, fallback_chain=['kimi_nv', 'dsv4p_nv', 'glm5_2_nv'])
```

### 2.3 DB nv_requests (6h window)

| Metric | Value |
|--------|-------|
| Total requests | 44 |
| OK (200) | 9 |
| Fail (non-200) | 35 |
| Success rate | 20.5% |
| avg OK latency | 9003ms |

### 2.4 30min window (last)

| Metric | Value |
|--------|-------|
| Total | 6 |
| OK | 0 |
| Fail | 6 |
| SR | 0.0% |

### 2.5 Recent 10 requests (all failures)

| created_at | model | status | duration_ms | error_type | key_cycle_429s | tiers_tried_count |
|------------|-------|--------|-------------|------------|----------------|-------------------|
| 10:06:02 | dsv4p_nv | 502 | 7 | all_tiers_exhausted | 0 | 1 |
| 10:06:01 | dsv4p_nv | 502 | 7 | all_tiers_exhausted | 0 | 1 |
| 10:06:00 | dsv4p_nv | 502 | 5 | all_tiers_exhausted | 0 | 1 |
| 10:03:38 | glm5_2_nv | 502 | 7 | all_tiers_exhausted | 0 | 1 |
| 10:03:37 | glm5_2_nv | 502 | 8 | all_tiers_exhausted | 0 | 1 |
| 10:03:32 | glm5_2_nv | 429 | 11369 | all_tiers_exhausted | 0 | 1 |
| 09:35:48 | dsv4p_nv | 502 | 6 | all_tiers_exhausted | 0 | 1 |
| 09:35:47 | dsv4p_nv | 502 | 8 | all_tiers_exhausted | 0 | 1 |
| 09:35:46 | dsv4p_nv | 502 | 8 | all_tiers_exhausted | 0 | 1 |
| 09:33:35 | glm5_2_nv | 502 | 8 | all_tiers_exhausted | 0 | 1 |

**Critical pattern**: ALL 10 recent failures have `tiers_tried_count=1` and `key_cycle_429s=0`. The gateway tries the default tier, finds keys in cooldown, immediately declares ATE — without cycling keys or trying fallback tiers.

### 2.6 Per-model breakdown (6h)

| Model | Total | OK | Fail | avg_ok_ms | real_ATE (502) |
|-------|-------|----|----|-----------|----------------|
| glm5_2_nv | 30 | 9 | 21 | 9003 | 14 |
| dsv4p_nv | 14 | 0 | 14 | — | 14 |

### 2.7 Error type breakdown (6h)

| Error type | Count |
|------------|-------|
| all_tiers_exhausted | 32 |
| zombie_empty_completion | 3 |

### 2.8 Tier attempts (6h)

| Tier | Error type | Count |
|------|-----------|-------|
| glm5_2_nv | 429_nv_rate_limit | 5 |
| glm5_2_nv | NVCFPexecRemoteDisconnected | 1 |

### 2.9 Hourly success rate (12h)

| Hour | Total | OK | SR |
|------|-------|----|----|
| 22:00 | 7 | 3 | 42.9% |
| 23:00 | 7 | 4 | 57.1% |
| 00:00 | 5 | 4 | 80.0% |
| 01:00 | 7 | 3 | 42.9% |
| 02:00 | 7 | 3 | 42.9% |
| 03:00 | 8 | 0 | 0.0% |
| 04:00 | 4 | 3 | 75.0% |
| 05:00 | 4 | 3 | 75.0% |
| 06:00 | 6 | 2 | 33.3% |
| 07:00 | 4 | 3 | 75.0% |
| 08:00 | 10 | 0 | 0.0% |
| 09:00 | 12 | 0 | 0.0% |
| 10:00 | 6 | 0 | 0.0% |

**3 consecutive hours (08-10 UTC) at 0% SR** — indicates persistent tier cooldown lockout.

### 2.10 Latency percentiles (6h, 200 status only)

| p50 | p90 | p95 | min | max |
|-----|-----|-----|-----|-----|
| 7832ms | 14042ms | 14075ms | 4548ms | 14109ms |

### 2.11 Zombie completions (6h)

| created_at | model | duration_ms | error_type |
|------------|-------|-------------|------------|
| 07:33:42 | glm5_2_nv | 14968 | zombie_empty_completion |
| 05:33:32 | glm5_2_nv | 5382 | zombie_empty_completion |
| 04:33:45 | glm5_2_nv | 10179 | zombie_empty_completion |

### 2.12 Current env (relevant params)

| Param | Value | Set by |
|-------|-------|--------|
| KEY_COOLDOWN_S | 10 | R2297 |
| TIER_COOLDOWN_S | 15 | R2305 |
| UPSTREAM_TIMEOUT | 24 | — |
| TIER_TIMEOUT_BUDGET_S | 415 | — |
| NVU_TIER_BUDGET_GLM5_2_NV | 210 | — |
| NVU_TIER_BUDGET_DSV4P_NV | 170 | — |
| NVU_TIER_BUDGET_KIMI_NV | 170 | — |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv,dsv4p_nv,kimi_nv | R2310+R2311+R2323 |
| NVU_BIG_INPUT_FAIL_N | 2 | R2322 |
| NVU_EMPTY_200_FASTBREAK | 3 | — |
| NVU_STREAM_TOTAL_DEADLINE_S | 35 | — |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 15 | — |

## 3. 分析与优化计划

### 3.1 Root cause: TIER_COOLDOWN_S > KEY_COOLDOWN_S creates dead zone

**Current**: `KEY_COOLDOWN_S=10` (R2297) + `TIER_COOLDOWN_S=15` (R2305).

When a 429 storm hits (5 keys fail in ~10s), each key enters 10s cooldown. At t=10s, keys start recovering. But `TIER_COOLDOWN_S=15` keeps the **entire tier** blocked until t=15s — a **5s dead zone** where keys are available but the tier is locked.

During this dead zone:
- Incoming requests find tier in cooldown → `TIER_SKIP` → try fallback tier → also in cooldown (same storm) → ATE
- `tiers_tried_count=1` confirms: the gateway only tried 1 tier before declaring ATE, because the default tier was blocked by TIER_COOLDOWN

### 3.2 Evidence

- All 10 recent ATEs have `tiers_tried_count=1`, `key_cycle_429s=0`
- Duration 5-8ms for 502s — instant rejection (tier cooldown fast-fail), not actual NVCF attempts
- 3 consecutive hours at 0% SR (08-10 UTC) — sustained lockout
- Only 1 real 429 in 30min (11369ms, a genuine NVCF rate-limit)

### 3.3 Change: TIER_COOLDOWN_S 15→10

Align `TIER_COOLDOWN_S` with `KEY_COOLDOWN_S=10`:
- Keys recover at t=10s, tier unlocks at t=10s — **no dead zone**
- 10s is still substantial: a 429 storm cycling 5 keys takes ~10s, so the tier cooldown still blocks re-hammering during the key-cycle window
- R2305's original concern (consecutive ATE re-hammering at 10-18s intervals) is addressed differently by R2322's BIG_INPUT_FAIL_N=2 breaker (instant rejection after 2 fails, 900s cooldown) — so the tier cooldown's circuit-breaker role is now secondary

### 3.4 Safety analysis

- **Normal requests** (no cooldown active): unaffected — TIER_COOLDOWN only activates after ATE
- **429 storm recovery**: keys recover and tier unlocks simultaneously at t=10s, allowing immediate retry instead of waiting to t=15s
- **Re-hammering risk**: mitigated by R2322's BIG_INPUT_FAIL_N=2 breaker (2 fails → 900s open) — this is the primary anti-re-hammer mechanism now
- **NVCF rate limiter**: 10s is still sufficient for NVCF to reset its per-IP rate limit (NVIDIA's 429 typically clears in ~5-10s)
- Single param change, minimal risk

## 4. 执行

```bash
# Line 512: TIER_COOLDOWN_S=15 → 10
sed -i 's/TIER_COOLDOWN_S=15  # R2305.*/TIER_COOLDOWN_S=10  # R2324 (HM2->HM1): 15->10 align with KEY_COOLDOWN_S=10, eliminate 5s dead zone where keys recovered but tier still blocked. 6h data: all ATE have tiers_tried_count=1, keys in cooldown. 10s still blocks tier during KEY_COOLDOWN window. Single param; iron law: only HM1/' /opt/cc-infra/docker-compose.yml
# Validate YAML
docker compose config --quiet  # → EXIT 0
# Restart container
docker compose up -d --no-deps --force-recreate nv_gw
```

## 5. 验证

- `docker compose config --quiet` → EXIT 0 (YAML valid) ✅
- `docker exec nv_gw env | grep TIER_COOLDOWN_S` → `TIER_COOLDOWN_S=10` ✅
- `curl localhost:40006/health` → 200 ✅
- Container recreated, status Up healthy, started 10:33 UTC ✅

## 6. 预期效果

- **Dead zone eliminated**: 5s window (t=10s to t=15s) where keys are available but tier is blocked → gone. Incoming requests can immediately use recovered keys.
- **429 storm recovery**: After 5 keys fail in ~10s, tier unlocks at t=10s (was t=15s) → 33% faster recovery
- **ATE with tiers_tried_count=1**: Requests will find the tier unlocked sooner, try real NVCF requests instead of instant 502
- **3h 0% SR lockout**: Should break the sustained lockout pattern — each 429 storm recovers in 10s instead of 15s
- **Normal requests**: Unaffected — TIER_COOLDOWN only activates after ATE
- **Re-hammering**: Protected by R2322 BIG_INPUT_FAIL_N=2 breaker (900s cooldown after 2 fails) — this is the primary circuit breaker now
- **KEY_COOLDOWN_S=10**: Unchanged (R2297), still prevents immediate key re-use after 429

## ⏳ 轮到HM1优化HM2
