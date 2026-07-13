# R1265: HM2→HM1 — Remove dsv4p_nv from ms_gw MODELMAP; route dsv4p ATE via peer-fallback

## Data Collection

### 6h Window (~2026-07-13 18:00 – 2026-07-14 00:00 UTC)

| Metric | Value |
|--------|-------|
| Total requests | 87 |
| OK (200) | 70 |
| Fail (non-200) | 17 |
| **Success rate** | **80.5%** |

### Per-Model Breakdown

| Model | Reqs | OK | Fail | SR | Avg TTFB | Avg Dur | Max Dur |
|-------|------|-----|------|-----|----------|---------|---------|
| glm5_2_nv | 74 | 60 | 14 | 81.1% | 11.3s | 12.9s | 44.8s |
| dsv4p_nv | 11 | 9 | 2 | 81.8% | 23.9s | 36.9s | 72.0s |
| *unmatched* | 2 | 1 | 1 | — | — | — | — |

### Per-Path Stats

| Path | Reqs | OK | Fail | SR | Avg TTFB | Avg Dur |
|------|------|-----|------|-----|----------|---------|
| nv_integrate | 68 | 57 | 11 | 83.8% | 11.5s | 13.0s |
| nvcf_pexec | 12 | 12 | 0 | 100% | 26.3s | 26.3s |
| NULL (ATE) | 7 | 1 | 6 | 14.3% | 0.9s | 32.1s |

### Error Breakdown

| Error Type | Count | % of Fail | Model |
|-----------|-------|-----------|-------|
| zombie_empty_completion | 10 | 58.8% | glm5_2_nv (all) |
| all_tiers_exhausted | 5 | 29.4% | 3 dsv4p_nv + 2 glm5_2_nv |
| NVStream_IncompleteRead | 1 | 5.9% | glm5_2_nv |
| (ms_gw TimeoutError) | 1 | 5.9% | dsv4p_nv |

### Real-Time Logs (last 100 lines from nv_gw)

- 100% NV-INTEGRATE-SUCCESS first-attempt (glm5_2_nv integrate, all keys)
- 0 NV-TIER-FAIL in recent window
- 1 NV-ZOMBIE-EMPTY (glm5_2_nv, 183K input, 15 chars content — correctly injected content_filter SSE)
- 1 NV-MS-FB BrokenPipeError (4987ms, relay_started=True)
- 1 NV-MS-FB TimeoutError (233s, relay_started=True)

### Tier Attempts (12h)

- 6 IntegrateTimeout (glm5_2_nv), all 90-93s, scattered across k1/k3
- 0 NVCFPexecTimeout (pexec path) in nv_tier_attempts
- No NVCFPexecTimeout entries in any tier — pexec path healthy

## Analysis

### Failure Classification

1. **zombie_empty_completion (10, 58.8%)** — NVCF code-level defect. glm5_2_nv integrate returns `finish_reason=stop` with 12-15 chars content for large context (>160K chars). Gateway correctly detects zombie and injects `content_filter` SSE error chunk → openclaw falls back. **Not config-fixable.** NVCF function-level behavior.

2. **dsv4p_nv ATE (3, 17.6%)** — Key finding: ms_gw fallback always wins over peer-fallback, and ms_gw dsv4p_ms is unreliable.

   **Full flow (confirmed by aligned log+DB):**
   ```
   k3 empty_200 (~2s) → cycle to k4
   k4 NVCFPexecTimeout (~10s) → FASTBREAK=1 correct (function-level timeout)
   Tier fail: empty200=1 + timeout=1 → elapsed=72011ms
   ABORT-NO-FALLBACK (single-tier, 3model architecture)
   NV-MS-FB: dsv4p_ms fallback → BrokenPipeError (5s) or TimeoutError (233s)
   Peer-fallback: NEVER attempted (fallback_actually_attempted=false)
   → 502 returned to client
   ```

   **Root cause**: handlers.py line 348-388 uses `if ms_gw_fallback ... elif peer_fallback`. Since dsv4p_nv IS in `NVU_MS_GW_FALLBACK_MODELMAP`, ms_gw always fires first. ms_gw dsv4p_ms has **100% failure rate** (6/6 observed: 3 BrokenPipeError + 3 TimeoutError). Peer-fallback (HM2 nv_gw, independent key pool, confirmed healthy from HM1) never gets a chance.

3. **glm5_2_nv ATE (2, 11.8%)** — 404 NONCYCLE. NVCF function 3b9748d8 returns 404 on both integrate+pexec. R1241-discovered function-level degradation. NONCYCLE correct. **Not config-fixable.** Wait for NVCF recovery.

