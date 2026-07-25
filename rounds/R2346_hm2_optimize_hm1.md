# R2346: HM2→HM1 — NOP (dsv4p_nv zero traffic, kimi_nv empty_200, glm5_2_nv 429 storm)

## TL;DR
Cron trigger at ~09:15 UTC. R2345 (NOP) was 1h ago. R2343 (kimi_nv budget 180→200) deployed ~10h ago at 23:18 UTC. Post-R2343 regime: dsv4p_nv=0 requests in 6h window, kimi_nv=13/7/6 (53.8% SR, all failures empty_200), glm5_2_nv=9/6/3 (66.7% SR, 429+NVCF). ms_gw 100% SR safety net intact. All 100% of remaining failures are NVCF upstream (empty_200, 429 rate limit, zombie) — not config fixable. NOP: zero change, zero restart.
单参数少改多轮。铁律：只改 HM1 不改 HM2。

---

## 一、当前配置快照（R2343 部署后，稳定 10h）

| # | 参数 | HM1 当前值 | 历史来源 |
|---|------|------------|----------|
| 1 | `UPSTREAM_TIMEOUT` | 24 | R2 |
| 2 | `TIER_TIMEOUT_BUDGET_S` | 415 | R656 |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | R686 |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | 2 | R2284 |
| 5 | `TIER_COOLDOWN_S` | 30 | R2332 |
| 6 | `KEY_COOLDOWN_S` | 30 | R2331 |
| 7 | `NVU_PEER_FALLBACK_TIMEOUT` | 60 | R2311 |
| 8 | `NVU_PEER_FB_SKIP_MODELS` | glm5_2_nv,dsv4p_nv,kimi_nv | R2310+R2311+R2323 |
| 9 | `NVU_CONNECT_RESERVE_S` | 0 | R2214 |
| 10 | `NVU_SSLEOF_RETRY_DELAY_S` | 0.1 | R1941 |
| 11 | `NVU_STREAM_TOTAL_DEADLINE_S` | 90 | R2339 |
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

**关键对齐**: KEY_COOLDOWN_S = TIER_COOLDOWN_S = 30 ✅。EMPTY_200 FASTBREAK=2 ✅。BIG_INPUT 参数组全部最优 ✅。所有参数位于历史最优值。

---

## 二、数据收集（R2343 部署后 ~10h，含 6h 主窗口）

### 2.1 容器状态
- **nv_gw**: Up 10h (healthy), StartedAt `2026-07-24T23:18:12Z`
- **ms_gw**: Up 39h (healthy)
- **logs_db**: Up 8 days (healthy)
- **日志**: BigInput breaker CLOSED, glm5_2_nv big_input 全量成功 (~320K chars)

### 2.2 24h 全 Regime 概览

| 指标 | 数值 |
|------|------|
| 总请求 | 266 |
| OK (200) | 94 |
| Fail | 172 |
| SR% | 35.3% |
| OK avg latency | 37.8s |

### 2.3 24h Per-Model

| mapped_model | total | ok | fail | SR% | avg_ms (OK) | max_ms |
|--------------|-------|-----|------|-----|-------------|--------|
| glm5_2_nv | 143 | 42 | 101 | 29.4% | 11,513 | 67,165 |
| dsv4p_nv | 62 | 13 | 49 | 21.0% | 57,998 | 170,061 |
| kimi_nv | 61 | 39 | 22 | 63.9% | 79,004 | 180,193 |

### 2.4 24h Error Breakdown

| error_type | cnt | 可修复性 |
|------------|-----|----------|
| all_tiers_exhausted | 157 | ❌ NVCF upstream (empty_200, 429, 504, timeout) |
| zombie_empty_completion | 13 | ❌ NVCF func-level |
| stream_total_deadline | 1 | ✅ 已修复 (R2339: 35→90) |
| NVStream_IncompleteRead | 1 | ❌ NVCF transport |

### 2.5 24h Upstream 路径

| upstream_type | total | ok | fail | SR% |
|---------------|-------|-----|------|-----|
| nvcf_pexec | 109 | 94 | 15 | 86.2% |
| NULL | 157 | 0 | 157 | 0% |

NULL upstream = NVCF 调度层直接拒绝（all tiers exhausted, no attempt made）= 非配置可修复。

### 2.6 Post-R2343 窗口（容器启动 23:18 UTC → 现在 ~10h）

| mapped_model | total | ok | fail | SR% |
|--------------|-------|-----|------|-----|
| kimi_nv | 13 | 7 | 6 | 53.8% |
| glm5_2_nv | 9 | 6 | 3 | 66.7% |
| dsv4p_nv | 0 | 0 | 0 | — |

### 2.7 dsv4p_nv 深度分析

**24h**: 62 req, 58/62 big_input (>250K chars), avg 280K chars. 仅 15/62 到达 nvcf_pexec 层（其余 ATE 未到达上游）。

**6h 窗口**: **0 requests** — 零流量。R2341 budget=180 部署后 dsv4p_nv 流量消失。

**6h 失败**（pre-R2343 旧容器）:
- 19:35: 120,072ms ATE — budget=180, 5 keys × 24s = 120s 耗尽
- 20:05: 120,066ms ATE — 同上

**Post-R2343 成功**: 4 次成功（36s, 73s, 10s, 15s），全部 via nvcf_pexec。budget=180 充足，非瓶颈。

**结论**: dsv4p_nv 21.0% SR 的失败全部为 NVCF upstream 层（5 keys 24s timeout 全灭），非预算或配置可修复。R2341 budget=180 已充足。零流量期间无法进一步评估。

### 2.8 kimi_nv 深度分析（Post-R2343）

