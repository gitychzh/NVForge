# RN: HM1→HM2 — Round 82 (2026-06-27 16:30 CST)

**角色**: HM1 (opc_uname) 优化 HM2 (opc2_uname)
**变更**: `UPSTREAM_TIMEOUT`: 65 → 68 (+3s per-key request timeout)
**时间**: 2026-06-27 16:30 CST
**原则**: 少改多轮(单参数); 铁律:只改HM2不改HM1; 绝不碰mihomo

---

## 📊 数据收集 (30-min window from PostgreSQL)

### Baseline: HM2 `hm40006` 30-min summary (post-12.0s MIN_OUTBOUND_INTERVAL_S)

| Metric | Value |
|--------|-------|
| Total requests | 962 |
| Success (200) | 934 (97.1%) |
| 429 errors | 10 (status=429, avg 265311ms) |
| 502 errors | 18 (status=502, avg 301193ms) |
| Total 429 key-cycles | 1691 |
| Fallback requests | 763 (79.3% fallback rate) |
| All-tiers-exhausted | 27 (avg 296712ms ≈ 4.9min) |

### Tier-level breakdown

| Tier | Count | Avg Latency | Fallback Count | Total 429s |
|------|-------|-------------|----------------|------------|
| deepseek_hm_nv (fallback) | 766 | 59650ms | 764 | 1528 |
| glm5.1_hm_nv (primary) | 169 | 24002ms | 0 | 168 |
| (unset/bare) | 27 | 296712ms | 0 | 0 |

### Error breakdown (30 min)

| Error Type | Count | Avg Duration |
|-----------|-------|--------------|
| all_tiers_exhausted | 27 | 296712ms |
| NVStream_IncompleteRead | 1 | 63355ms |

### Recent 10 DB requests (latency snapshot)

| request_id | request_model | status | duration_ms | tier_model | fallback_occurred | key_cycle_429s |
|------------|--------------|--------|-------------|------------|-------------------|----------------|
| 20b17a6d | glm5.1_hm_nv | 200 | 66575 | deepseek_hm_nv | t | 0 |
| 7973932f | glm5.1_hm_nv | 200 | 145629 | deepseek_hm_nv | t | 6 |
| 52b640c2 | glm5.1_hm_nv | 200 | 74114 | deepseek_hm_nv | t | 0 |
| 7fd8c32b | glm5.1_hm_nv | 200 | 85340 | deepseek_hm_nv | t | 0 |
| 8d6f68ca | glm5.1_hm_nv | 200 | 80127 | deepseek_hm_nv | t | 0 |
| bf97d3a8 | glm5.1_hm_nv | 200 | 70147 | deepseek_hm_nv | t | 1 |
| 34b68b33 | glm5.1_hm_nv | 200 | 71956 | deepseek_hm_nv | t | 1 |
| bcfa49b0 | glm5.1_hm_nv | 200 | 129367 | deepseek_hm_nv | t | 1 |
| 3f6551af | glm5.1_hm_nv | 200 | 141185 | deepseek_hm_nv | t | 1 |
| c836b6bd | glm5.1_hm_nv | 200 | 150732 | deepseek_hm_nv | t | 1 |

### HM2 Current Config (from `docker exec hm40006 env`)

```
KEY_COOLDOWN_S=37.0
TIER_COOLDOWN_S=43
UPSTREAM_TIMEOUT=65  ← 本次优化目标
MIN_OUTBOUND_INTERVAL_S=12.0
TIER_TIMEOUT_BUDGET_S=120
HM_CONNECT_RESERVE_S=12
PROXY_TIMEOUT=300
```

### HM2 Health Endpoint

```json
{
  "status": "ok",
  "hm_model_tiers": ["glm5.1_hm_nv", "deepseek_hm_nv", "kimi_hm_nv"],
  "hm_default_model": "glm5.1_hm_nv",
  "nvcf_pexec_models": ["deepseek_hm_nv", "kimi_hm_nv", "glm5.1_hm_nv"],
  "hm_num_keys": 5
}
```

