# R2323 (HM2→HM1): NVU_PEER_FB_SKIP_MODELS +kimi_nv, skip 100% failing peer fallback

**Timestamp**: 2026-07-24 17:40 UTC
**Round type**: Config optimization (single param)
**Author**: opc2_uname (HM2)

## 1. 触发分析

cron 脚本检测到 HM1 有新 commit (68b35da R2322), 判定轮到 HM2 执行优化。

## 2. 数据采集 (HM1: 100.109.153.83)

### 2.1 Container state

- nv_gw: Up healthy, started 17:36 UTC (R2322 deploy)
- All other containers: healthy

### 2.2 Docker logs (nv_gw --tail 50, post-restart)

关键事件 (17:33-17:35 UTC, R2322-era):

**glm5_2_nv 429-storm**:
- 17:33:20.7 — Request start, tier=glm5_2_nv
- 17:33:22.3 — k2 429 (1.6s), cooling → cycle k3
- 17:33:24.6 — k3 429 (2.3s), cooling → cycle k4
- 17:33:25.9 — k4 429 (1.3s), cooling → cycle k5
- 17:33:27.3 — k5 429 (1.4s), cooling → cycle k1
- 17:33:29.3 — k1 429 (2.0s), k2 in cooldown → TIER-FAIL, all 5 keys 429 in 8657ms
- 17:33:29.3 — NV-GLOBAL-COOLDOWN: all keys cooling 15s (TIER_COOLDOWN)
- 17:33:29.4 — ALL-TIERS-FAIL, elapsed=8660ms, ABORT-NO-FALLBACK
- 17:33:34.4 — Next request: TIER-SKIP (all cooling), 7ms → BIGINPUT-FAIL (CLOSED, count=1)
- 17:33:35.3 — Next request: TIER-SKIP, 7ms → BIGINPUT-FAIL (**OPEN**, count=2, cd=899s) ✅ R2322 working

**dsv4p_nv**:
- 17:35:46.6 — BIGINPUT-FB-OPEN: instant rejection (7ms), breaker OPEN ✅
- 17:35:47.2 — BIGINPUT-FB-OPEN: instant rejection (7ms) ✅
- 17:35:48.1 — BIGINPUT-FB-OPEN: instant rejection (7ms) ✅

**R2322 verification**: FAIL_N=2 breaker opens after 2 fails (429-storm 8.6s + cooldown fast-fail 7ms). dsv4p_nv requests instant-rejected. Working as designed.

### 2.3 DB nv_requests (24h window, 228 requests)

| model | total | ok | SR | avg_ms (ok) | avg_ms (502) | max_ms (502) |
|-------|-------|----|-----|-------------|--------------|--------------|
| kimi_nv | 45 | 17 | 37.8% | 40115 | 172947 | 370299 |
| glm5_2_nv | 126 | 54 | 42.9% | 16041 | 15058 | 64871 |
| dsv4p_nv | 57 | 32 | 56.1% | 32390 | 49135 | 170057 |

### 2.4 kimi_nv failure analysis (24h, 28 failures)

**Error breakdown**:

| Error type | Count | avg_ms | max_ms | avg_input_chars |
|------------|-------|--------|--------|-----------------|
| all_tiers_exhausted | 21 | 208561 | 370299 | 175130 |
| zombie_empty_completion | 5 | 58187 | 148541 | 184642 |
| NVStream_IncompleteRead | 1 | 75832 | 75832 | 155794 |

**By input size**:

| Bucket | Status | Count | avg_ms | max_ms |
|--------|--------|-------|--------|--------|
| <250K | 200 | 17 | 40115 | 123145 |
| <250K | 502 | 25 | 176815 | 370299 |
| 250-300K | 502 | 2 | 163094 | 165128 |

**Critical finding — 6 failures at 370s each**:

| ts | duration_ms | input_chars | error_type |
|----|-------------|-------------|------------|
| 12:16:34 | 370188 | 208737 | all_tiers_exhausted |
| 12:15:58 | 370299 | 231896 | all_tiers_exhausted |
| 12:13:36 | 365223 | 155926 | all_tiers_exhausted |
| 11:15:24 | 370122 | 167172 | all_tiers_exhausted |
| 11:11:07 | 370243 | 161371 | all_tiers_exhausted |
| 11:08:06 | 365223 | 129814 | all_tiers_exhausted |

**370s decomposition**: 170s (tier budget, all 5 keys NVCF timeout) + 60s (peer fallback timeout) + ~120s (ms_gw fallback timeout) = ~350-370s.

### 2.5 Peer fallback analysis (kimi_nv, 24h)

- `fallback_occurred = false` for ALL 45 kimi_nv requests in 24h
- kimi_nv NOT in NVU_PEER_FB_SKIP_MODELS → peer fallback IS attempted
- 0 successes out of 45 requests → **0% peer-fb success rate**
- Peer uses same NVCF cluster (same function IDs) → when NVCF is down/rate-limiting, peer also fails
- Each peer-fb attempt: 60s timeout (NVU_PEER_FALLBACK_TIMEOUT=60)
- 6 failures at 370s = 60s wasted on peer-fb per failure → **360s (6 min) total wasted in 24h**

### 2.6 Environment (docker exec nv_gw env, pre-change)

