# R1633: HM2→HM1 — NOP (all params at floor, all failures NVCF platform-level, zero config-fixable errors. 5th consecutive NOP)

## 触发分析

- HM1 提交: `f40499a` — R1632: HM2→HM1 NOP (4th consecutive)
- 判定: 轮到HM2 — HM1 提交了 R1632 (NOP), 需要评估是否有新数据可优化

## 数据采集 (改前必有数据)

### HM1 环境 (container env, verified with docker exec)
| 参数 | 值 | 来源 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | container env |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | container env (R1628) |
| NVU_TIER_BUDGET_GLM5_2_NV | 120 | container env |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | container env |
| TIER_COOLDOWN_S | 15 | container env |
| KEY_COOLDOWN_S | 25 | container env |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | container env |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | container env |
| MIN_OUTBOUND_INTERVAL_S | 0 | container env |
| NVU_CONNECT_RESERVE_S | 0 | container env |
| NVU_SSLEOF_RETRY_DELAY_S | 0.5 | container env |
| NVU_FORCE_STREAM_UPGRADE | 0 | container env |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | container env |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | container env |
| NVU_EMPTY_200_FASTBREAK | 2 | container env |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | container env |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | container env |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | container env |
| NVU_PEER_FALLBACK_ENABLED | 1 | container env |
| NVU_PEER_FALLBACK_TIMEOUT | 72 | container env |
| NVU_PEER_FALLBACK_URL | http://100.109.57.26:40006 | container env |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | container env |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms | container env (dsv4p_nv excluded per R1609) |
| TIER_TIMEOUT_BUDGET_S | 205 | container env |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | container env |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | container env |
| PROXY_TIMEOUT | 360 | container env |

✅ compose-comment vs container-env verified: all match. No drift.

### HM1 nv_gw 日志 (最近100行, 17:03-18:08)

**dsv4p_nv failures (3/3, 100% ATE):**
| 时间 | 结果 | 详情 |
|------|------|------|
| 17:05:51 | 502 ATE | k4→504 (504_nv_gateway_timeout), budget 66.0s remaining 1.9s < 5s min→break, peer-fb→502 after 70,404ms |
| 17:33:58 | 502 ATE | k5→504, budget 66.0s remaining 2.4s < 5s min→break, peer-fb→TimeoutError after 72,084ms |
| 18:05:53 | 502 ATE | k1→504, budget 66.0s remaining 2.1s < 5s min→break, peer-fb→502 after 70,369ms |

**glm5_2_nv: 3 zombie_empty_completion + 4 success + 1 SSLEOF (recovered)**
| 时间 | 结果 | 详情 |
|------|------|------|
| 17:03:20 | 200 | k5 pexec success, 7,964ms |
| 17:03:31 | 502 zombie | SSLEOF on k2→retry k3→success but zombie_empty_completion (content_chars=48 < 50, input_chars=231,366) |
| 17:33:20 | 200 | k4 pexec success, 9,348ms |
| 17:33:30 | 502 zombie | zombie_empty_completion (content_chars=48 < 50, input_chars=232,062) |
| 18:03:20 | 200 | k3 pexec success, 7,964ms |
| 18:03:28 | 502 zombie | zombie_empty_completion (content_chars=12 < 50, input_chars=232,672) |
| 18:05:39 | 200 | k2 pexec success, 17,529ms |

**peer-fb: 3/3 FAILED (HM2 also degraded simultaneously)**
- 2/3: peer returned 502 (HM2 nv_gw also all_tiers_exhausted)
- 1/3: TimeoutError after 72,084ms (HM2 nv_gw unresponsive)

### HM1 DB (6h窗口)
| model | status | count |
|-------|--------|-------|
| dsv4p_nv | 200 | 8 |
| dsv4p_nv | 502 | 11 |
| glm5_2_nv | 200 | 15 |
| glm5_2_nv | 502 | 12 |
| **Total** | | **46req/23OK 50.0%SR** |

### HM1 DB (最近15条)
| 时间 | model | status | duration_ms | error_type |
|------|-------|--------|-------------|------------|
| 10:05:53 | dsv4p_nv | 502 | 63,861 | all_tiers_exhausted |
| 10:05:39 | glm5_2_nv | 200 | 17,529 | — |
| 10:03:28 | glm5_2_nv | 502 | 13,429 | zombie_empty_completion |
| 10:03:20 | glm5_2_nv | 200 | 7,964 | — |
| 09:33:58 | dsv4p_nv | 502 | 63,653 | all_tiers_exhausted |
| 09:33:30 | glm5_2_nv | 502 | 5,273 | zombie_empty_completion |
| 09:33:20 | glm5_2_nv | 200 | 9,348 | — |
| 09:05:51 | dsv4p_nv | 502 | 64,087 | all_tiers_exhausted |
| 09:03:31 | glm5_2_nv | 502 | 12,089 | zombie_empty_completion |
| 09:03:20 | glm5_2_nv | 200 | 10,355 | — |
| 08:35:22 | dsv4p_nv | 502 | 72,030 | all_tiers_exhausted |
| 08:33:54 | dsv4p_nv | 200 | 18,518 | (success, error_type=ATE stale) |
| 08:33:26 | glm5_2_nv | 502 | 4,783 | zombie_empty_completion |
| 08:33:20 | glm5_2_nv | 200 | 5,625 | — |
| 08:07:30 | dsv4p_nv | 200 | 10,056 | (success) |

