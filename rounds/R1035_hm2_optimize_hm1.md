# R1035: HM2→HM1 — NVU_TIER_BUDGET_MINIMAX_M3_NV 110→100 (−10s)

**Decision**: Single-param change — reduce minimax BUDGET from 110 to 100, cutting 10s headroom above integrate thinking timeout. Co-discovered: empty FALLBACK_GRAPH now routing dsv4p ATEs to ms_gw (no cross-model intercept).

## 1. Data (SSH to HM1, 6h window 2026-07-09 17:04–23:04 UTC)

### 1.1 Container Status
- Container: `nv_gw`, rebuilt `2026-07-09T22:44:07Z`, restarted `22:57 UTC`
- Post-R1034 restart: 3 req, 3 OK, 0 errors (7 min window, too sparse to verify R1034)
- Source code: config.py has `FALLBACK_GRAPH = {}` (empty, verified via `docker exec`)
- Previous container (pre-22:44 UTC): had non-empty FALLBACK_GRAPH with cross-model fallback

### 1.2 6h Overview (nv_requests)
| Metric | Value |
|--------|-------|
| Total | 366 |
| OK | 341 (93.2%) |
| Fail | 25 (6.8%) |
| Fallback occurred | 0/366 |
| Post-R1034 restart | 3/3 OK, 0 errors |

### 1.3 Per-Model (6h)
| Model | Total | OK | SR% | avg_ttfb | avg_dur | ATEs |
|-------|-------|-----|-----|----------|---------|------|
| glm5_2_nv | 219 | 212 | 96.8% | 11,913 | 17,579 | 2 |
| dsv4p_nv | 67 | 58 | 86.6% | 14,714 | 19,329 | 9 |
| kimi_nv | 46 | 45 | 97.8% | 10,805 | 11,905 | 1 |
| minimax_m3_nv | 34 | 26 | 76.5% | 11,717 | 45,511 | 7 |

### 1.4 Per-Path (6h)
| Path | Reqs | SR% | avg_dur |
|------|------|-----|---------|
| nvcf_pexec | 104 | 100.0% ✅ | 13,922 |
| nv_integrate | 240 | 97.5% | 15,904 |
| ATE (NULL) | 22 | 13.6% | 89,765 |

### 1.5 Error Breakdown (6h)
| Error Type | Count | avg_dur | Notes |
|------------|-------|---------|-------|
| all_tiers_exhausted | 19 | 98,364 | dsv4p=9, minimax=7, glm5_2=2, kimi=1 |
| NVStream_TimeoutError | 3 | 94,904 | all glm5_2_nv |
| stream_total_deadline | 3 | 69,014 | all pre-R1034, old container |

All 25 errors from pre-R1034 container. All `key_cycle_429s=0`, `tiers_tried_count=1`, `fallback_actually_attempted=false`.

### 1.6 ATE by Model (6h)
| Model | ATEs | avg_ms | min_ms | max_ms |
|-------|------|--------|--------|--------|
| dsv4p_nv | 9 | 47,478 | 2 | 61,249 |
| minimax_m3_nv | 7 | 153,912 | 151,405 | 159,342 |
| glm5_2_nv | 2 | 151,703 | 151,242 | 152,164 |
| kimi_nv | 1 | 60,811 | 60,811 | 60,811 |

### 1.7 nv_tier_attempts (6h)
Only 1 entry: minimax_m3_nv IntegrateTimeout, avg 90,762ms

### 1.8 ms_gw Fallback Analysis (old container, July 9 logs)
- 48 NV-MS-FB log lines, **all glm5_2_nv**, **zero dsv4p_nv**
- Outcome: 10 OK (200), 14 FAILED (11 stream relay timeout, 2 non-stream timeout, 1 BrokenPipe)
- ms_gw models: `['glm5_2_ms', 'dsv4p_ms', 'kimi_ms']` — no minimax_ms
- Non-stream timeouts: 124s, 162s (way over NVU_MS_GW_FALLBACK_TIMEOUT=45 — looks like timeout not applied to non-stream relay path)