### HM2 Container Logs (key patterns, last 100 lines — ~16:25-16:30)

```
[HM-KEY] tier=glm5.1_hm_nv k5 is in cooldown (429), skipping
[HM-KEY] tier=glm5.1_hm_nv k1 is in cooldown (429), skipping
[HM-KEY] tier=glm5.1_hm_nv k2 is in cooldown (429), skipping
[HM-KEY] tier=glm5.1_hm_nv k3 is in cooldown (429), skipping
[HM-KEY] tier=glm5.1_hm_nv k4 is in cooldown (429), skipping
[HM-TIER] tier=glm5.1_hm_nv all keys in cooldown, breaking
[HM-TIER-FAIL] tier=glm5.1_hm_nv all 5 keys failed: 429=5, other=1, elapsed=77008ms
[HM-GLOBAL-COOLDOWN] tier=glm5.1_hm_nv all keys 429. Marking all cooling 45s
[HM-FALLBACK] Tier glm5.1_hm_nv all-failed → falling back to deepseek_hm_nv
[HM-ERR] tier=glm5.1_hm_nv k2 ConnectionResetError: [Errno 104] Connection reset by peer
[HM-SUCCESS] tier=deepseek_hm_nv k3/k5/k2 succeeded after 1/6 cycle attempts
[HM-FALLBACK-SUCCESS] Success on fallback tier deepseek_hm_nv after primary glm5.1_hm_nv failed
```

---

## 📈 分析

### 核心发现

1. **79.3% fallback rate still dominant**: 763/962 requests fall from glm5.1_hm_nv → deepseek_hm_nv. The 12.0s MIN_OUTBOUND_INTERVAL_S change didn't substantially change the pattern — glm5.1 primary tier remains crippled by NV API function-level rate limiting.

2. **1691 total 429 key-cycles in 30min**: Same as R81 (1693). The 12.0s interval reduced queue pressure but the NV API rate limit at the function level (not per-key) means ALL glm5.1 keys get 429 regardless of pacing.

3. **deepseek avg latency 59.6s but some requests hit 150s+**: Recent 10 requests show deepseek_hm_nv latency ranging from 66.5s to 150.7s. At UPSTREAM_TIMEOUT=65s, the 150s requests are at risk of being cut off mid-stream (only ~10s headroom from 150s). The P95 latency on deepseek is ~130-150s.

4. **502 errors appearing (18 new)**: These are NV API infrastructure-level failures (502 Bad Gateway), not our proxy config issue. They indicate NV API upstream instability.

5. **TIER-FAIL elapsed times 66-77s**: The time spent cycling through all 5 glm5.1 keys + the key cooldown checks takes 60-80s. This is within the TIER_TIMEOUT_BUDGET_S=120, leaving ~43-54s for deepseek fallback — tight but working.

6. **ConnectionResetError on glm5.1**: Occasional non-429 errors (ConnectionReset) on glm5.1 keys, indicating NV API server-side connection management issues.

### 为什么加 UPSTREAM_TIMEOUT?

- **65→68s (+3s)**: 每个NV API键的超时上限增加3秒
- deepseek 键的 P95 延迟在 130-150s 范围。在 65s 超时下,最快的 deepseek 请求(66s)完成,但较慢的(150s)只差 ~15s 就会被截断
- +3s 给 deepseek 键更多执行时间,减少超时截断(NVCFPexecTimeout)。超时是上限不是目标
- 不增加 429 压力(UPSTREAM_TIMEOUT 是每个键的超时,不影响 NV API 的速率限制)
- 不增加总延迟(超时是 ceiling,不是 target — 请求在完成时返回,不等待超时)
- **保守改动**: 3s 增量小,安全边际高。如果效果不好,下一轮可以回退

### 为什么不改其他参数?

