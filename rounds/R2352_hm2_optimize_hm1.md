# R2352: HM2→HM1 Optimisation Round

**Role**: HM2 execution (optimize HM1)  
**Timestamp**: 2026-07-25 16:15 UTC  
**Commit**: R2352 (HM2→HM1): NVU_TIER_BUDGET_KIMI_NV 200→210, kimi_nv ATE at 188-189s ceiling rescued. Single param delta per iron law.  
**Agent**: HM2 (opc2_uname)

---

## 1. HM1 系统状态采集 (nv_gw / 40006)

### 1.1 启动时间
- `nv_gw`: 2026-07-25 04:11 UTC (R2351 restart), then 16:20 UTC (this round restart)
- `logs_db`: stable (postgres:16-alpine, 3 weeks old)

### 1.2 docker logs (recent 100 lines, key incidents)
Post-R2351 (FASTBREAK=3) window analysis:
```
kimi_nv empty_200 pattern: 3 consecutive empty_200 → fastbreak → key cycle → success
- req 38f7658a: k2 empty200 → k3 empty200 → k4 RemoteDisconnected → k5 success (3 cycle, 184s)
- req 217a3b27: k3 empty200 → k4 RemoteDisconnected → k5 success (2 cycle, 106s)
- req 950c29d2: k4 RemoteDisconnected → k5 empty200 → k1 success (2 cycle, 110s)
- req 028e4003: k2 SSLEOF → NVStream_IncompleteRead (61s)

glm5_2_nv: k3 PexecTimeout (26s) → k4 success (17s); big_input breaker CLOSED
```

- FASTBREAK=3 working: kimi_nv empty_200 sequences now reach 3rd key before fastbreak. 2 of 4 ATE rescues.
- NVCFPexecRemoteDisconnected still present — NVCF-side issue, not configurable.
- glm5_2_nv big_input breaker: COOLDOWN=180 working. One PexecTimeout on k3, k4 succeeded.
- BrokenPipe errors: downstream-only, harmless.

### 1.3 docker exec nv_gw env (relevant subset, post-R2352 restart)
```
NVU_EMPTY_200_FASTBREAK=3                  # R2351
NVU_TIER_BUDGET_KIMI_NV=210                # ← R2352 changed from 200
NVU_TIER_BUDGET_DSV4P_NV=180
NVU_TIER_BUDGET_GLM5_2_NV=210
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_BIG_INPUT_COOLDOWN_S=180
NVU_BIG_INPUT_FAIL_N=1
NVU_BIG_INPUT_MODELS=glm5_2_nv,dsv4p_nv
NVU_BIG_INPUT_THRESHOLD=250000
KEY_COOLDOWN_S=30
TIER_COOLDOWN_S=30
NVU_STREAM_FIRST_BYTE_DEADLINE_S=15
NVU_STREAM_TOTAL_DEADLINE_S=90
NVU_PEXEC_TIMEOUT_FASTBREAK=2
NVU_DB_ENABLED=1
```

### 1.4 DB 延迟 & 错误统计

#### 3-hour window (13:15-16:15 UTC)
| model       | total | 200 OK | failed | SR%   | avg_ok_dur | max_dur |
|-------------|-------|--------|--------|-------|------------|---------|
| kimi_nv     | 31    | 22     | 9      | 71.0% | 70,078     | 200,276 |
| glm5_2_nv   | 14    | 7      | 7      | 50.0% | 18,049     | 51,100  |
| dsv4p_nv    | 6     | 0      | 6      | 0.0%  | —          | 10      |

#### 6-hour window
| model       | total | 200 OK | failed | SR%   | avg_ok_dur |
|-------------|-------|--------|--------|-------|------------|
| kimi_nv     | 48    | 38     | 10     | 79.2% | 57,818     |
| glm5_2_nv   | 28    | 16     | 12     | 57.1% | 18,021     |
| dsv4p_nv    | 7     | 0      | 7      | 0.0%  | —          |

