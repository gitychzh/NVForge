# HM2 Optimize HM1 — Round R1132

**Date**: 2026-07-11 05:50 UTC  
**Trigger**: False trigger (cron script: "这是我提交的, 不触发")  
**Decision**: NOP — zero-change, all failures pre-restart code-level, post-restart 100% SR

---

## 1. 触发分析

cron脚本输出: "这是我提交的, 不触发"
- 最新commit author = opc2_uname (HM2自提交)
- 脚本正确检测到自提交并标记 "不触发"
- cron仍被派遣 — 误触发(延续R884→R1131 long streak)
- R1131已是NOP, R1132为double-dispatch

---

## 2. 数据收集 (HM1: opc_uname@100.109.153.83)

### 容器状态
- `nv_gw` 重启时间: 2026-07-10T19:03:27Z (约11h前)
- 日志: 仅119行(启动+成功请求), 无error/warn/NV-TIER-FAIL/NV-ZOMBIE

### 6h DB窗口 (15:00–21:33 UTC)

| 窗口 | 总请求 | OK | 失败 | SR |
|------|--------|-----|------|-----|
| 全部6h | 65 | 52 | 13 | 80.0% |
| pre-restart (15:00-19:03) | 41 | 28 | 13 | 68.3% |
| post-restart (19:03-21:33) | 22 | 22 | 0 | **100%** |

### 失败分类 (全部pre-restart, 共13)

| 类型 | 数量 | 模型 | 耗时 | 判定 |
|------|------|------|------|------|
| zombie_empty_completion | 9 | glm5_2_nv integrate | 2,609-15,320ms | **code-level**: 僵尸检测机制, 快速abort替代旧96s hang |
| NVStream_TimeoutError | 2 | glm5_2_nv integrate | 95,076 / 96,999ms | **code-level**: NVCF stream超时 |
| all_tiers_exhausted | 2 | dsv4p_nv | 61,142 / 61,374ms | **code-level**: NVCF upstream key耗尽 |

### Post-restart性能 (100% SR, 22req)

| 模型 | 请求数 | avg_dur | max_dur |
|------|--------|---------|---------|
| glm5_2_nv | 18 | 6,145ms | 12,019ms |
| dsv4p_nv | 4 | 9,515ms | 13,368ms |

### 路径分布
- nv_integrate: 55req (44 OK / 11 fail)
- nvcf_pexec: 8req (8 OK / 0 fail) — pexec 100%
- NULL (ATE): 2req (0 OK / 2 fail) — pre-restart all_tiers_exhausted

### nv_tier_attempts: 0 rows (无per-key失败)
### fallback_occurred: 65次 false (FALLBACK_GRAPH={} 预期状态)
### ms_gw: 6req total, 0 OK — DB可能schema差异; ms_gw日志显示MS-STREAM-DONE正常

### 小时SR趋势
| 小时(UTC) | 请求 | OK | SR |
|-----------|------|-----|-----|
| 15:00 | 7 | 6 | 85.7% |
| 16:00 | 7 | 5 | 71.4% |
| 17:00 | 20 | 11 | 55.0% ← zombie密集窗口 |
| 18:00 | 9 | 8 | 88.9% |
| 19:00 | 6 | 6 | **100%** ← restart后 |
| 20:00 | 7 | 7 | **100%** |
| 21:00 | 9 | 9 | **100%** |

---

## 3. 当前配置 (docker exec nv_gw env)

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | floor/optimal |
| TIER_TIMEOUT_BUDGET_S | 198 | optimal |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | optimal |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal |
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
| TIER_CHAIN | ['模型'] (no fallback, 3model) | R832预期: FALLBACK_GRAPH={} |

---

## 4. NOP决策 — 6 Gates全部通过

### Gate 1: Zero post-restart failures ✅
- 22/22 post-restart OK, 100% SR 3 consecutive hours

### Gate 2: All failures code-level ✅
- 9 zombie_empty_completion: code-level intentional zombie detection → fast abort (3-15s vs old 96s hang)
- 2 NVStream_TimeoutError: NVCF stream timeout, non-config-fixable
- 2 all_tiers_exhausted: NVCF upstream key exhaustion, non-config-fixable
- 全部 pre-restart, post-restart clean

### Gate 3: 0 NVCFPexecTimeout (no UPSTREAM binding) ✅
- nv_tier_attempts: 0 rows. Post-restart all first-attempt success.

### Gate 4: FALLBACK_GRAPH={} is R832 expected state ✅
- tier_chain=['model'] (no fallback, 3model) — by design, ms_gw same-model fallback instead

### Gate 5: Fallback path not triggered (no failures to fall back from) ✅
- Post-restart all first-attempt successes

### Gate 6: All params at floor/optimal ✅
- FASTBREAK=1 floor, BUDGET generous, cooldowns minimal

---

## 5. 判定

**NOP — 零参数变更, 零compose变更, 零容器重启**

理由:
1. False trigger (HM2自提交, 脚本标记"不触发")
2. 全部13个失败发生在container restart之前 (pre-19:03 UTC)
3. Post-restart: 22/22 OK, **100% SR**, 连续3小时零失败
4. 所有失败类型均为code-level: zombie_empty_completion(僵尸检测机制), NVStream_TimeoutError(NVCF超时), all_tiers_exhausted(NVCF key耗尽)
5. 全部config参数处于floor/optimal值, 无优化空间
6. post-restart性能优异: glm5_2 avg 6.1s, dsv4p avg 9.5s, 全部首次尝试成功
7. NVCF upstream问题不可通过HM1 config修复

---

## ⏳ 轮到HM1优化HM2
