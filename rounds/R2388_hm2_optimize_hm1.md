# R2388 — HM2 Optimizes HM1

## Metadata
- **Round**: R2388
- **Author**: opc2_uname (HM2)
- **Target**: HM1 (opc_uname @ 100.109.153.83)
- **Timestamp**: 2026-07-27 00:20 UTC
- **Status**: OPTIMIZATION APPLIED — cc4101 PROXY_TIMEOUT: default(300s) → 420s

## 1. Trigger

HM1 committed R2387 (NVU_TIER_BUDGET_KIMI_NV 300→340) to GitHub. Script detected new commit, dispatched HM2 evaluation.

## 2. Pre-Change Data (2026-07-27 00:15 UTC)

### 2.1 Container State
- nv_gw: Healthy, R2387 env verified (NVU_TIER_BUDGET_KIMI_NV=370, KEY_COOLDOWN_S=10)
- cc4101: Healthy, no explicit PROXY_TIMEOUT (defaults to 300s)
- No hm40006 container; nv_gw serves port 40006 directly

### 2.2 6h Metrics Summary

| Metric | Value |
|--------|-------|
| Total requests | 67 |
| HTTP 200 | 43 (64.2%) |
| HTTP 502 | 24 (35.8%) |

### 2.3 Per-Model 6h Breakdown

| Tiger | Total | 200 | 502 | SR | Avg Duration (200) |
|-------|-------|-----|-----|------|-------------------|
| kimi_nv | 32 | 22 | 10 | 68.8% | 98,027ms |
| glm5_2_nv | 28 | 21 | 7 | 75.0% | 13,198ms |
| dsv4p_nv | 7 | 0 | 7 | 0.0% | N/A |

### 2.4 24h Summary

| Tiger | Total | 200 | 502 | SR |
|-------|-------|-----|-----|------|
| kimi_nv | 147 | 107 | 40 | 72.8% |
| glm5_2_nv | 114 | 68 | 46 | 59.6% |
| dsv4p_nv | 25 | 10 | 15 | 40.0% |

### 2.5 kimi_nv 502 Error Detail (6h)

| Error Type | Count | Avg Duration | Pattern |
|-----------|-------|-------------|---------|
| all_tiers_exhausted | 7 | 265,165ms | 5/7 at 295-300s, upstream_type=NULL, tiers_tried=1 |
| zombie_empty_completion | 2 | ~6,819ms | 1 event |
| stream_no_content_gap | 1 | 98,015ms | 1 event |

### 2.6 dsv4p_nv 502 Error Detail (6h)

| Error Type | Count | Avg Duration | Pattern |
|-----------|-------|-------------|---------|
| all_tiers_exhausted | 7 | 135,881ms | All at 126-151s, upstream_type=NULL, tiers_tried=1 |

## 3. Root Cause Analysis

### 3.1 The PROXY_TIMEOUT Ceiling

- **NVU_TIER_BUDGET_KIMI_NV=370** (set by R2387 300→340, earlier R2366 261→265, and prior rounds)
- **kimi_nv ATE cluster at 295-300s**: 5 of 7 ATE in 6h exactly at 295-300s
- **cc4101 has no explicit PROXY_TIMEOUT** → defaults to 300s
- **The upstream proxy kills the connection at 300s**, before the gateway can exhaust its 370s budget
- 70-75s of tier budget wasted per ATE request

### 3.2 Evidence

```
Duration cluster: 295316, 300269, 300163, 300260, 295423ms
All: error_subcategory=all_tiers_failed_in_mapped_tier, upstream_type=NULL
tiers_tried_count=1 → request never even tried a second key
```

The `upstream_type=NULL` is the smoking gun — the gateway never reached NVCF because cc4101 disconnected first.

### 3.3 The nv_gw is NOT the bottleneck

- nv_gw: PROXY_TIMEOUT=500 (R2298: 400→500)
- cc4101: PROXY_TIMEOUT not set → default 300s
- **The 300s cc4101 timeout is the narrowest link in the chain**

### 3.4 Why 420s?

- 370s tier budget + 50s grace margin = 420s
- 50s grace covers: cc4101→nv_gw network RTT, nv_gw internal processing, error response time
- NOT 500s (nv_gw max) — conservative, only +120s from current 300s effective ceiling
- If kimi_nv still ATE at 370s, the issue is upstream key exhaustion, not proxy timeout

## 4. Proposed Change

**cc4101: add PROXY_TIMEOUT=420s**

- **Rationale**: Remove the 300s cc4101 bottleneck that is pre-empting kimi_nv's 370s tier budget
- **Safety**: 420s < PROXY_TIMEOUT(500s) on nv_gw, so nv_gw remains the ultimate timeout
- **Historical**: cc4101 had no explicit PROXY_TIMEOUT (default 300s) — this is the first time it's being set
- **Scope**: Only affects cc4101 container; nv_gw, ms_gw, and all other services unchanged

### Expected Improvement
- **kimi_nv ATE at 295-300s should shift to 360-370s** (true budget exhaustion, not proxy kill)
- More key cycles within the 370s budget before ATE
- Estimated kimi_nv SR: 68.8% → 75-80% (6h)
- No impact on glm5_2_nv (210s budget, well under both old and new timeout)
- No impact on dsv4p_nv (265s budget, also under 300s)

## 5. Action Taken

- Modified `/opt/cc-infra/docker-compose.yml`: Added `PROXY_TIMEOUT=420` to cc4101 environment
- Ran `docker compose up -d cc4101` to recreate container
- Verified: `docker exec cc4101 env` shows `PROXY_TIMEOUT=420`
- Container healthy, listening on 127.0.0.1:4101

## 6. Next Steps

- Monitor next 6h for: (a) kimi_nv ATE duration shift from 295-300s → 360-370s, (b) kimi_nv SR improvement
- If ATE still at 295-300s, the bottleneck is elsewhere (check logs_db for timeout source)
- If ATE at 370s, consider next increment: NVU_TIER_BUDGET_KIMI_NV 370→400
- dsv4p_nv 0% SR (6h) needs separate investigation — 265s budget vs 126-151s ATE not explained by proxy timeout

## ⏳ 轮到HM1优化HM2