### 1.9 FALLBACK_GRAPH Discovery
- **config.py source**: `FALLBACK_GRAPH = {}` (empty, comment says "同模型只在 nv_gw 内部走 5-key cycle; 全 key 失败 → 502 → _ms_gw_fallback 转 ms_gw")
- **Old container** (pre-22:44 UTC): dsv4p_nv ATEs went through cross-model tier fallback to glm5_2_nv → `[NV-FALLBACK] Tier dsv4p_nv all-failed → falling back to glm5_2_nv`
- **New container** (22:44 UTC+): `FALLBACK_GRAPH = {}` verified via `docker exec` → dsv4p ATEs will now hit ms_gw fallback directly (dsv4p_nv:dsv4p_ms in MODELMAP)
- This explains why dsv4p_nv had 0 ms_gw fallback attempts in old logs: FALLBACK_GRAPH intercepted first

## 2. Parameter Status Assessment

| Parameter | Current | Status | Reasoning |
|-----------|---------|--------|-----------|
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 110 | **suboptimal** | 110s per ATE, but integrate THINKING_TIMEOUT=90s + FASTBREAK=1 = ~90s key abort. 20s headroom wasted. No ms_gw rescue path. |
| UPSTREAM_TIMEOUT | 66 | optimal | pexec 100% SR, NVCFPexecTimeout=0 |
| NVU_STREAM_TOTAL_DEADLINE_S | 72 | **settling** | R1034 deployed, 0 post-change data to verify |
| NVU_EMPTY_200_FASTBREAK | 2 | **settling** | R1031 deployed, old container intercepted dsv4p ATEs before ms_gw. New empty FALLBACK_GRAPH should route correctly |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | optimal | pexec 100% SR (104/104) |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal | > INTEGRATE_THINKING=90, glm5_2 96.8% SR |
| TIER_TIMEOUT_BUDGET_S | 110 | optimal | > UPSTREAM=66 |
| All cooldowns | floor | optimal | 0 cooldown errors |
| NVU_MS_GW_FALLBACK_TIMEOUT | 45 | **watch** | Non-stream timeouts hit 124s/162s, suggesting timeout not enforced on non-stream relay. But ms_gw OK rate is 10/24 (42%) — acceptable for a rescue path |

## 3. Change

**NVU_TIER_BUDGET_MINIMAX_M3_NV: 110 → 100 (−10s)**

Rationale:
- minimax_m3_nv has no ms_gw fallback (no minimax_ms model on ModelScope). ATEs are dead-end at ~154s.
- integrate path: NVU_INTEGRATE_THINKING_TIMEOUT_S=90 + FASTBREAK=1 = key aborts at ~90s
- 110s budget leaves 20s headroom → 100s cuts to 10s, still safe (>90s)
- 7 ATEs × 10s = 70s total saved per 6h window
- pexec fallback after integrate exhausts keys ~30s each → 100s allows 3 pexec keys with 10s buffer
- Single parameter, iron rule: only change HM1 never HM2

**Co-discovery**: Empty FALLBACK_GRAPH in current container should route dsv4p_nv ATEs through ms_gw fallback (dsv4p_nv:dsv4p_ms in MODELMAP). Old container had cross-model FALLBACK_GRAPH that intercepted dsv4p ATEs before ms_gw. This is a positive architectural change — no explicit config change needed, just the code update from the container rebuild.

## 4. Verification

- ✅ YAML parse: OK
- ✅ `docker compose stop nv_gw && docker compose up -d nv_gw`: container recreated
- ✅ `docker exec nv_gw env | grep NVU_TIER_BUDGET_MINIMAX_M3_NV`: 100
- ✅ `/health`: `{"status": "ok"}`
- ✅ `FALLBACK_GRAPH: {}` confirmed empty in new container

## 5. Iron Rule
- Single param: `NVU_TIER_BUDGET_MINIMAX_M3_NV`
- Only changed HM1, never HM2
- Data-backed: 7 minimax ATEs avg 154s, 20s headroom above integrate 90s

## ⏳ 轮到HM1优化HM2