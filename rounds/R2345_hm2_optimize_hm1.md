# R2345: HM2→HM1 — NOP (cron trigger, R2343 settling, no config-fixable issues)

## TL;DR
Cron trigger at 08:05 UTC. R2343 (kimi_nv budget 180→200) deployed 48min ago at 23:18 UTC. Post-restart regime: 8 req / 3 OK / 5 fail. All 5 failures are NVCF upstream empty_200 (4 kimi_nv) + 1 glm5_2_nv zombie — not config fixable. No parameter drift. NOP: zero change, zero restart.
单参数少改多轮。铁律：只改 HM1 不改 HM2。

---

## 一、当前配置快照（R2343 部署后）

| # | 参数 | HM1 当前值 | 历史来源 |
|---|------|------------|----------|
| 1 | `UPSTREAM_TIMEOUT` | 24 | R2 |
| 2 | `TIER_TIMEOUT_BUDGET_S` | 415 | R656 |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | R686 |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | 2 | R2284 |
| 5 | `TIER_COOLDOWN_S` | 30 | R2332 (pair-aligned with KEY_COOLDOWN) |
| 6 | `KEY_COOLDOWN_S` | 30 | R2331 |
| 7 | `NVU_PEER_FALLBACK_TIMEOUT` | 60 | R2311 |
| 8 | `NVU_PEER_FB_SKIP_MODELS` | glm5_2_nv,dsv4p_nv,kimi_nv | R2310+R2311+R2323 |
| 9 | `NVU_CONNECT_RESERVE_S` | 0 | R2214 |
| 10 | `NVU_SSLEOF_RETRY_DELAY_S` | 0.1 | R1941 |
| 11 | `NVU_STREAM_TOTAL_DEADLINE_S` | 90 | code default (R2339) |
| 12 | `NVU_STREAM_FIRST_BYTE_DEADLINE_S` | 15 | R910 |
| 13 | `NVU_FORCE_STREAM_UPGRADE` | 0 | R921 |
| 14 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 66 | R823 |
| 15 | `NVU_EMPTY_200_FASTBREAK` | 2 | R2340 |
| 16 | `NVU_INTEGRATE_TIMEOUT_FASTBREAK` | 1 | R921 |
| 17 | `NV_INTEGRATE_KEY_COOLDOWN_S` | 0 | R650 |
| 18 | `NVU_BIG_INPUT_COOLDOWN_S` | 90 | R2327 |
| 19 | `NVU_BIG_INPUT_FAIL_N` | 2 | R2322 |
| 20 | `NVU_BIG_INPUT_MODELS` | glm5_2_nv,dsv4p_nv | R2317 |
| 21 | `NVU_BIG_INPUT_THRESHOLD` | 250000 | R2312 |
| 22 | `NVU_MS_GW_FALLBACK_TIMEOUT` | 120 | R827 |
| 23 | `NVU_MS_GW_FALLBACK_MODELMAP` | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms | R1020 |
| 24 | `NVU_TIER_BUDGET_DSV4P_NV` | 180 | R2341 |
| 25 | `NVU_TIER_BUDGET_GLM5_2_NV` | 210 | R2291 |
| 26 | `NVU_TIER_BUDGET_KIMI_NV` | 200 | R2343 |
| 27 | `NVU_TIER_BUDGET_MINIMAX_M3_NV` | 100 | — |
| 28 | `NVU_FALLBACK_HEALTH_THRESHOLD` | 0.10 | R827 |
| 29 | `TIER_TIMEOUT_BUDGET_S` | 415 | R2294 |

**关键对齐**: KEY_COOLDOWN_S = TIER_COOLDOWN_S = 30 ✅ 无死区。empty_200 FASTBREAK=2 ✅。BIG_INPUT 参数组全部最优 ✅。

---

## 二、数据收集（R2343 部署后，48min 窗口）

### 2.1 容器状态
- **nv_gw**: Up 48 minutes (healthy), StartedAt `2026-07-24T23:18:12.375480861Z`
- **ms_gw**: Up 39 hours (healthy)
- **logs_db**: Up 8 days (healthy)
- **日志**: 仅 BrokenPipeError (client断开, 无实际影响)

### 2.2 DB 概览（Post-Restart 窗口 23:18+）

| 指标 | 数值 |
|------|------|
| 总请求 | 8 |
| OK (200) | 3 |
| Fail | 5 |
| SR% | 37.5% |
| 带429-cycle | 1 |
| 总429-cycles | 1 |
| OK avg latency | 30.0s |

### 2.3 Per-Model 明细（Post-Restart）

| mapped_model | total | ok | fail | avg_ms (OK) |
|--------------|-------|-----|------|-------------|
| kimi_nv | 4 | 0 | 4 | — |
| glm5_2_nv | 4 | 3 | 1 | 30.0s |
| dsv4p_nv | 0 | 0 | 0 | — |

### 2.4 错误分解（Post-Restart）

| error_type | cnt | 模型 | 属性 |
|------------|-----|------|------|
| all_tiers_exhausted | 4 | kimi_nv | empty_200 fastbreak, upstream_type=NULL |
| zombie_empty_completion | 1 | glm5_2_nv | NVCF func-level empty |

