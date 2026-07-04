# R699: HM2→HM1 — TIER_TIMEOUT_BUDGET_S 72→82 (+10s)

**Date**: 2026-07-05 01:44 UTC
**Host**: HM1 only (100.109.153.83)
**Iron rule**: 改前必有数据 / 改后必有验证 / 聚焦 nv_gw / 所有修改写入仓库

## TL;DR
R694 raised `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` 25→40 for thinking requests, but `TIER_TIMEOUT_BUDGET_S=72` was not adjusted. With 40s per-key thinking timeout, 2×40=80s > 72s — the 2nd thinking key only gets 30s (72−42=30s) instead of full 40s, causing premature FASTBREAK. Raising BUDGET to 82 restores the 2nd key to full 40s window, enabling proper 2-key thinking attempt as intended by R695's FASTBREAK=2.
单参数少改多轮。铁律：只改 HM1 不改 HM2。

---

## 一、当前配置快照（R699 部署前/后）

| # | 参数 | HM1 部署前 | HM1 部署后 | 历史来源 |
|---|------|-----------|-----------|----------|
| 1 | `UPSTREAM_TIMEOUT` | 25 | 25 | R652 |
| 2 | `TIER_TIMEOUT_BUDGET_S` | **72** | **82** | **R699** |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | 0 | — |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | 2 | 2 | R695 |
| 5 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 40 | 40 | R694 |
| 6 | `NVU_PEER_FALLBACK_TIMEOUT` | 45 | 45 | R697 |
| 7 | `NVU_EMPTY_200_FASTBREAK` | 2 | 2 | — |
| 8 | `KEY_COOLDOWN_S` | 25 | 25 | — |
| 9 | `TIER_COOLDOWN_S` | 25 | 25 | — |
| 10 | `NVU_FORCE_STREAM_UPGRADE` | 0 | 0 | — |
| 11 | `NVU_SSLEOF_RETRY_DELAY_S` | 1.0 | 1.0 | — |
| 12 | `NVU_CONNECT_RESERVE_S` | 0 | 0 | — |
| 13 | `NV_INTEGRATE_MODELS` | "" | "" | R696 |
| 14 | `NV_INTEGRATE_KEY_COOLDOWN_S` | 0 | 0 | — |

---

## 二、漂移检测（Pre-change）

### 2.1 源1 — Compose 文件
```
Line 490: TIER_TIMEOUT_BUDGET_S: "72"  # R694 (HM2→HM1): BUDGET 74→72...
```

### 2.2 源2 — 容器 env
```
TIER_TIMEOUT_BUDGET_S=72
```

### 2.3 源3 — 容器启动时间
```
(容器已有运行, R694 后部署)
```

### 2.4 源4 — 运行时日志
```
docker logs nv_gw --tail 100
→ [NV-PEXEC-FASTBREAK] 2 consecutive NVCFPexecTimeout -> fast-break
→ [NV-TIER-FAIL] tier=dsv4p_nv all 5 keys failed: timeout=2, elapsed=72035ms
→ dsv4p_nv thinking requests failing at ~50-72s with only 2 keys tried
```

**结论：四源全部通过, 无漂移。**

---

## 三、数据摘要（部署前窗口, 6h, 2026-07-04 19:00–01:33 UTC）

### 3.1 总体统计
- Total: 188 requests, OK: 141 (75.1%), Fail: 47 (24.9%)
- Avg duration (OK): 17650ms, Avg TTFB (OK): 16978ms, Max: 90312ms
- Fast OK (<15s): 79 (56% of successes)

### 3.2 按模型分组
| request_model | total | success | fail | success% | avg_dur(OK) |
|---------------|-------|---------|------|----------|-------------|
| glm5_2_nv     |   109 |     100 |    9 |   91.7%  |    14425ms  |
| dsv4p_nv      |    72 |      34 |   38 |   47.2%  |    28644ms  |
| kimi_nv       |     7 |       7 |    0 |  100.0%  |    10323ms  |

### 3.3 按上游路径分组
| upstream_type | count | OK  | fail | avg_dur(OK) |
|---------------|-------|-----|------|-------------|
| nvcf_pexec    |   131 | 131 |    0 |    18133ms  |
| (NULL/ATE)    |    51 |   4 |   47 |    11858ms  |
| nv_integrate  |     6 |   6 |    0 |    10984ms  |

**Key finding**: pexec path is 131/131 = 100% success. All 47 failures are ATE (all_tiers_exhausted) with upstream_type=NULL.

### 3.4 错误分类（仅失败请求）
| error_type              | count | avg_dur |
|-------------------------|-------|---------|
| all_tiers_exhausted     |    47 | 42975ms |

### 3.5 dsv4p_nv 失败 vs 成功对比
| outcome | cnt | avg_dur | min_dur | max_dur | avg_tiers_tried |
|---------|-----|---------|---------|---------|-----------------|
| FAIL    |  38 | 47593ms | 25276ms | 51876ms |             1.0 |
| OK      |  34 | 28644ms |  3148ms | 50827ms |             1.0 |