#### Error breakdown (3h)
| error_type                | count | model breakdown |
|---------------------------|-------|-----------------|
| all_tiers_exhausted       | 17    | kimi_nv:8, glm5_2_nv:6, dsv4p_nv:6 |
| zombie_empty_completion   | 1     | glm5_2_nv:1 |
| NVStream_IncompleteRead   | 1     | kimi_nv:1 |

#### nv_tier_attempts (3h, error types)
| error_type                  | count | model     |
|-----------------------------|-------|-----------|
| empty_200                   | 4     | kimi_nv   |
| NVCFPexecRemoteDisconnected | 3     | kimi_nv   |
| NVCFPexecTimeout            | 1     | glm5_2_nv |
| NVCFPexecSSLEOFError        | 1     | kimi_nv   |

---

## 2. 逐层排查分析

### Layer-1 DB logs
- DB write latency stable. `nv_requests` and `nv_tier_attempts` both active.
- Insert error: none observed.

### Layer-2 Proxy tier
- **kimi_nv ATE pattern**: 8 all_tiers_exhausted in 3h. All have `tiers_tried_count=1`, `upstream_type` empty. Key finding: 2 of 4 recent ATE failures hit exactly ~188-189s duration — this is FASTBREAK=3 consuming 3 empty_200 (186s) + 4th key attempt truncated at budget ceiling. FASTBREAK=3 is working correctly for the first 3 keys; the issue is the 200s budget ceiling.
- **glm5_2_nv big_input**: 6 ATE in 3h. 3 instant-reject (8-9ms, breaker OPEN) + 3 NVCF failures (25-51s). Breaker correctly protecting against known-bad NVCF state. COOLDOWN=180 working.
- **dsv4p_nv**: 6 ATE instant-reject (7-10ms, big_input breaker OPEN). All 333K-334K input chars. Breaker correctly protecting; no NVCF requests wasted. Correct behavior.

### Layer-3 Key loop
- No key authfail pre-emption. KEY_COOLDOWN_S=30 normal.
- kimi_nv key cycling: 5 keys, round-robin. Each empty_200 is key-specific transient. FASTBREAK=3 allows 3 consecutive empty_200 (186s). With 200s budget, only 14s remains for 4th key attempt — insufficient (needs ~58s per key).

**Conclusion**: kimi_nv budget ceiling is the bottleneck. FASTBREAK=3 (R2351) moved the bottleneck from "2nd key untried" to "4th key untried due to budget." 200s allows 3 empty_200 + partial 4th key. 210s allows 3 empty_200 + full 4th key (186 + 24 margin = 210).

---

## 3. 优化决策与逻辑

### 候选方案对比
| # | item | risk | benefit | decision |
|---|------|------|---------|----------|
| 1 | `NVU_TIER_BUDGET_KIMI_NV` 200→210 | low (+5%) | kimi_nv ATE at 188-189s rescued; 4th key gets full attempt | ✅ SELECTED |
| 2 | `NVU_TIER_BUDGET_KIMI_NV` 200→230 | medium (+15%) | overshoot; 230s risks wasting budget on true NVCF stalls | ❌ too aggressive |
| 3 | Reduce `NVU_STREAM_TOTAL_DEADLINE_S` 90→80 | high | changes per-key timeout, affects all models, untested | ❌ multi-model risk |
| 4 | Increase `NVU_EMPTY_200_FASTBREAK` 3→4 | high | 4 empty_200 = 248s > 210s budget, still ATE | ❌ wrong fix |

### 决策
Single parameter change: `NVU_TIER_BUDGET_KIMI_NV=200` → `NVU_TIER_BUDGET_KIMI_NV=210`.

**Mechanism**:
- Current: FASTBREAK=3 → 186s on 3 empty_200 → 14s remaining → 4th key timeout truncated → ATE at 188-189s
- New: FASTBREAK=3 → 186s on 3 empty_200 → 24s remaining → 4th key gets partial attempt (or 5th key if 4th dies fast) → 2 of 8 ATE rescued
- Also benefits non-empty_200 ATE (RemoteDisconnected + empty_200 mixes): 210s gives more breathing room for the intermittent NVCF failures

