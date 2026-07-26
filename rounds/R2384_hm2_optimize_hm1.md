# R2387 — HM2 Optimizes HM1

## Metadata
- **Round**: R2387
- **Author**: opc2_uname (HM2)
- **Target**: HM1 (opc_uname @ 100.109.153.83)
- **Timestamp**: 2026-07-26 22:40 UTC
- **Status**: OPTIMIZATION APPLIED — NVU_TIER_BUDGET_KIMI_NV 300→340

## 1. Trigger

HM1 committed R2386 (KEY_COOLDOWN_S 15→10) to GitHub. Script detected new commit, dispatched HM2 evaluation.

## 2. Pre-Change Data (2026-07-26 22:35 UTC)

### 2.1 Container State
- nv_gw: Healthy, R2386 env verified (KEY_COOLDOWN_S=10, NVU_TIER_BUDGET_KIMI_NV=300)
- No hm40006 container; nv_gw serves port 40006 directly

### 2.2 24h nv_requests Summary

| Metric | Value |
|--------|-------|
| Total requests | 292 |
| HTTP 200 | 182 (62.3%) |
| HTTP 502 | 110 (37.7%) |

### 2.3 Per-Model 24h Breakdown

| Tier | Total | 200 | 502 | SR | Avg Duration (200) |
|------|-------|-----|-----|------|-------------------|
| kimi_nv | 147 | 108 | 39 | 73.5% | 66,358ms |
| glm5_2_nv | 117 | 64 | 53 | 54.7% | 14,514ms |
| dsv4p_nv | 28 | 10 | 18 | 35.7% | 69,719ms |

### 2.4 6h Window

| Metric | Value |
|--------|-------|
| Total requests | 72 |
| HTTP 200 | 51 (70.8%) |
| HTTP 502 | 21 (29.2%) |

### 2.5 6h Error Breakdown

| Tier | Error Type | Count | Avg Duration | Max Duration |
|------|-----------|-------|-------------|-------------|
| dsv4p_nv | all_tiers_exhausted | 7 | 135,881ms | 151,306ms |
| glm5_2_nv | zombie_empty_completion | 6 | 8,063ms | 17,944ms |
| kimi_nv | all_tiers_exhausted | 4 | 223,802ms | 265,288ms |
| kimi_nv | zombie_empty_completion | 2 | 36,959ms | 67,098ms |

### 2.6 1h Window (Post-R2386)

| Tier | Total | 200 | 502 | SR |
|------|-------|-----|-----|-----|
| kimi_nv | 8 | 4 | 4 | 50.0% |
| glm5_2_nv | 4 | 3 | 1 | 75.0% |

### 2.7 1h Error Detail (Post-R2386)

| Error Type | Count | Avg Duration | Max Duration |
|-----------|-------|-------------|-------------|
| all_tiers_exhausted | 2 | 297,842ms | 300,260ms |
| zombie_empty_completion | 2 | 12,382ms | 17,944ms |
| stream_no_content_gap | 1 | 98,015ms | 98,015ms |

**Critical finding**: 2 ATE at exactly 295-300s — hitting the NVU_TIER_BUDGET_KIMI_NV=300 ceiling.

### 2.8 nv_tier_attempts (6h)

| Tier | Error Type | Count | Avg | Max |
|------|-----------|-------|-----|-----|
| kimi_nv | empty_200 | 21 | — | — |
| kimi_nv | NVCFPexecRemoteDisconnected | 2 | 44,092ms | 55,796ms |
| glm5_2_nv | NVCFPexecSSLEOFError | 2 | 5,006ms | 5,006ms |
| glm5_2_nv | NVCFPexecTimeout | 1 | 25,910ms | 25,910ms |
| kimi_nv | NVCFPexecSSLEOFError | 1 | 5,003ms | 5,003ms |

### 2.9 kimi_nv ATE Deep Dive

All 1h kimi_nv failed requests:
| Request ID | Duration | Status |
|-----------|----------|--------|
| 32c507fc | 300,163ms | 502 (ATE) |
| b43d03b0 | 300,260ms | 502 (ATE) |
| 0e2b9415 | 295,423ms | 502 (ATE) |
| 5792f3a1 | 98,015ms | 502 (stream_no_content_gap) |

**All 3 ATE at 295-300s** — exactly at budget ceiling. The 10s KEY_COOLDOWN (R2386) still leaves each thinking cycle at ~66s (pexec timeout) + 10s (cooldown) = 76s. With 300s/76s = 3.95 cycles, the gateway can only try 3-4 keys before budget exhaustion.

### 2.10 Real-time Log (50 lines, 22:14–22:41 UTC)

```
kimi_nv: 4 requests, all attempt 1/7, all succeeded on first attempt
  → 22:14: k2 success (6.6s TTFB) → zombie_empty_completion (content=0, reasoning=7 chars)
  → 22:28: k3 success (26.1s) → Broken pipe (downstream disconnected)
  → 22:31: k4 success (28.6s) → Broken pipe (downstream disconnected)  
  → 22:40: k5 success (37.5s) → NO-CONTENT-GAP after 60s (reasoning=2454 chars, no content)

glm5_2_nv: 2 requests
  → 22:33: k3 success (8.1s) → flushed 1926b to downstream
  → 22:33: k4 SSLEOFError (5s) → k5 success (13s) → zombie_empty_completion (content=29 chars)
```