4. **NVStream_IncompleteRead (1, 5.9%)** — Code-level stream interruption. Not config-fixable.

### Config Assessment

All params at floor/optimal:
- `UPSTREAM_TIMEOUT=66` — aligned with NVCFPexecTimeout max=62.6s, buffer=3.4s ≥ 3s (R751 rule)
- `TIER_TIMEOUT_BUDGET_S=210` — ample headroom for peer-fallback
- `NVU_TIER_BUDGET_DSV4P_NV=72` — dsv4p_nv ATE at exactly 72s confirms budget binding
- `NVU_TIER_BUDGET_GLM5_2_NV=96` — safe for integrate thinking=90s
- `TIER_COOLDOWN_S=15` — R1103 validated for key-specific empty_200
- `NVU_PEXEC_TIMEOUT_FASTBREAK=1` — function-level timeout, FASTBREAK=1 correct
- `NVU_EMPTY_200_FASTBREAK=2` — key-specific empty_200 (1/5 keys), FASTBREAK=2 is correct intent per R1031 (but code-level bug in R1039 makes it a no-op in pexec path)
- `NVU_INTEGRATE_TIMEOUT_FASTBREAK=1` — function-level integrate timeout, correct
- `NVU_PEER_FB_SKIP_MODELS=""` — all models eligible for peer-fb
- `NVU_PEER_FALLBACK_ENABLED=1` — peer-fallback enabled

## Optimization

### Change: Remove `dsv4p_nv:dsv4p_ms` from `NVU_MS_GW_FALLBACK_MODELMAP`

**File**: `/opt/cc-infra/docker-compose.yml` (HM1 only)

**Before**:
```
NVU_MS_GW_FALLBACK_MODELMAP: "glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms"
```

**After**:
```
NVU_MS_GW_FALLBACK_MODELMAP: "glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms"
```

**Rationale**:
1. ms_gw dsv4p_ms has **100% failure rate** (6/6: BrokenPipeError + TimeoutError). Each futile relay wastes 5-233s.
2. The `if ms_gw ... elif peer_fb` ordering in handlers.py means ms_gw always wins — peer-fallback never fires for dsv4p_nv.
3. By removing dsv4p_nv from MODELMAP, the `if` guard fails and the `elif peer_fallback` path is taken.
4. HM2's nv_gw has independent key pool (different IPs, different mihomo ports) — confirmed healthy from HM1 (`curl http://100.109.57.26:40006/health` → OK).
5. Peer-fallback timeout=66s << ms_gw's 200s TimeoutError → faster failure resolution if peer-fb also fails.
6. glm5_2_nv and kimi_nv keep their ms_gw fallback (their ms_gw backends are functional).

**Risk**: If peer-fb also fails, request returns 502 — same as current behavior (ms_gw already fails → 502). No regression.

**Verification**: 
- `docker exec nv_gw env | grep NVU_MS_GW_FALLBACK_MODELMAP` → `glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms` ✓
- `curl http://localhost:40006/health` → `{"status":"ok"}` ✓
- Test request: dsv4p_nv "Hello, reply OK" → `{"content":"OK","finish_reason":"stop"}` ✓

### Non-Changes (validated optimal)

- `NVU_EMPTY_200_FASTBREAK=2` — kept at 2. R1031 justified (key-specific empty_200). R1039 code-level bug makes it a no-op in pexec path, but that's code-level, not config-fixable. Setting to 1 would regress the intended behavior.
- All other params at floor/optimal — no change needed.

## Results

| Metric | Before | After |
|--------|--------|-------|
| dsv4p_nv ATE recovery path | ms_gw dsv4p_ms (100% fail) | peer-fallback HM2 nv_gw (independent key pool) |
| ATE recovery time | 5-233s (futile ms_gw relay) | 0-66s (peer-fb timeout ceiling) |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2,kimi,dsv4p | glm5_2,kimi (dsv4p removed) |
| Single param | yes | yes |

**Expected improvement**: dsv4p_nv ATE requests get peer-fallback rescue from HM2's independent key pool instead of the guaranteed-failure ms_gw dsv4p_ms path. The 66s peer-fb timeout is faster than ms_gw's 200s abort. Success rate for dsv4p_nv ATE path should improve from current 0% (ms_gw always fails) to non-zero (peer-fb has HM2's 5-key pool).

**Iron rule**: Only change HM1, never HM2. ✓

## ⏳ 轮到HM1优化HM2