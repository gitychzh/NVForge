# R2403 (HM2→HM1): NVU_TIER_BUDGET_KIMI_NV 400→420

## Data (HM1, 6h window ending ~18:40 UTC)

| Metric | Value |
|--------|-------|
| Total requests | 76 |
| Success (200) | 34 |
| ATE (502) | 40 |
| Overall SR | 44.7% |

### Per-model

| Model | Total | OK | ATE | SR% | avg_ok | avg_ate |
|-------|-------|----|-----|-----|--------|---------|
| glm5_2_nv | 34 | 12 | 22 | 35.3% | 40s | 110s |
| kimi_nv | 40 | 22 | 18 | 55.0% | 66s | 210s |

### ATE detail (kimi_nv)

| Pattern | Count | Duration Range | Root cause |
|---------|-------|----------------|------------|
| upstream_type=NULL, tiers_tried=1 | 15 | 60ms–1.5s | Pre-tier-phase fast-fail (breaker/map failure, NOT budget) |
| upstream_type=nvcf_pexec | 3 | 198–400s | NVCF degradation, actual pexec attempts |
| zombie_empty_completion | 2 | 131–139s | NVCF upstream content filter, not gateway fixable |
| NVStream_IncompleteRead | 1 | 56s | Transport transient |

### ATE duration distribution (kimi_nv)

| Bucket | Count |
|--------|-------|
| <1s | 1 (fast-fail) |
| 1–5s | 1 (fast-fail) |
| 50–100s | 2 |
| 100–150s | 2 |
| 150–200s | 2 |
| 200–250s | 6 |
| 350–400s | 1 (400s budget wall?) |
| >400s | 3 (MAX=400s, hard wall) |

## Diagnosis

1. **NULL ATE (15/18 = 83%)**: `upstream_type=NULL` and `tiers_tried_count=1` means the gateway rejected the request *before* entering key cycling. This is **not** a budget ceiling pattern. Potential causes: big-input breaker OPEN, model mapping failure, tier budget pre-exhaustion. These are outside this budget change's scope.

2. **Budget wall risk (3/18)**: Three `nvcf_pexec` ATE hit 350–400s. With `TIER_BUDGET_KIMI_NV=400`, a 400,097ms ATE is at the exact budget wall (`status=502, error_type='all_tiers_exhausted', duration_ms≈budget`). Slight increase gives margin for the key-cycling tail.

3. **Budget formula check**: 
   - Thinking model: `per_key_timeout = 66s` (NVU_FORCE_STREAM_UPGRADE_TIMEOUT)
   - 5 keys × 66s = 330s for full pexec cycle
   - `FASTBREAK=4` → FASTBREAK after 4 consecutive timeouts = 4×66 = 264s + (3×KEY_COOLDOWN=5) = 279s consumed
   - Remaining for 5th key attempt: 400−279 = 121s > 66s → key5 gets full attempt
   - So FASTBREAK=4 isn't prematurely cutting the 5th key with budget=400

## Fix

**NVU_TIER_BUDGET_KIMI_NV: 400 → 420**

- `420s = 5-key full cycle + 90s margin`
- Absorbs the 350–400s tail ATE, prevents hard wall at exactly 400s
- NULL ATE (pre-tier-phase) unaffected by budget change — will address in future rounds if persistent
- No paired parameter change — budget increase only

## Verification

- `docker exec nv_gw env | grep NVU_TIER_BUDGET_KIMI_NV` → `420` ✅
- `curl localhost:40006/health` → ok ✅
- Container restarted with `docker compose up -d nv_gw`

## Expected effect

- 350–400s ATE should absorb into the new 420s budget
- Null ATE unaffected (remain ~60ms–1.5s);
- +20s minimizes risk of budget truncation when key chain goes deep.

## ⏳ 轮到HM1优化HM2  ← 脚本检测此标记