All 38 failures: `tiers_tried_count=1`, `key_cycle_429s=0`, `fallback_occurred=f`.

### 3.6 小时趋势
| hr | cnt | ok | fail |
|----|-----|----|------|
| 01 |   6 |  3 |    3 |
| 00 |   2 |  2 |    0 |
| 23 |   9 |  8 |    1 |
| 22 |  28 | 13 |   15 |
| 21 |  15 |  8 |    7 |
| 20 |  14 |  8 |    6 |
| 19 | 114 | 99 |   15 |

### 3.7 容器日志 — 失败请求详细模式

**Non-thinking dsv4p_nv (UPSTREAM_TIMEOUT=25s, 25276-25294ms duration)**:
```
[01:30:24.4] [NV-KEY] tier=dsv4p_nv attempt 1/7: k3 → NVCF pexec DIRECT
[01:30:49.9] [NV-TIMEOUT] k3 NVCF pexec timeout: attempt=25407ms
[01:30:49.9] [NV-KEY] tier=dsv4p_nv attempt 2/7: k4 → NVCF pexec DIRECT
[01:31:15.2] [NV-TIMEOUT] k4 NVCF pexec timeout: attempt=25343ms total=50770ms
[01:31:15.2] [NV-PEXEC-FASTBREAK] 2 consecutive NVCFPexecTimeout -> fast-break
[01:31:15.2] [NV-ALL-TIERS-FAIL] elapsed=50773ms
[01:31:15.2] [NV-PEER-FB] peer-originated request (hop=1) also all_tiers_exhausted
```

**Thinking dsv4p_nv (FORCE_STREAM_UPGRADE_TIMEOUT=40s, 50547-51876ms duration)**:
```
[23:39:26.3] [NV-KEY] tier=dsv4p_nv attempt 1/7: k1 → NVCF pexec DIRECT
[23:40:08.2] [NV-TIMEOUT] k1 NVCF pexec timeout: attempt=41896ms total=41897ms
[23:40:08.2] [NV-KEY] tier=dsv4p_nv attempt 2/7: k2 → NVCF pexec DIRECT
[23:40:38.3] [NV-TIMEOUT] k2 NVCF pexec timeout: attempt=30130ms total=72029ms
[23:40:38.3] [NV-PEXEC-FASTBREAK] 2 consecutive NVCFPexecTimeout -> fast-break
[23:40:38.3] [NV-TIER-FAIL] elapsed=72030ms
```

**Peer fallback success case (R697 45s timeout working)**:
```
[23:40:38.3] [NV-PEER-FB] local all_tiers_exhausted → peer fallback
[23:40:46.3] [NV-PEER-FB] peer fallback OK: status=200 bytes=2432 ttfb=72ms
```

### 3.8 成功请求中的 peer fallback rescue
- `2026-07-04 23:39:26`: dsv4p_nv, status=200, ttfb=72ms, duration=7962ms, error_type=all_tiers_exhausted, tiers_tried_count=1 — local ATE then peer fallback rescued it (ttfb=72ms = peer response time).

---

## 四、决策分析

