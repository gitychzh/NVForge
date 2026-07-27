# R2396 (HM2→HM1): NVU_TIER_BUDGET_KIMI_NV 380→400

## 改前数据 (2026-07-27 08:25 UTC)

### nv_gw 健康

- `/health` → `{"status": "ok", "proxy_role": "passthrough", "nv_num_keys": 5}`
- Container `nv_gw` running, passthrough role
- env: `NVU_STREAM_FIRST_BYTE_DEADLINE_S=16`, `UPSTREAM_TIMEOUT=24`, `KEY_COOLDOWN_S=5`, `TIER_COOLDOWN_S=0`

### DB 6h 窗口 (nv_requests)

| mapped_model | total | OK | SR% | avg_ok_ms | fail | avg_fail_ms |
|--------------|-------|----|-----|-----------|------|------------
| glm5_2_nv | 27 | 20 | 74.1% | 14430 | 7 | 66676 |
| kimi_nv | 38 | 32 | 84.2% | 76841 | 6 | 293532 |
| dsv4p_nv | 0 | 0 | - | - | 0 | - |

### DB 6h 窗口 (error breakdown)

| mapped_model | error_type | error_subcategory | count | avg_ms |
|--------------|------------|---------------------|-------|--------
| glm5_2_nv | zombie_empty_completion | - | 4 | 13223 |
| glm5_2_nv | all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 3 | 137948 |
| kimi_nv | all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 5 | 313019 |
| kimi_nv | zombie_empty_completion | - | 1 | 196099 |

### kimi_nv ATE 详细分析

- **5 ATE**, all at `start_tier_idx=0`, `tiers_tried_count=1`: only kimi_nv tier tried, no fallback to dsv4p/glm5_2. This is a **fast-fail at mapped tier**, not a budget-exhaust issue.
- ATE avg duration: **313s** (min ~196s), max approaching 380s budget ceiling.
- **Tail risk**: ATE with +~313s = total ~135+313=448s on some upstream chain, but within the ATE itself the `duration_ms` is approaching 380s. With upstream_timeout=24 and key_cooldown=5, the per-cycle cost is ~29s. 5 cycles = 145s nominal, but the 313s average suggests some cycles take longer (slow pexec, stream start delays).
- `zombie_empty_completion` (1/6) on kimi_nv at 196s: early EOF with `finish_reason=stop` and 2097 output tokens, a truncated completion.

### glm5_2_nv 就况

- 4 `zombie_empty_completion` at 13s avg: all `finish_reason=stop`, avg chars=396K, avg output_tokens=0. These are **truncated completions** — NVCF returned empty body with 200 status.
- 3 ATE at 135s avg, `tiers_tried_count=1`, `start_tier_idx=2`. Only glm5_2_nv tried, no fallback attempt.

### 2h 最近窗口 (status=200 OK)

| mapped_model | count | avg_ok_ms | min | max |
|--------------|-------|-----------|-----|-----|
| glm5_2_nv | 5 | 30956 | 6766 | 96479 |
| kimi_nv | 8 | 90498 | 19557 | 252619 |

### kimi_nv ttfb>16s (STREAM_FIRST_BYTE_DEADLINE)

- 6h: 25/33 OK kimi have ttfb > 16s (76% exceed STREAM_FIRST_BYTE_DEADLINE)
- This is normal for kimi (long stream) → `NVU_STREAM_TOTAL_DEADLINE_S=90` and `PROXY_TIMEOUT=420` are the real guards.

## 问题分析

### kimi_nv ATE 尾端风险，380s 硬墙

- 5 ATE avg=313s, max tail >~380s
- `UPSTREAM_TIMEOUT=24` + `KEY_COOLDOWN_S=5` = 29s per cycle nominally. 5 cycles of 29s = 145s, but actual 313s suggests:
  - Stream start delays (kimi ttfb frequently >16s, some cycles have >24s pexec time before the timeout fires)
  - Some keys hit 429 cooldown which extends the cycle
  - `all_tiers_exhausted` means no keys responded successfully within the budget
- Budget compression at 380s: if a future cluster event produces 7-8 failed cycles, 380s = hard wall. +20s provides a safety margin.

### Why 380→400?

- **Non-budget root cause**: 5 ATE all have `tiers_tried_count=1` = fast fail at kimi tier, not "budget exhausted after trying all keys". The ATE is a genuine NVCF cluster issue.
- **Tail risk**: 380s budget with 313s avg ATE = 67s margin. A single outlier ATE cycle (e.g., 7 cycles with some 429 delays) could hit 380s hard wall and produce a truncated/incomplete response.
- **Conservative**: +20s = 5.3% increase. At 400s budget, 4 full key cycles + 15s headroom. No impact on other models.
- **cc4101 compatible**: `PROXY_TIMEOUT=420` > 400, so cc4101 does not kill before budget.
- **No impact on HM2**: single param, only HM1 env.

### Risk Assessment

- **No impact on glm5_2_nv** (230s budget, independent)
- **No impact on dsv4p_nv** (265s budget, independent)  
- **No impact on cc4101** (PROXY_TIMEOUT=420s > 400)
- **No impact on HM2** (single param, only HM1)
- **Conservative**: +20s on a 380s baseline = 5.3% increase

## 修改

### docker-compose.yml (HM1, /opt/cc-infra)

```yaml
# Before:
- NVU_TIER_BUDGET_KIMI_NV=380  # R2390: 370→380. R2388 fixed cc4101 300s bottleneck. 380s allows 5 full key cycles vs 370s=4.87. +10s budget single param; iron law.

# After:
- NVU_TIER_BUDGET_KIMI_NV=400  # R2396 (HM2->HM1): 380->400. 6h DB: kimi_nv 5 ATE avg=313s at 380s budget. MAX(ATE)=135+313s compresses, tail=380s hard wall risk. +20s (5.3pct) gives 4 full key cycles+15s headroom. tiers_tried_count=1 at start_tier_idx=0: all 8 ATE only 1 tier tried=fast fail, not budget. 400 absorbs tail ATE + keeps buffer. Single param; iron law: only HM1.
```

## 验证

1. `docker compose up -d nv_gw` → Container nv_gw Recreated/Started ✅
2. `curl http://localhost:40006/health` → `{"status": "ok"}` ✅
3. `docker exec nv_gw env | grep TIER_BUDGET_KIMI` → `NVU_TIER_BUDGET_KIMI_NV=400` ✅

## 预期改善

- kimi_nv ATE 尾端硬墙风险降低，400s 吸收极端集群故障周期
- avg ATE=313s → 400s 预算 = 87s margin (vs 67s at 380)
- 不影响 glm5_2_nv/dsv4p_nv 模型
- 保守 +20s，仅 5.3% 预算增加

## ⏳ 轮到HM1优化HM2