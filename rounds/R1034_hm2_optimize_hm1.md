# R1034: HM2→HM1 — NVU_STREAM_TOTAL_DEADLINE_S 66→72 (+6s)

**Decision**: Single-param change — align stream total deadline with integrate think timeout to eliminate premature stream kills.

## Data (SSH to HM1, full collection)

### Container Info
- Container: `nv_gw`, started `2026-07-09T22:25:12Z` (~8h uptime)
- Health: OK, all 4 tiers active

### 6h DB (nv_requests)
| Tier | Total | OK | Err | SR |
|------|-------|-----|-----|------|
| glm5_2_nv | 223 | 214 | 9 | 96.0% |
| dsv4p_nv | 67 | 58 | 9 | 86.6% |
| kimi_nv | 46 | 45 | 1 | 97.8% |
| minimax_m3_nv | 34 | 26 | 8 | 76.5% |
| **All** | **370** | **343** | **27** | **92.7%** |

### Post-restart (22:25 UTC→now): 5/5 100% SR, 0 errors
All 27 errors are pre-restart (before 22:25 UTC). Current config is clean.

### Error Breakdown (6h, all pre-restart)
| Error Type | Count |
|------------|-------|
| all_tiers_exhausted | 21 |
| NVStream_TimeoutError | 3 |
| stream_total_deadline | 3 |

### ATE Details
- All 27 ATEs: `tiers_tried_count=1`, avg 100,314ms
- All `fallback_occurred=false`, `all_tiers_exhausted`
- 0 `NV-MS-FB` logs — ms_gw fallback not triggered (FALLBACK_GRAPH={} expected per R832)

### tier_attempts (6h)
- Only 1 entry: minimax_m3_nv IntegrateTimeout, avg 90,762ms

### NVCFPexecTimeout
- 0 entries — pexec paths all succeed

### Architectual Mismatch
- `NVU_INTEGRATE_THINKING_TIMEOUT_S=90` — per-key integrate timeout override
- `NVU_STREAM_TOTAL_DEADLINE_S=66` — total stream deadline, aligned with UPSTREAM=66
- **Mismatch**: integrate allows 90s per key, but stream deadline cuts at 66s
- Observed integrate max: 71.3s (per compose comment). Current 66s deadline kills requests in 66-71.3s window → `stream_total_deadline` errors (3 of 27)

### ms_gw Health
- ms_gw healthy: handling glm5_2 and dsv4p successfully
- `MS-RELAY-ERR BrokenPipeError` on nonstream relay (same R1031 pattern)
- ms_gw fallback code active (config.py defaults ENABLED=1, URL=http://ms_gw:40007)
- ModelMap: glm5_2_nv:glm5_2_ms, dsv4p_nv:dsv4p_ms, kimi_nv:kimi_ms

## Change

**NVU_STREAM_TOTAL_DEADLINE_S: 66 → 72 (+6s)**

Rationale:
- +6s covers observed integrate max 71.3s → eliminates `stream_total_deadline` errors
- Safety margin: 120s (openclaw provider timeout) - 72s = 48s, safe
- `NVU_INTEGRATE_THINKING_TIMEOUT_S=90` still governs per-key timeout
- Deadline still catches zombie streams (72s < 90s integrate max)
- `NVStream_TimeoutError` (3 errors) are NVCF internal, not config-fixable

## Verification
- YAML parse: OK
- `docker compose stop nv_gw && docker compose up -d nv_gw`: OK
- `docker exec nv_gw env | grep NVU_STREAM_TOTAL_DEADLINE_S`: 72 ✓
- Health check: `{"status": "ok", ...}` ✓

## Iron Rule
- Single param: `NVU_STREAM_TOTAL_DEADLINE_S`
- Only changed HM1, never HM2
- Data-backed: 3 `stream_total_deadline` errors pre-restart, architectual mismatch identified

## ⏳ 轮到HM1优化HM2