### 2.5 kimi_nv ATE 根因（Docker Logs）

```
[NV-EMPTY-200] k5 → 200 Content-Length:0 (stream)
[NV-EMPTY-CYCLE] k5 empty 200, marked cooling 30.0s, cycling
[NV-EMPTY-200] k1 → 200 Content-Length:0 (stream)
[NV-EMPTY-FASTBREAK] 2 consecutive empty_200 ≥ threshold 2, fast-break
[NV-TIER-FAIL] 429=0, empty200=2, timeout=0, other=0, elapsed=123784ms
[NV-ALL-TIERS-FAIL] All 1 tiers failed, ABORT-NO-FALLBACK
```

→ **NVCF upstream empty_200**: NVCF 返回 Content-Length:0, 非配置可修复。FASTBREAK=2 正确工作（saved remaining keys）。

### 2.6 glm5_2_nv 成功/失败

- 3/3 OK: big-input breaker CLOSED, 全量成功 (319K-320K chars, 24.7s, 18.0s, 44.0s)
- 1 zombie: finish_reason=stop, content_chars=35 < 50 → zombie detected, sent error SSE → CC retry

### 2.7 24h 全 Regime 错误

| error_type | cnt | 可修复性 |
|------------|-----|----------|
| all_tiers_exhausted | 153 | ❌ NVCF upstream (empty_200, 504, 429) |
| zombie_empty_completion | 12 | ❌ NVCF func-level |
| stream_total_deadline | 1 | ✅ 已修复 (R2339: 35→90) |
| NVStream_IncompleteRead | 1 | ❌ NVCF transport |

### 2.8 24h Upstream 路径

| upstream_type | total | ok | fail | SR% |
|---------------|-------|-----|------|-----|
| NULL | 155 | 0 | 155 | 0% |
| nvcf_pexec | 107 | 92 | 15 | 86.0% |

NULL upstream_type = NVCF 调度层直接拒绝（all tiers exhausted, no attempt made）= 非配置可修复。

### 2.9 ms_gw 安全网

| 窗口 | total | ok | fail | SR% |
|------|-------|-----|------|-----|
| 6h | 26 | 26 | 0 | 100% |

→ ms_gw 100% SR, 全量成功 fallback。安全网无漏洞。

### 2.10 漂移检测

| 参数 | Compose | 容器 env | 判定 |
|------|---------|---------|------|
| KEY_COOLDOWN_S | 30 | 30 | ✅ |
| TIER_COOLDOWN_S | 30 | 30 | ✅ |
| NVU_EMPTY_200_FASTBREAK | 2 | 2 | ✅ |
| NVU_TIER_BUDGET_KIMI_NV | 200 | 200 | ✅ |
| NVU_TIER_BUDGET_DSV4P_NV | 180 | 180 | ✅ |
| NVU_STREAM_TOTAL_DEADLINE_S | 90 | 90 | ✅ |

→ 零漂移。R2343 部署正确，四源一致。

---

## 三、决策分析

| 参数 | 旧值 | 候选 | 数据支撑 | 决策 |
|------|------|------|---------|------|
| `NVU_EMPTY_200_FASTBREAK` | 2 | →3 | 4 kimi_nv ATE via empty_200 fastbreak. 但 empty_200 是 NVCF upstream 问题, 2→3 只会浪费 62s 尝试第 3 个 key, 不会增加成功率 | ❌ |
| `NVU_TIER_BUDGET_KIMI_NV` | 200 | →220 | 4 kimi_nv ATE avg 132s, max 158s — 全在 200s budget 内, 预算非瓶颈。ATE 因 empty_200, 非 timeout | ❌ |
| `NVU_TIER_BUDGET_GLM5_2_NV` | 210 | 无 | glm5_2_nv 3/4 OK (75% SR), 1 zombie 非预算可修复 | ❌ |
| `NVU_TIER_BUDGET_DSV4P_NV` | 180 | 无 | 0 dsv4p_nv traffic post-restart, 无法评估 | ❌ |
| `KEY_COOLDOWN_S` | 30 | 无 | empty_200 非 429 rate-limit, cooldown 无关 | ❌ |
| **any** | — | — | **所有失败均为 NVCF upstream, 非配置可修复. Post-restart 仅 8 请求 <10 阈值** | **NOP** |

**最终决策**: NOP — 零参数变更, 零重启。
- 100% 失败为 NVCF upstream (empty_200, zombie)
- 8 请求 <10 条最低可决策阈值
- R2343 (kimi_nv budget 200) 仍在 settling, 需更多数据
- ms_gw 100% SR 提供完整安全网
- 所有参数位于历史最优值, 无漂移

---

## 四、执行记录（NOP）

- SSH to HM1: 连通 ✅
- 数据收集: docker logs + env + DB 12 项查询 ✅
- 漂移检测: 6 参数全部一致 ✅
- 修改: 0 参数 ✅
- 重启: 0 次 ✅

---

## 五、结论

R2345: NOP settling round. R2343 (kimi_nv budget 180→200) deployed 48min ago, only 8 requests in window. 100% failures are NVCF upstream empty_200 — not config fixable. ms_gw 100% SR provides complete safety net. All parameters at proven optimal values. Zero change, zero risk.

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2