## 分析

### dsv4p_nv: NVCF 504 function-level timeout (0 config-fixable)

所有3个dsv4p_nv ATE模式完全一致:
- 第1key尝试→NVCF 504 at ~64s
- budget=66s剩余1.9-2.4s < 5s minimum → 无法尝试第2key
- peer-fb→HM2也返回502/TimeoutError (HM2同时退化)

**为什么不能提升BUDGET**: 504是NVCF function-level gateway timeout — 同一个function_id (74f02205-c7ba) 所有5个key共享。即使给预算尝试第2key, 同一function仍然返回504。R1628切BUDGET 72→66的推理正确: "72s wastes 6s/ATE waiting for 2nd key on already-dead function, 66=UPSTREAM aligns budget with single-key timeout, fails faster→peer-fb sooner."

**为什么peer-fb也失败**: 6h data: 3/3 peer-fb all failed. 2/3 HM2返回502 (HM2 nv_gw的dsv4p_nv也all_tiers_exhausted), 1/3 TimeoutError. 两个host同时退化 → NVCF function-level系统性问题, 非HM1/HM2各自配置可修。

### glm5_2_nv: NVCF content-filter zombie (0 config-fixable)

3/7 zombie_empty_completion — NVCF返回finish_reason=stop但content_chars<50 (12-48 chars), input_chars全>230K. 这是NVCF content-filter行为 — 大上下文请求被NVCF服务器端过滤, 返回空completion。非配置可修。

glm5_2_nv healthy时表现良好: 4/4 success (7,964-17,529ms), 1 SSLEOF快速恢复。12 zombie全NVCF content-filter, 与R1629/R1630/R1631/R1632观察一致。

### 所有参数已在地板

| 参数 | 当前值 | 地板 | 可再降? |
|------|--------|------|----------|
| NVU_TIER_BUDGET_DSV4P_NV | 66 | 66 (UPSTREAM) | ❌ 低于UPSTREAM则连1key都完不成 |
| MIN_OUTBOUND_INTERVAL_S | 0 | 0 | ❌ 已为0 |
| NVU_CONNECT_RESERVE_S | 0 | 0 | ❌ 已为0 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | 0 | ❌ 已为0 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 1 | ❌ 已为1 |
| NVU_SSLEOF_RETRY_DELAY_S | 0.5 | 0.5 | ❌ 已为0.5 |
| KEY_COOLDOWN_S | 25 | 25 | ❌ 再降429风险 |
| TIER_COOLDOWN_S | 15 | 15 | ❌ 再降key竞争加剧 |
| UPSTREAM_TIMEOUT | 66 | 66 | ❌ NVCFPexecTimeout max=62.6s, thinking需66s |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | 120 | ❌ R1459刚从280→120 |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | 42 | ❌ 已对齐openclaw timeout |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | 20 | ❌ 已为地板 |
| NVU_FORCE_STREAM_UPGRADE | 0 | 0 | ❌ 已关 |
| NVU_EMPTY_200_FASTBREAK | 2 | 2 | ❌ 已为2 |
| NVU_PEER_FALLBACK_TIMEOUT | 72 | 72 | ❌ PEER=72 ≥ peer BUDGET=66+2 ✓ |

**无任何参数可再降。地板已触及。**

## 判定: NOP

**所有失败类型均为NVCF平台级:**
1. dsv4p_nv: NVCF 504 function-level gateway timeout — 单function_id所有key共享, 函数不可用非配置可修
2. glm5_2_nv: NVCF content-filter zombie_empty_completion — 服务器端过滤, 非配置可修
3. peer-fb: HM2同时退化 — 两个host同时受NVCF平台影响, 非配置文件可修

**5th consecutive NOP** (R1629→R1630→R1631→R1632→R1633). 两个host同时退化是NVCF供给侧问题, 不是HM1或HM2本地配置问题。所有参数已在地板, 零配置可修错误。

**变更: 无**
- 零参数修改
- 零compose修改
- 零重启

**预算安全**: 66+72=138 < 205 ✓

## 铁律:只改HM1不改HM2 ✅
## ⏳ 轮到HM1优化HM2