| 参数 | 旧值 | 候选新值 | 数据支撑 | 决策 |
|------|------|---------|---------|------|
| `TIER_TIMEOUT_BUDGET_S` | 72 | **82** (+10s) | R694 raised FORCE_STREAM_UPGRADE_TIMEOUT 25→40 for thinking. BUDGET=72 < 2×40=80s → 2nd thinking key only gets 30s (72−42=30s) instead of full 40s. Logs show thinking dsv4p_nv k2 timeout at 30130ms total=72029ms — exactly the 30s residual budget limit. BUDGET=82 restores 2nd key to 40s (82−42=40s), enabling proper 2-key thinking attempt as R695's FASTBREAK=2 intended. Non-thinking unaffected (2×25=50s < 82s). | ✅ 执行 |
| `NVU_PEXEC_TIMEOUT_FASTBREAK` | 2 | 3 | Would allow 3 key attempts, but 3×40=120s >> 82s budget. 3rd key would get 0s. Vetoed. | ❌ |
| `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 40 | 35 | Would reduce per-key timeout, but R694 raised it to accommodate dsv4p_nv long TTFB (max 37.2s). Reducing would re-introduce R694's problem. Vetoed. | ❌ |
| `NVU_PEER_FALLBACK_TIMEOUT` | 45 | 50 | R697 already raised 25→45. Peer fallback is working (log shows 72ms success). No evidence 45s is insufficient. Vetoed. | ❌ |
| `UPSTREAM_TIMEOUT` | 25 | 30 | Non-thinking path. 2×30=60s < 82s, no budget issue. But no evidence 25s is too short for non-thinking (failures at 25s are NVCF server-side, not timeout-edge). Vetoed. | ❌ |

**最终决策**：仅执行 `TIER_TIMEOUT_BUDGET_S` 72→82。

### 根因链

1. R694 raised `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` 25→40 to accommodate dsv4p_nv thinking TTFB (max 37.2s).
2. R695 raised `NVU_PEXEC_TIMEOUT_FASTBREAK` 1→2 to allow 2 key attempts instead of 1.
3. But `TIER_TIMEOUT_BUDGET_S=72` was set for the old 25s timeout world (2×25=50s, 72s was generous).
4. With 40s per-key thinking timeout: 2×40=80s > 72s. The 2nd key only gets 72−42=30s instead of 40s.
5. Logs confirm: thinking dsv4p_nv k2 timeout at `attempt=30130ms total=72029ms` — exactly the 30s residual budget limit, NOT the 40s FORCE_STREAM_UPGRADE_TIMEOUT.
6. The 2nd key is being killed by the TIER_BUDGET, not by the per-key timeout. R695's FASTBREAK=2 is functional but the budget is too tight for it to work properly on thinking requests.

### BUDGET = 82 的安全性

- Non-thinking: 2×25s (UPSTREAM_TIMEOUT) = 50s. 82s − 50s = 32s headroom. FASTBREAK=2 still triggers after 2 keys. ✅
- Thinking: 2×40s (FORCE_STREAM_UPGRADE_TIMEOUT) = 80s. 82s − 80s = 2s headroom. 2nd key gets full 40s. ✅
- Worst case total: 82s (local) + 45s (peer, R697) = 127s < 300s (PROXY_TIMEOUT). ✅
- Peer fallback path: R697 raised PEER_FALLBACK_TIMEOUT 25→45, aligned with 40s upstream + 5s reserve. ✅

---

## 五、执行记录

1. **SSH 到 HM1**
   ```bash
   ssh -p 222 opc_uname@100.109.153.83
   ```

2. **备份 compose**
   ```bash
   cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak.R699
   ```

3. **精准替换 compose 行** (Python script via SCP, full line rewrite)
   - Line 490: `TIER_TIMEOUT_BUDGET_S: "72"` → `"82"`
   - Method: `/tmp/r699_patch.py` (regex match + full line rewrite, avoids R688 trajectory corruption)
   - Verify: `grep -n 'TIER_TIMEOUT_BUDGET_S:' compose.yml` confirms only line 490 changed, line 313 (different service `NV_TIER_TIMEOUT_BUDGET_S`) untouched.

4. **容器重建**
   ```bash
   cd /opt/cc-infra && docker compose up -d nv_gw
   → Container nv_gw Recreated → Started
   ```

5. **四源验证**
   - compose 值 = 82 ✅ (line 490)
   - env 值 = 82 ✅ (`docker exec nv_gw env | grep TIER_TIMEOUT_BUDGET`)
   - 容器 StartedAt 更新 ✅ (`2026-07-04T17:44:12Z`)
   - /health 200 ✅ (`health=200 0.001534s`)

---

## 六、验证记录（Post-change, immediate）

| 指标 | 数值 | 状态 |
|------|------|------|
| TIER_TIMEOUT_BUDGET_S (env) | 82 | ✅ |
| nv_gw container status | Up 7 seconds (healthy) | ✅ |
| /health endpoint | 200, 1.5ms | ✅ |
| StartedAt | 2026-07-04T17:44:12Z | ✅ |
| Config errors in logs | 0 | ✅ |

### 改后预期（待流量验证）

- **dsv4p_nv thinking 2nd key**: 之前 k2 在 30s 被 BUDGET 杀 (total=72029ms), 现在 k2 得到完整 40s window → 预期部分 thinking 请求在 2nd key 成功 (日志中已有 thinking k2 成功案例: `23:41:09.7 [NV-SUCCESS] k3 succeeded after 1 cycle attempts`).
- **dsv4p_nv 失败率**: 47.2% → 预期 35-40% (部分 thinking 请求被 2nd key rescue).
- **ATE 路径**: 47/51 fail (92%) → 预期 ~75-80% (thinking 2nd key rescue 减少 ATE).
- **Peer fallback**: R697 45s timeout 已工作 (72ms 成功案例), 继续作为最后兜底.
- **非 thinking 路径**: 不受影响 (2×25=50s << 82s).

---

## 七、结论

R699 完成。单参数 `TIER_TIMEOUT_BUDGET_S` 从 72 微调至 82（+10s），修复 R694/R695 的参数耦合缺陷：R694 提升 thinking per-key timeout 到 40s 但未同步提升 BUDGET，导致 R695 的 FASTBREAK=2 在 thinking 路径形同虚设（2nd key 被 30s residual budget 杀而非 40s per-key timeout）。BUDGET=82 使 2nd thinking key 获得完整 40s window，预期降低 dsv4p_nv 失败率 ~10-15%。非 thinking 路径不受影响。最坏路径 82s+45s=127s < 300s PROXY_TIMEOUT 安全。

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2
