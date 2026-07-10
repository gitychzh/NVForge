# R1134: HM2→HM1 — NOP (false trigger, triple-dispatch of R1133, post-restart 100% SR 3h then 22:03 zombie burst, all 15 failures code-level, all params at floor/optimal, no config change justified)

**Date**: 2026-07-11 06:10 UTC  
**Trigger**: False trigger (cron script: "这是我提交的, 不触发")  
**Decision**: NOP — zero-change, all failures code-level (13 zombie + 1 NVStream + 1 ATE), all params at floor/optimal

---

## 1. 触发分析

cron脚本输出: "这是我提交的, 不触发"
- 最新 commit 20342de (R1133) author = opc2_uname (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (triple-dispatch: R1132→R1133→R1134)
- Streak: R1124→R1134 = 11 consecutive NOPs (all false triggers)

---

## 2. 数据收集 (HM1: opc_uname@100.109.153.83, 收集于 2026-07-10 22:12 UTC)

### 容器状态
- `nv_gw` 重启时间: 2026-07-10T19:03:27Z (UTC) = ~3h 前
- 容器运行正常，日志零 error/warn/NV-TIER-FAIL/NV-ZOMBIE

### 6h DB 窗口 (16:00-22:12 UTC)

| 指标 | 值 |
|------|-----|
| 总请求 | 59 |
| 成功 (200) | 44 (74.6%) |
| 失败 | 15 (25.4%) |
| avg_dur (OK) | 10,286ms |
| p50_dur (OK) | 6,776ms |
| p95_dur (OK) | 23,874ms |
| max_dur (OK) | 95,076ms |

### 按模型 (6h)

| 模型 | total | ok | err | avg_dur_ok | max_dur |
|------|-------|-----|-----|------------|---------|
| glm5_2_nv | 49 | 35 | 14 | 8,706ms | 95,076ms |
| dsv4p_nv | 10 | 9 | 1 | 18,029ms | 61,142ms |

### 按路径 (6h)

| upstream | cnt | ok | err | avg_dur_ok | avg_ttfb_ok |
|----------|-----|-----|-----|------------|-------------|
| nv_integrate | 51 | 37 | 14 | 9,115ms | 6,835ms |
| nvcf_pexec | 7 | 7 | 0 | 11,550ms | 11,550ms |
| unknown (ATE) | 1 | 0 | 1 | — | — |

- **nvcf_pexec: 7/7 = 100% SR** — 零 NVCFPexecTimeout

### 错误分类 (6h)

| error_type | cnt | 判定 |
|-----------|-----|------|
| zombie_empty_completion | 13 | **code-level**: 僵尸检测功能，快速 abort (3-4s) 替代旧版 96s hang |
| NVStream_TimeoutError | 1 | **code-level**: NVCF stream 超时 (95,076ms) |
| all_tiers_exhausted | 1 | **code-level**: NVCF upstream key 耗尽 (dsv4p_nv, 61,142ms) |

### 小时 SR 趋势 (6h)

| hour (UTC) | total | ok | err | sr% |
|------------|-------|-----|-----|-----|
| 16:00 | 4 | 3 | 1 | 75.0 |
| 17:00 | 20 | 11 | 9 | 55.0 ← zombie密集窗口 |
| 18:00 | 9 | 8 | 1 | 88.9 |
| 19:00 | 6 | 6 | 0 | **100.0** ← restart后 |
| 20:00 | 7 | 7 | 0 | **100.0** |
| 21:00 | 9 | 9 | 0 | **100.0** |
| 22:00 | 4 | 0 | 4 | **0.0** ← zombie burst (22:03 UTC) |

- **Post-restart: 19:00-21:00 = 3 小时 100% SR (22/22 OK)**
- 22:03 zombie burst: 4× zombie_empty_completion, glm5_2_nv integrate, 3,105-4,353ms

### nv_tier_attempts: 0 rows (6h)
— 零 per-key 失败尝试。所有成功请求首 key 成功。

### 24h 总结

| 指标 | 值 |
|------|-----|
| 总请求 | 267 |
| 成功 | 241 (90.3%) |
| 失败 | 26 (9.7%) |
| 24h 错误: zombie_empty_completion | 13 |
| 24h 错误: all_tiers_exhausted | 7 |
| 24h 错误: NVStream_TimeoutError | 6 |

### 最近 10 条请求延迟

| ts | model | status | dur_ms | error |
|----|-------|--------|--------|-------|
| 22:03:43 | glm5_2_nv | 502 | 3,655 | zombie_empty_completion |
| 22:03:38 | glm5_2_nv | 502 | 4,353 | zombie_empty_completion |
| 22:03:32 | glm5_2_nv | 502 | 3,160 | zombie_empty_completion |
| 22:03:27 | glm5_2_nv | 502 | 3,105 | zombie_empty_completion |
| 21:33:48 | glm5_2_nv | 200 | 8,752 | — |
| 21:33:34 | glm5_2_nv | 200 | 5,561 | — |
| 21:33:28 | glm5_2_nv | 200 | 3,163 | — |
| 21:04:06 | glm5_2_nv | 200 | 4,663 | — |
| 21:04:01 | glm5_2_nv | 200 | 10,878 | — |
| 21:03:50 | glm5_2_nv | 200 | 3,655 | — |

— 21:03-21:33 全部 200 OK，延迟 2.5s-10.9s；22:03 全部 zombie (3-4s 快速 abort)

---

## 3. 当前配置 (docker exec nv_gw env)

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | floor/optimal |
| TIER_TIMEOUT_BUDGET_S | 198 | optimal |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | optimal |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | optimal |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | (R1031 code bug: env=2 but log shows threshold=1) |
| TIER_COOLDOWN_S | 15 | floor |
| KEY_COOLDOWN_S | 25 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NVU_FORCE_STREAM_UPGRADE | 0 | disabled |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | aligned |
| NVU_PEER_FALLBACK_ENABLED | 1 | enabled |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | optimal |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | dsv4p_nv has peer-fb path |
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 | generous |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | optimal |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | floor |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | optimal |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | defensive |

---

## 4. NOP决策 — 6 Gates全部通过

### Gate 1: Zero config-fixable failures ✅
- 13 zombie_empty_completion: 代码级僵尸检测功能（正向特征：3-4s 快速 abort 替代旧版 96s hang，触发 openclaw fallback）
- 1 NVStream_TimeoutError: 代码级 NVCF stream 超时，非 config-fixable
- 1 all_tiers_exhausted: NVCF upstream key 耗尽，非 config-fixable
- 0 NVCFPexecTimeout, 0 SSLEOFError, 0 429
- 0 per-key 错误（nv_tier_attempts: 0 rows）

### Gate 2: Pexec 100% SR ✅
- nvcf_pexec: 7/7 = 100% SR
- 零 NVCFPexecTimeout，所有 pexec 请求首 key 成功

### Gate 3: Post-restart 3h 100% before zombie burst ✅
- 19:00-21:00 UTC: 22/22 OK, 100% SR, 连续 3 小时
- 22:03 zombie burst: 4× zombie_empty_completion (代码级功能，快速 abort)
- 所有成功请求首 key 成功

### Gate 4: All params at floor/optimal ✅
- FASTBREAK=1 floor, BUDGET generous, cooldowns minimal
- 零调整空间

### Gate 5: Fallback path not needed ✅
- FALLBACK_GRAPH={} expected state
- No actual fallback triggered
- ms_gw/peer-fb available as safety net

### Gate 6: False trigger ✅
- HM2 自提交 (20342de, author=opc2_uname)
- 脚本标记 "不触发"

---

## 5. 判定

**NOP — 零参数变更, 零compose变更, 零容器重启**

理由:
1. False trigger (HM2自提交, 脚本标记"不触发"), triple-dispatch R1132→R1133→R1134
2. 全部 15 个失败为代码级: 13 zombie_empty_completion (僵尸检测功能, 3-4s 快速 abort), 1 NVStream_TimeoutError (NVCF超时), 1 all_tiers_exhausted (NVCF key耗尽)
3. Post-restart: 19:00-21:00 = 3h 100% SR (22/22 OK), 22:03 zombie burst 4× (代码级)
4. nvcf_pexec 100% SR (7/7), 零 NVCFPexecTimeout
5. nv_tier_attempts: 0 rows — 零 per-key 失败，所有成功请求首 key 成功
6. 全部 config 参数处于 floor/optimal 值, 无优化空间
7. 铁律: 只改HM1不改HM2

**系统健康。等待 HM1 实际新提交触发真正的优化轮次。**

---

## ⏳ 轮到HM1优化HM2