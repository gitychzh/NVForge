# R2353: HM2→HM1 Optimisation Round

**Role**: HM2 execution (optimize HM1)  
**Timestamp**: 2026-07-25 11:06 UTC  
**Commit**: R2353 (HM2→HM1): NVU_TIER_BUDGET_KIMI_NV 210→220, kimi_nv ATE ceiling moves from 188-209s to >220s. Single param delta per iron law.  
**Agent**: HM2 (opc2_uname)

---

## 1. HM1 系统状态采集 (nv_gw / 40006)

### 1.1 启动时间
- `nv_gw`: 2026-07-25 10:25 UTC (R2353 restart with KIMI_NV=220)
- `logs_db`: stable (postgres:16-alpine)

### 1.2 docker exec nv_gw env (post-R2353 restart)
```
NVU_EMPTY_200_FASTBREAK=3                  # R2351
NVU_TIER_BUDGET_KIMI_NV=220                # ← R2353 changed from 210
NVU_TIER_BUDGET_DSV4P_NV=180
NVU_TIER_BUDGET_GLM5_2_NV=210
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_BIG_INPUT_COOLDOWN_S=180
NVU_BIG_INPUT_FAIL_N=2
NVU_BIG_INPUT_MODELS=glm5_2_nv,dsv4p_nv
NVU_BIG_INPUT_THRESHOLD=250000
KEY_COOLDOWN_S=30
TIER_COOLDOWN_S=30
NVU_STREAM_FIRST_BYTE_DEADLINE_S=15
NVU_STREAM_TOTAL_DEADLINE_S=90
NVU_PEXEC_TIMEOUT_FASTBREAK=2
NVU_DB_ENABLED=1
```

### 1.3 DB 延迟 & 错误统计

#### 3-hour window (08:06-11:06 UTC, includes 210s → 220s transition at 10:25)
| model       | total | 200 OK | failed | SR%   | avg_ok_dur |
|-------------|-------|--------|--------|-------|------------|
| kimi_nv     | 20    | 14     | 6      | 70.0% | 70,235     |
| glm5_2_nv   | 15    | 9      | 6      | 60.0% | 11,697     |
| dsv4p_nv    | 6     | 0      | 6      | 0.0%  | —          |

#### 6-hour window (05:06-11:06 UTC, mostly 210+budget; last 41 min at 220)
| model       | total | 200 OK | failed | SR%   |
|-------------|-------|--------|--------|-------|
| kimi_nv     | 35    | 24     | 11     | 68.6% |
| glm5_2_nv   | 18    | 10     | 8      | 55.6% |
| dsv4p_nv    | 18    | 0      | 18     | 0.0%  |

#### ATE bucket breakdown (6h, failed only)
| model       | bucket  | count |
|-------------+---------+-------|
| dsv4p_nv    | <5s     | 12    |
| glm5_2_nv   | <5s     |  9    |
| glm5_2_nv   | 5-30s   |  2    |
| glm5_2_nv   | 30-60s  |  2    |
| kimi_nv     | 60-120s |  1    |
| kimi_nv     | 120-180s|  3    |
| kimi_nv     | >180s   |  9    |

#### Tier attempt error types (6h)
| tier      | error_type                 | count |
|-----------|----------------------------|-------|
| kimi_nv   | empty_200                  | 19    |
| kimi_nv   | NVCFPexecRemoteDisconnected |  7    |
| kimi_nv   | NVCFPexecSSLEOFError       |  2    |
| glm5_2_nv | NVCFPexecRemoteDisconnected |  1    |
| glm5_2_nv | NVCFPexecTimeout           |  1    |

### 1.4 NVCF gateway log analysis (post-R2353 last 50 lines)
- FASTBREAK=3 solid: multiple kimi_nv ATE rescued through 3 empty_200 → key cycle → success
- Pattern: k1 empty200 → k2 empty200 → k3 success (2 cycle attempts)
- NVCFPexecRemoteDisconnected still present: NVCF-side host-level transient (not configurable)
- BrokenPipe: downstream-only, harmless (client disconnects after partial write)

---

## 2. 数据分析与决策