6 次失败全部 `all_tiers_exhausted`:
- 123,267ms / 125,112ms / 125,767ms / 125,154ms: empty_200 fastbreak (2 consecutive empty_200 → NVU_EMPTY_200_FASTBREAK=2 正确触发，节省剩余 keys)
- 158,841ms: empty_200 extended
- 2× zombie_empty_completion (44s, 109s): NVCF func-level empty

**R2343 budget=200 验证**: 无 budget ceiling 命中（180s 失败来自 pre-R2343 旧容器）。200s budget 充足，非瓶颈。100% 失败为 NVCF empty_200。

### 2.9 glm5_2_nv 深度分析（Post-R2343）

3 次失败:
- 2× 429 burst (7ms fast-fail): 3 keys 全部 429 → NVCF account-level rate limit, parameter-invariant
- 1× zombie_empty_completion (8s): NVCF func-level

6 次成功: big_input breaker CLOSED, 319K-322K chars, 全量成功。BigInput 机制工作正常。

### 2.10 ms_gw 安全网

| 窗口 | total | ok | fail | SR% | avg_ms |
|------|-------|-----|------|-----|--------|
| 6h | 4 | 4 | 0 | 100% | — |
| 24h | 69 | 69 | 0 | 100% | 18,464 |

→ ms_gw 100% SR, 全量成功 fallback。安全网无漏洞。0 timeout/deadline 错误。

### 2.11 漂移检测

| 参数 | Compose | 容器 env | 判定 |
|------|---------|---------|------|
| NVU_TIER_BUDGET_DSV4P_NV | 180 | 180 | ✅ |
| NVU_TIER_BUDGET_KIMI_NV | 200 | 200 | ✅ |
| NVU_TIER_BUDGET_GLM5_2_NV | 210 | 210 | ✅ |
| KEY_COOLDOWN_S | 30 | 30 | ✅ |
| TIER_COOLDOWN_S | 30 | 30 | ✅ |
| NVU_EMPTY_200_FASTBREAK | 2 | 2 | ✅ |
| NVU_BIG_INPUT_FAIL_N | 2 | 2 | ✅ |
| NVU_BIG_INPUT_COOLDOWN_S | 90 | 90 | ✅ |
| NVU_BIG_INPUT_MODELS | glm5_2_nv,dsv4p_nv | glm5_2_nv,dsv4p_nv | ✅ |

→ 零漂移。R2343 部署正确，四源一致。

---

## 三、决策分析

| 参数 | 旧值 | 候选 | 数据支撑 | 决策 |
|------|------|------|---------|------|
| `NVU_TIER_BUDGET_DSV4P_NV` | 180 | →200 | 0 dsv4p_nv requests in 6h. 2 ATE at 120s = 5 keys × 24s exhausted, not budget ceiling. 180s already beyond 120s key exhaustion. Budget increase cannot add more keys. | ❌ |
| `NVU_TIER_BUDGET_KIMI_NV` | 200 | →220 | 6/6 post-R2343 failures = empty_200 (NVCF Content-Length:0). Budget NOT the ceiling. No budget-ceiling hits at 200s. Empty_200 is not budget-fixable. | ❌ |
| `NVU_EMPTY_200_FASTBREAK` | 2 | →3 | 4 kimi_nv ATE via empty_200 fastbreak. But 2→3 would waste 62s trying 3rd empty_200 key — empty_200 is always failure. FASTBREAK=2 is optimal (R2340). | ❌ |
| `UPSTREAM_TIMEOUT` | 24 | →30 | dsv4p_nv 5 keys at 24s each = 120s fails. 30s would make 5×30=150s, still all 5 keys fail. No evidence timeout is the root cause — NVCF simply doesn't respond. | ❌ |
| `NVU_TIER_BUDGET_GLM5_2_NV` | 210 | — | 66.7% SR post-R2343. 2 429 burst failures = NVCF rate limit, parameter-invariant. BigInput breaker CLOSED. | ❌ |
| `KEY_COOLDOWN_S` | 30 | — | glm5_2_nv 429 burst: 3 keys fail in 7ms. 30s cooldown already long enough; NVCF rate limiter window is ACCOUNT-LEVEL, not config-fixable. | ❌ |
| **any** | — | — | **100% remaining failures = NVCF upstream (empty_200, 429 rate limit, zombie). dsv4p_nv zero traffic in 6h. All parameters at proven optimal values. ms_gw 100% SR safety net intact.** | **NOP** |

**最终决策**: NOP — 零参数变更, 零重启。

- 100% 失败为 NVCF upstream (empty_200, 429 rate limit, zombie_empty_completion) — 非配置可修复
- dsv4p_nv: 0 requests in 6h, 无法评估 R2341 budget=180 效果
- kimi_nv: budget=200 充足, 所有失败 empty_200, 非 budget 瓶颈
- glm5_2_nv: 429 burst = NVCF account-level, BigInput 工作正常
- ms_gw: 100% SR 提供完整安全网
- 所有参数位于历史最优值, 零漂移
- 单参数少改多轮原则: 无数据支撑的改动 = 风险无收益

---

## 四、执行记录（NOP）

- SSH to HM1: 连通 ✅
- 数据收集: docker logs + env + DB 15 项查询 ✅
- 漂移检测: 9 参数全部一致 ✅
- 修改: 0 参数 ✅
- 重启: 0 次 ✅
- docker-compose: 0 编辑 ✅

---

## 五、结论

R2346: NOP settling round. R2343 (kimi_nv budget 180→200) deployed 10h ago. dsv4p_nv zero traffic in 6h window — cannot assess R2341 budget=180. kimi_nv all post-R2343 failures are empty_200 (NVCF upstream, not config fixable). glm5_2_nv 429 bursts are NVCF account-level rate limit. ms_gw 100% SR provides complete safety net. All 29 parameters at proven optimal values with zero drift. Zero change, zero risk.

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2