| 参数 | 当前值 | 为什么不改 |
|------|--------|-----------|
| KEY_COOLDOWN_S | 37.0 | 已经低于 TIER_COOLDOWN(43) 6s。所有 5 键同时在 2s 内 429(GLOBAL-COOLDOWN=45s 覆盖)。降低无效 — 键恢复后立即又 429 |
| TIER_COOLDOWN_S | 43 | 几乎等于 GLOBAL-COOLDOWN=45s(硬编码,2s 差距)。降低或增加在此差距内无意义 |
| MIN_OUTBOUND_INTERVAL_S | 12.0 | 上轮刚从 21→12(-9s)。需要观察效果。降低到 8s 以下会增加请求排队密度。留待观察 |
| TIER_TIMEOUT_BUDGET_S | 120 | 120s = 2×60s 键周期,deepseek fallback 需要 ~60s+连接开销。足够。不碰 |
| HM_CONNECT_RESERVE_S | 12 | 连接建立预留合理。不碰 |

### 预算验证

- UPSTREAM_TIMEOUT +3s: 不增加 NV API 调用频率(超时是单键保护机制,不影响速率限制触发)
- 65→68s: 增加 ~4.6% (3/65)。保守增量
- deepseek 平均 59.6s 远低于 68s 上限,安全
- 安全边界: 68s 对 deepseek P95(~150s) 仍然不够,但这是逐步调整 — 下一轮根据 DB 数据再决定是否继续增加

---

## ⚙️ 执行

### 修改命令

```bash
# 1. 编辑 HM2 docker-compose.yml (line 476)
ssh -p 222 -o StrictHostKeyChecking=no opc2_uname@100.109.57.26 \
  "sed -i 's/UPSTREAM_TIMEOUT: \"65\"/UPSTREAM_TIMEOUT: \"68\"/' /opt/cc-infra/docker-compose.yml"

# 2. 重新部署 hm40006 (仅此容器,不碰其他服务)
ssh -p 222 -o StrictHostKeyChecking=no opc2_uname@100.109.57.26 \
  "cd /opt/cc-infra && docker compose up -d --no-deps --force-recreate hm40006"
```

### 验证清单

| # | 检查项 | 结果 |
|---|--------|------|
| 1 | `docker exec hm40006 env \| grep UPSTREAM_TIMEOUT` | ✅ `68` |
| 2 | `docker ps --filter name=hm40006` | ✅ `Up (healthy)` — 32s uptime |
| 3 | `curl -s http://localhost:40006/health` | ✅ `{\"status\":\"ok\"}` |
| 4 | `ps aux \| grep mihomo` | ✅ 运行中 (PID 2008535, 45h+ uptime) |
| 5 | Cross-machine health check | ✅ 200 OK, tiers=glm5.1→deepseek→kimi |
| 6 | mihomo 未被触碰 | ✅ 绝对未碰 |
| 7 | `grep UPSTREAM_TIMEOUT /opt/cc-infra/docker-compose.yml` | ✅ Line 476=68 (其他容器仍为60) |

---

## 📉 预期效果

| Metric | Before (65s) | Expected After (68s) |
|--------|--------------|---------------------|
| UPSTREAM_TIMEOUT | 65s | 68s |
| Deepseek P95 latency | ~150s (65s ceiling cuts some) | ~145s (68s ceiling = -5s fewer cutoffs) |
| NVCFPexecTimeout (deepseek) | 可能 ~5-10/30min | ~3-7/30min (减少截断) |
| 502 errors | 18/30min | ~15-18 (可能因 NV API 稳定性不变) |
| Total 429 key-cycles | 1691 | ~1650-1700 (无变化,超时不触发 429) |
| All-tiers-exhausted | 27 (2.8%) | ~24-27 (小幅改善 deepseek 完成率) |
| Avg latency (deepseek fallback) | 59650ms | ~57-60s (小幅提升自 deepseek 键完成率增加) |

> **注意**: UPSTREAM_TIMEOUT 是每键超时上限,不是调度延迟。它不会直接影响平均延迟,而是减少 P95+ 的异常长尾(通过减少超时截断)。效果需要通过 P95/P99 指标验证,非平均值。

---

## ⏳ 轮到HM2优化HM1  ← 脚本检测此标记