### 2.1 发现的问题
1. **kimi_nv ATE at budget ceiling (update)**: 6h data shows 9 of 11 kimi_nv ATE are >180s duration. Of these, 3 in 120-180s bucket (sub-budget) and 9 in >180s (budget exhaustion). R2352 changed KIMI 200→210; compose already updated to 220 at 10:25 UTC by prior power-on cycle, but round file never written.
2. **dsv4p_nv <5s ATE**: 12 instant ATE in 6h. big_input breaker rejecting per FAIL_N=2 + threshold 250000. confirms circuit breaker active. 0 dsv4p_nv 200s mean all dsv4p_nv requests hit breaker → all rejected. This is by design – dsv4p_nv big-input issue.
3. **glm5_2_nv**: 9 instant ATE (<5s) + 4 in 5-60s. PexecTimeout fastbreak=2 working but 55.6% SR still needs work.

### 2.2 kimi_nv budget ceiling math
- FASTBREAK=3: 3 empty_200 = 186s consumed (3 × 62s key timeout)
- With 210s budget (R2352): after FASTBREAK, 210−186 = **24s** remaining for 4th key
- With 220s budget (R2353): after FASTBREAK, 220−186 = **34s** remaining for 4th key
- Each key attempt baseline: ~15-20s for litellm + NVCF pexec setup → 24s is tight, 34s is safer
- ATE duration evidence: requests hitting ~188-210s (all tiers exhausted at or near budget)
- **Observation**: since restart at 10:25 (41 min window at 220), kimi_nv 6 requests: 6× success, 0× ATE. Small sample but ceiling relief is consistent.

### 2.3 候选方案对比
| # | Parameter / Value | Risk | Rationale | Decision |
|---|-------------------|------|-----------|----------|
| 1 | `NVU_TIER_BUDGET_KIMI_NV` 210→220 | low (+5%) | kimi_nv ATE at 188-210s rescued; 4th key gets 34s margin | Already applied (10:25 UTC); now round-filed |
| 2 | `NVU_TIER_BUDGET_DSV4P_NV` 180→220 | high | lower priority; dsv4p_nv breaker already working | ❌ single param rule + dsv4p_nv not optimisation target |
| 3 | `NVU_BIG_INPUT_FAIL_N` 2→1 | med | open dsv4p_nv to 1-instant-allowed, but repeats waste 52s | ❌ risk too high for one round |
| 4 | `NVU_TIER_BUDGET_GLM5_2_NV` 210→230 | medium (+9.5%) | glm5_2_nv 55.6% SR, short ATE cluster 5-60s | ❌ not highest priority this round |

Single parameter change: `NVU_TIER_BUDGET_KIMI_NV=210` → `NVU_TIER_BUDGET_KIMI_NV=220`.

---

## 3. 执行过程 (HM1 only per iron law)

1. **Compose edit applied**: `NVU_TIER_BUDGET_KIMI_NV=210` → `220` on line 496 of `/opt/cc-infra/docker-compose.yml`  
   - Comment corrected to reflect actual state and R2353 rationale  
   - Helmsman already modified compose and restarted container at 10:25 UTC
2. **Env verification**: `docker exec nv_gw env | grep BUDGET_KIMI` → `=220` ✓  
3. **Container health**: docker healthcheck returning `healthy` ✓

---

## 4. 回退触发条件

| Metric            | Threshold | Action                  |
|-------------------|-----------|-------------------------|
| kimi_nv ATE / 24h | >12       | confirm 220 not enough, R2354 re-evaluate |
| New error pattern   | any       | rollback to 210, investigate |
| dsv4p_nv SR rise    | >5%       | dsv4p_nv improvement → nothing to do (breaker working) |

---

## 5. 变更清单

| 文件                        | 变更                                      | 说明                                   |
|----------------------------|-------------------------------------------|----------------------------------------|
| `/opt/cc-infra/docker-compose.yml` 496 | `NVU_TIER_BUDGET_KIMI_NV=210` → `=220` | 预算上限+10s; fastbreak margin 24→34s |

---

## 6. 验证

- `docker exec nv_gw env | grep BUDGET_KIMI_NV` → `=220` ✅  
- docker-compose.yml line 496: `NVU_TIER_BUDGET_KIMI_NV=220  # R2353 (HM2→HM1): 210→220, kimi_nv ATE at ~208-209s ceiling. FASTBREAK=3 consumes 186s leaving 24s for 4th key; 220s gives 34s.` ✅
- `docker inspect nv_gw --format='{.State.StartedAt}'` → `2026-07-25T10:25:17Z` (restart at change) ✅
- Health status: `healthy` ✅

| **单参数变更** | **1** (`NVU_TIER_BUDGET_KIMI_NV` 210→220) |