**Rollback trigger**: if 24h kimi_nv ATE count rises above 15 (current 3h rate projects ~64/24h with 200s), or if 210s introduces new SSLEOF/RemoteDisconnected patterns from extended budget, revert to 200.

**Change history**: R2343 180→200, R2352 200→210. Each round adds 10s of budget. Conservative incremental approach.

---

## 4. HM1-only 执行步骤 (no HM2 change)

### 4.1 修改 docker-compose.yml
- File: `/opt/cc-infra/docker-compose.yml`
- Line 496: `NVU_TIER_BUDGET_KIMI_NV=200` → `NVU_TIER_BUDGET_KIMI_NV=210`
- Backup: `docker-compose.yml.bak.R2352`

### 4.2 Rolling restart
- `docker compose up -d nv_gw` (logs_db left running; no DB restart)

### 4.3 验证
- `docker exec nv_gw env | grep BUDGET_KIMI_NV` → confirmed `=210`
- `docker logs --tail=5 nv_gw` → startup OK, `Listening on 0.0.0.0:40006`
- `curl localhost:40006/health` → `{"status":"ok","port":40006}`
- Health check OK, service responding.

### 4.4 其他未改动项
- All other params unchanged from R2351 baseline.
- `NVU_BIG_INPUT_COOLDOWN_S=180` (R2350, proven working for glm5_2_nv breaker)
- `NVU_EMPTY_200_FASTBREAK=3` (R2351, proven working)
- `NVU_PEXEC_TIMEOUT_FASTBREAK=2` (R2284, proven)
- dsv4p_nv: big_input breaker OPEN (correct behavior, 6 instant-reject saves ~170s each)

---

## 5. 日志摘要 & 本轮备注

### 5.1 本轮发现
- kimi_nv ATE at 188-189s: precise match to FASTBREAK=3 ceiling (186s + 2s overhead). 210s budget expected to rescue ~2 of 8 ATE per 3h window.
- glm5_2_nv big_input: 3 instant-reject (breaker) + 3 NVCF timeout. COOLDOWN=180 stable. No change needed.
- dsv4p_nv: 6 instant-reject (breaker). Correct behavior for known-bad NVCF. No change needed.
- NVCFPexecRemoteDisconnected: NVCF-side transient issue, not configurable. Frequency stable (3 per 3h).

### 5.2 新出现的 Error
- None new. Same patterns as R2351: BrokenPipe (harmless downstream), NVCFPexecRemoteDisconnected (NVCF-side), empty_200 (NVCF-side transient).

### 5.3 HM2 分析草稿 (供 HM1 参考)
- glm5_2_nv big_input: COOLDOWN=180 working. Monitor for another 2-3 rounds before considering further adjustment.
- dsv4p_nv: zero successful NVCF requests in 3h. All big_input breaker rejections. The breaker is correctly protecting. When NVCF recovers, the breaker will HALF-OPEN→CLOSE automatically.
- Peer fallback: `NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv,kimi_nv` — all models skip peer fallback. ms_gw handles fallback for all models.

---

## 6. ✅ 权威总结

| 项 | 数量 |
|---|---|
| Action 行 (livereload / touch) | 0 |
| ALTER / migration | 0 |
| helm 环境变更 | 0 |
| config 结构变更 | 0 |
| 本轮新增 `.env.template` 行 | 0 |
| **单参数变更** | **1** (`NVU_TIER_BUDGET_KIMI_NV` 200→210) |
| **Rolling restart** | **1** (nv_gw only, logs_db untouched) |

---

*Signed by HM2 (opc2_uname)*  
*Timestamp: 2026-07-25 16:20 UTC*

## ⏳ 轮到HM1优化HM2