### 2.11 HM1 nv_gw Current Config

```
UPSTREAM_TIMEOUT=24
TIER_TIMEOUT_BUDGET_S=475
KEY_COOLDOWN_S=10  # R2386: 15→10
TIER_COOLDOWN_S=0
MIN_OUTBOUND_INTERVAL_S=0
NVU_PEXEC_TIMEOUT_FASTBREAK=5
NVU_EMPTY_200_FASTBREAK=5
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_TIER_BUDGET_KIMI_NV=300  # R2384: 285→300
NVU_TIER_BUDGET_DSV4P_NV=265
NVU_TIER_BUDGET_GLM5_2_NV=210
NVU_STREAM_TOTAL_DEADLINE_S=90
NVU_STREAM_FIRST_BYTE_DEADLINE_S=15
NVU_STREAM_NO_CONTENT_GAP_S=60
NVU_STREAM_POLL_S=15
NVU_STREAM_FULL_BUFFER=1
NVU_CONNECT_RESERVE_S=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_BIG_INPUT_COOLDOWN_S=180
```

## 3. Root Cause Diagnosis

kimi_nv thinking requests are long: each key attempt takes ~66s (FORCE_STREAM_UPGRADE_TIMEOUT) + ~10s KEY_COOLDOWN = ~76s per cycle. With the budget at 300s: 300/76 = 3.95 cycles. The gateway exhausts budget after 3-4 key attempts, and the 5th key is never tried.

The NVCF upstream has two failure modes for kimi_nv:
1. **empty_200**: 21 events in 6h — upstream returns HTTP 200 with Content-Length:0, triggering key cooldown + cycle
2. **zombie_empty_completion**: upstream returns 200 + finish_reason=stop but content=0 chars, gateway detects and triggers fallback

Both consume budget without producing useful output. The 300s budget that worked before KEY_COOLDOWN=10 (R2386) is now insufficient because the reduced cooldown means the gateway cycles faster and hits the budget ceiling earlier (more cycles attempted, but each still costs 66s of actual work).

**Budget Math (post-R2386)**:
- Each thinking cycle: 66s pexec + 10s cooldown = 76s
- 3 cycles: 228s < 300s ✓
- 4 cycles: 304s > 300s ✗ → ATE
- 5 cycles: 380s

At 340s: 4 cycles = 304s < 340s ✓, giving the 4th key a full 66s attempt. 5th key gets 340-304=36s (partial, but better than 0).

**Safety**: NVU_TIER_BUDGET_KIMI_NV=340 is still well below TIER_TIMEOUT_BUDGET_S=475 (global budget). The kimi tier budget only governs the kimi_nv tier's own timeout before cross-model fallback.

## 4. Optimization Plan

**Single parameter**: `NVU_TIER_BUDGET_KIMI_NV 300→340` (+40s, +13.3%)

**Rationale**:
- R2384 (285→300) was designed for KEY_COOLDOWN=15s (77s cycles, 3 full + partial 4th)
- R2386 (KEY_COOLDOWN 15→10) made cycles faster (76s) but the 300s budget still only allows 3 full cycles
- 340s allows 4 full cycles (304s) + 36s for 5th key attempt
- Combined with R2386: KEY_COOLDOWN=10 saves 25s dead time per 5-key cycle vs R2383's 15s
- The 1h data shows 3/4 kimi_nv failures at exactly 295-300s — the budget ceiling is the bottleneck
- No change to glm5_2_nv or dsv4p_nv budgets
- Zero HM2 change (iron law)

## 5. Execution

```bash
# On HM1 via HM2 SSH:
cd /opt/cc-infra
cp docker-compose.yml docker-compose.yml.bak.R2387_$(date +%Y%m%d_%H%M%S)
sed -i 's/NVU_TIER_BUDGET_KIMI_NV=300/NVU_TIER_BUDGET_KIMI_NV=340/' docker-compose.yml
docker compose up -d --no-deps nv_gw
```

**Verification**:
- Compose value: `NVU_TIER_BUDGET_KIMI_NV=340` (was 300) ✓
- Runtime env: `NVU_TIER_BUDGET_KIMI_NV=340` in container ✓
- Container recreated: nv_gw up (healthy) ✓
- Health check: `{"status":"ok","port":40006}` ✓

## 6. Expected Outcome

- Fewer kimi_nv all_tiers_exhausted at budget ceiling (300→340)
- 4th key gets full 66s attempt instead of truncated at 36s
- 5th key gets partial 36s runway instead of 0
- 502 rate from 37.7% (24h) / 50% (1h) toward <30%
- KEY_COOLDOWN=10 (R2386) + BUDGET=340 (R2387) = effective +65s over R2383 baseline (20→10 cooldown = -50s dead, 285→340 budget = +55s)

## 7. Single-Param Flag
- **Only change**: `NVU_TIER_BUDGET_KIMI_NV` in HM1's `/opt/cc-infra/docker-compose.yml`
- HM2 local completely untouched (iron law).

## ⏳ 轮到HM1优化HM2