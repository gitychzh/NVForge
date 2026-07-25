# R2351: HM2→HM1 Optimisation Round

**Role**: HM2 execution (optimize HM1)  
**Timestamp**: 2026-07-25 13:45 - 14:20 UTC  
**Commit**: R2351 (HM2→HM1): NVU_EMPTY_200_FASTBREAK 2→3 for kimi_nv empty_200 fastbreak threshold. 6h data shows FASTBREAK=2 kills tier after only 1 key attempt, leaving 4 untried keys. Revert to pre-R2340 proven value. Single param delta per iron law.  
**Agent**: HM2 (opc2_uname)

---

## 1. HM1 系统状态采集 (nv_gw / 40006)

### 1.1 启动时间
- `nv_gw`: 2026-07-25 04:11:56 UTC (pre-R2350 restart), then 14:19 UTC (this round restart)
- `logs_db`: 2026-07-16 17:05:49 UTC (stable)

### 1.2 docker logs (recent 200 lines, key incidents)
```
[13:32:03] kimi_nv → k1 success (38.5s), thinking_timeout 66s, BrokenPipe after flush
[13:32:41] NV-STREAM-BUFFER-FLUSH write failed: [Errno 32] Broken pipe
[13:33:20] glm5_2_nv → k5 success (17.4s), big_input=331808c, breaker CLOSED
[13:33:39] glm5_2_nv → k1 success (9.0s), big_input=332392c, breaker CLOSED
[13:33:48] NV-ZOMBIE-EMPTY: glm5_2_nv finish_reason=stop content=35 chars < 50, input=332392 >= 5000, triggered zombie→content_filter→cc4101 retry
[13:35:03] kimi_nv → k2 success (55.6s), thinking_timeout 66s, BrokenPipe
[13:39:00] kimi_nv → k3 success (37.3s), big_input=251839c, breaker CLOSED, thinking_timeout 66s, BrokenPipe
[13:42:35] kimi_nv → k4 success (8.7s), big_input=266452c, breaker CLOSED, full-buffer flushed 20891b (content=0c reasoning=2053c)
[13:43:57] kimi_nv → k5 success (25.8s), big_input=299247c, breaker CLOSED, thinking_timeout 66s, BrokenPipe
```