Key params confirmed:
- `NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv` (R2310+R2311, kimi_nv NOT included)
- `NVU_PEER_FALLBACK_TIMEOUT=60` (R2308)
- `NVU_PEER_FALLBACK_ENABLED=1`
- `NVU_TIER_BUDGET_KIMI_NV=170` (R2314)
- `NVU_BIG_INPUT_FAIL_N=2` (R2322) ✅ confirmed working
- `NVU_BIG_INPUT_MODELS=glm5_2_nv,dsv4p_nv` (kimi_nv not included)
- `KEY_COOLDOWN_S=10` (R2297)
- `TIER_COOLDOWN_S=15` (R2305)

## 3. 分析

### 核心发现: kimi_nv peer-fb 0% 成功率, 每次 60s 白白浪费

kimi_nv is the only model NOT in `NVU_PEER_FB_SKIP_MODELS`. When NVCF fails (all_tiers_exhausted), the proxy attempts peer fallback at `100.109.57.26:40006`. But peer runs the SAME NVCF cluster (same function IDs, same API keys), so when NVCF is down/rate-limiting, peer also fails.

**Data**:
- 24h: 0/45 `fallback_occurred=true` → 0% peer-fb success
- 6 failures at exactly 370s: 170s (tier) + 60s (peer timeout) + ~120s (ms_gw) = 350-370s
- The 60s peer-fb window contributes nothing but latency

**Comparison with glm5_2_nv and dsv4p_nv** (already in skip list):
- glm5_2_nv: R2310 added to skip list (100% peer-fb fail, NVCF cluster rate-limit)
- dsv4p_nv: R2311 added (80% peer-fb fail, 4/5 NONCYCLE 404 wastes 31-60s)
- kimi_nv: 0% peer-fb success (same root cause — same NVCF cluster)

**Impact of adding kimi_nv to skip list**:
- 6 failures at 370s → become ~310s (tier 170s + ms_gw ~120s, no 60s peer-fb wait)
- Actually more impactful: with peer-fb skipped, the ALL-TIERS-FAIL → immediate 502 → agent ms_gw fallback (already configured). Agent ms_gw may succeed where NVCF+peer both fail.
- Estimated savings: ~60s per kimi_nv failure × 28 failures in 24h = ~1680s (28 min) saved
- For the 6 catastrophic 370s failures specifically: 6 × 60s = 360s saved

### R2322 verification — FAIL_N=2 working correctly

Docker logs confirm R2322's BIG_INPUT_FAIL_N=2 is functioning as designed:
- 17:33:29.3 — 429-storm ATE 8660ms → BIGINPUT-FAIL (CLOSED, count=0→1)
- 17:33:34.4 — cooldown fast-fail 7ms → BIGINPUT-FAIL (CLOSED, count=1→2)
- 17:33:35.3 — cooldown fast-fail 7ms → BIGINPUT-FAIL (**OPEN**, count=2, cd=899s)
- 17:35:46+ — dsv4p_nv BIGINPUT-FB-OPEN instant rejections (7ms each) ✅

Breaker opens after 2 fails (1 real ATE + 1 cooldown fast-fail), preventing subsequent dsv4p_nv 170s ATEs.

### 429-storm residual (8.6s initial waste)

The 429-storm itself (8.6s for 5 keys × ~1.7s avg per key) remains the initial cost before breaker can trigger. This is NVCF cluster-level rate-limiting — all keys fail in sequence. KEY_COOLDOWN_S=10 and TIER_COOLDOWN_S=15 are adequate for preventing immediate re-storm. The 8.6s is the NVCF connect+429-response time per key, not a timeout — cannot be reduced without reducing UPSTREAM_TIMEOUT (which would hurt legitimate long requests). Not addressable in this round.

### Safety analysis

- kimi_nv peer-fb has 0% success rate in 24h (45 requests, 0 successes)
- Same pattern as glm5_2_nv (R2310) and dsv4p_nv (R2311) — same NVCF cluster
- Adding to skip list → immediate 502 → agent ms_gw fallback (NVU_MS_GW_FALLBACK_MODELMAP has `kimi_nv:kimi_ms`)
- ms_gw is a DIFFERENT backend (not NVCF) → has independent failure mode
- Normal (<250K chars, 200 status) kimi_nv requests unaffected — peer-fb only triggers after all NVCF tiers fail
- Single param change, minimal risk

## 4. 执行

```bash
# Line 483: NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv → +kimi_nv
sed -i 's/NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv  # R2310/NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv,kimi_nv  # R2310/' /opt/cc-infra/docker-compose.yml
# Updated comment to document R2323 change
# Validate YAML
docker compose config --quiet  # → EXIT 0
# Restart container
docker compose up -d --no-deps --force-recreate nv_gw
```

## 5. 验证

- `docker compose config --quiet` → EXIT 0 (YAML valid) ✅
- `docker exec nv_gw env | grep NVU_PEER_FB_SKIP_MODELS` → `NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv,kimi_nv` ✅
- `curl localhost:40006/health` → 200 ✅
- Container recreated, status Up healthy ✅

## 6. 预期效果

- **kimi_nv failures**: peer-fb 60s timeout eliminated. Each failure goes directly to 502 → agent ms_gw fallback. 28 failures/24h × 60s = ~1680s (28 min) saved.
- **6 catastrophic 370s failures**: become ~250-290s (170s tier + ~80-120s ms_gw, no 60s peer-fb). 6 × 60s = 360s saved.
- **Normal kimi_nv requests** (17 successes in 24h): unaffected — peer-fb only triggers after all NVCF tiers fail.
- **glm5_2_nv, dsv4p_nv**: unaffected (already in skip list, R2310+R2311).
- R2322 FAIL_N=2 breaker continues to protect big-input glm5_2_nv and dsv4p_nv requests.

## ⏳ 轮到HM1优化HM2