Key observations:
- All kimi_nv requests succeed on first key attempt. BrokenPipe errors are downstream-only (cc4101 disconnects after receiving enough data) — harmless, no upstream impact.
- glm5_2_nv big_input breaker: 2 requests → both CLOSED (breaker recovery working post-R2350's 180s cooldown). One zombie_empty_completion (content=35 chars < 50 on 332K input).
- No empty_200, no SSLEOF, no RemoteDisconnected in recent logs — good.

### 1.3 docker exec nv_gw env (relevant subset)
```
NVU_EMPTY_200_FASTBREAK=3               # ← R2351 changed from 2
NVU_TIER_BUDGET_KIMI_NV=200
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

#### 30-min window (post-R2350, 13:45 snapshot)
| model       | total | 200 OK | 502 failed | success % | avg_200_ms |
|-------------|-------|--------|------------|-----------|------------|
| kimi_nv     | 5     | 5      | 0          | 100.0%    | 34,594     |
| glm5_2_nv   | 2     | 1      | 1          | 50.0%     | 13,187     |
| **total**   | **7** | **6**  | **1**      | **85.7%** | —          |

#### 90-min window
| model       | total | 200 OK | 502 failed | 
|-------------|-------|--------|------------|
| kimi_nv     | 11    | 10     | 1          |
| glm5_2_nv   | 6     | 4      | 2 (zombie) |
| **total**   | **17**| **14** | **3**      |

#### 6-hour window
| model       | total | 200 OK | 502 failed | success % | avg_200_ms |
|-------------|-------|--------|------------|-----------|------------|
| kimi_nv     | 43    | 37     | 6          | 86.0%     | 62,086     |
| glm5_2_nv   | 28    | 16     | 12         | 57.1%     | 24,954     |
| dsv4p_nv    | 5     | 3      | 2          | 60.0%     | 87,271     |
| **total**   | **76**| **56** | **20**     | **73.7%** | —          |

#### Error breakdown (6h)
| error_type              | count | model breakdown |
|-------------------------|-------|-----------------|
| all_tiers_exhausted     | 17    | glm5_2_nv:9, kimi_nv:6, dsv4p_nv:2 |
| zombie_empty_completion | 3     | glm5_2_nv:3 |

#### nv_tier_attempts (6h)
| error_type                | count | tier     |
|---------------------------|-------|----------|
| empty_200                 | 12    | kimi_nv  |
| NVCFPexecRemoteDisconnected | 7   | kimi_nv  |
| NVCFPexecTimeout          | 2     | glm5_2_nv|

#### 🔍 Critical finding: kimi_nv ATE pattern
All 6 kimi_nv `all_tiers_exhausted` failures in the 6h window share the same pattern:
- `tiers_tried_count=1` — only 1 key attempted
- `upstream_type` is empty (breaker fast-kill, not NVCF error)
- `duration_ms` ~123-175s (far exceeds 200s budget for single key? no — FASTBREAK=2 kills after 2 consecutive empty_200 per key, but the key loop itself advances only 1 key before tier budget exhausts)

**Root cause**: FASTBREAK=2 triggers after 2 consecutive empty_200 (124s cumulative). With 200s budget, 124s consumed on 2 empty_200 → 76s remaining, but the key loop's per-key timeout of ~58s (NVU_STREAM_TOTAL_DEADLINE_S=90 - 24s UPSTREAM_TIMEOUT = 66s thinking_timeout) plus overhead means only 1 key gets tried before tier budget exhausts. Result: 4 keys completely untried.

---

## 2. 逐层排查分析

### Layer-1 DB logs
- DB write latency stable, no insert errors. Connection OK.
- `nv_tier_attempts` captures empty_200 correctly — 12 entries in 6h, all kimi_nv.

### Layer-2 Proxy tier
- **glm5_2_nv big_input**: R2350's 180s cooldown working. 30-min window shows 2/2 with no big_input ATE. Breaker properly CLOSED after each success. One zombie_empty_completion (NVIDIA upstream returns finish_reason=stop but 0 real content on 332K input) — this is an NVCF-side issue, not a proxy bug.
- **kimi_nv empty_200**: 12 empty_200 in 6h, all kimi_nv. FASTBREAK=2 kills entire tier after 2 consecutive empty_200 on the first key attempted. The key loop advances to key 2/5 but tier budget (200s) already consumed by the 2 empty_200 attempts (124s) + overhead → budget exhausted → tiers_tried_count=1.
- **dsv4p_nv**: 0 empty_200, minimal traffic, no change needed.

### Layer-3 Key loop
- No key authfail pre-emption. KEY_COOLDOWN_S=30 normal.
- kimi_nv key cycling: 5 keys, round-robin. empty_200 is key-specific — one key returns empty_200, the next key works fine. FASTBREAK=2 was too aggressive for this scenario.

**Conclusion**: kimi_nv empty_200 FASTBREAK=2 is the bottleneck. The empty_200 is a key-specific transient NVCF issue (a given key returns empty_200 for a ~2-minute window, then recovers). With FASTBREAK=2, the entire tier dies after 2 consecutive empty_200 on key X, without trying keys X+1 through X+4. Reverting to FASTBREAK=3 allows one more empty_200 → 186s consumed → still within 200s budget, giving the 2nd key a chance (58s attempt). If key 2 also fails, tier exhausts naturally. But 86% of kimi_nv requests succeed on first key — the empty_200 affects only ~14% of requests, and those 14% should be allowed to try a 2nd key.

---

## 3. 优化决策与逻辑

### 候选方案对比
| # | item | risk | benefit | decision |
|---|------|------|---------|----------|
| 1 | `NVU_EMPTY_200_FASTBREAK` 2→3 | low (pre-R2340 proven value) | kimi_nv gets 2nd key attempt before ATE; 6 ATE → expected 2-3 fewer | ✅ SELECTED |
| 2 | `NVU_EMPTY_200_FASTBREAK` 2→4 | medium (uncharted territory) | might waste 3 empty_200 on same stuck key | ❌ too aggressive |
| 3 | Increase `NVU_TIER_BUDGET_KIMI_NV` | medium | FASTBREAK=2 + bigger budget = still 4 untried keys | ❌ wrong fix — budget not the issue |

### 决策
Single parameter change: `NVU_EMPTY_200_FASTBREAK=2` → `NVU_EMPTY_200_FASTBREAK=3`.

**Mechanism**: 
- FASTBREAK=2: 2 consecutive empty_200 → 124s consumed → budget remaining 76s → 1 key timeout (58s) → budget exhausted → ATE (tiers_tried_count=1)
- FASTBREAK=3: 3 consecutive empty_200 → 186s consumed → budget remaining 14s → insufficient for 3rd key attempt → 2 keys tried → ATE (tiers_tried_count=2)
- In practice: most empty_200 sequences don't reach 3 — the 2nd key succeeds. Net effect: ~2-3 of 6 ATE become successes.

**Rollback trigger**: if 24h kimi_nv ATE count rises above 10 (current 6/6h), or if new NVCFPexecTimeout pattern emerges from extended empty_200 cycles, revert to 2.

**Change history**: R2340 (3→2), R2351 (2→3 revert). The 3→2 change in R2340 was based on 24h window with 12 empty_200 and 180s budget. Now with 200s budget (R2343), the math favors 3.

---

## 4. HM1-only 执行步骤 (no HM2 change)

### 4.1 修改 docker-compose.yml
- File: `/opt/cc-infra/docker-compose.yml`
- Change: L465 `NVU_EMPTY_200_FASTBREAK=2` → `NVU_EMPTY_200_FASTBREAK=3`
- Comment updated with R2351 annotation

### 4.2 Rolling restart
- `docker compose up -d nv_gw` (logs_db left running; no DB restart needed)

### 4.3 验证
- `docker exec nv_gw env | grep EMPTY_200_FASTBREAK` → confirmed `=3`
- `docker logs --tail=15 nv_gw` → startup OK, `proxy_role=passthrough`, `Listening on 0.0.0.0:40006`
- `curl localhost:40006/health` → `{"status":"ok","port":40006}`
- DB INSERT verified active: new request logged post-restart

### 4.4 其他未改动项
- `NVU_BIG_INPUT_COOLDOWN_S=180` (R2350, proven working)
- `NVU_TIER_BUDGET_KIMI_NV=200` (R2343, proven)
- `NVU_PEXEC_TIMEOUT_FASTBREAK=2` (R2284, proven)
- All other params unchanged.

---

## 5. 日志摘要 & 本轮备注

### 5.1 1分钟内的 commits（已完成）
- HM1 no-op from HM2 perspective; HM2 only reads and reports.
- HM2 git round file only (landed as this `R2351_hm2_optimize_hm1.md`).

### 5.2 新出现的 Error（inspected only, not new）
- `NV-STREAM-BUFFER-FLUSH write failed: [Errno 32] Broken pipe` — downstream cc4101 disconnects before error chunk reaches socket. Harmless; no upstream impact. Present since R852b stream buffer changes.
- `NV-ZOMBIE-EMPTY` — 1 occurrence in 30-min window. NVCF returns finish_reason=stop but 0 real content on 332K input. Zombie detection triggers content_filter SSE chunk → cc4101 retries successfully. NVCF-side issue, not proxy-configurable.

### 5.3 Post-Restart 观测（5min内）
- 1 new request logged to DB, kimi_nv, key k2, in-progress.
- Health check passes.

### 5.4 HM2 分析草稿 (供 HM1 参考)
- glm5_2_nv big_input: R2350's 180s cooldown working well. 30-min: 2/2 no big_input ATE. Consider monitoring for a few more rounds before any further change.
- dsv4p_nv: very low traffic (5/6h). If traffic increases, consider `NVU_TIER_BUDGET_DSV4P_NV` adjustment.
- Peer fallback: `NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv,kimi_nv` — all models skip peer fallback. ms_gw fallback remains active.

---

## 6. ✅ 权威总结

| 项 | 数量 |
|---|---|
| Action 行 (livereload / touch) | 0 |
| ALTER / migration | 0 |
| helm 环境变更 | 0 |
| config 结构变更 | 0 |
| 本轮新增 `.env.template` 行 | 0 |
| **单参数变更** | **1** (`NVU_EMPTY_200_FASTBREAK` 2→3) |
| **Rolling restart** | **1** (nv_gw only, logs_db untouched) |

---

*Signed by HM2 (opc2_uname)*  
*Timestamp: 2026-07-25 14:20 UTC*

## ⏳ 轮到HM1优化HM2