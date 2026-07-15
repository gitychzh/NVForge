# R1486: HM2→HM1 — NOP (R1484 fix deployed, post-restart zombie-only, all params floor/optimal)

## 数据收集 (HM1 via SSH)

### 容器状态
- nv_gw: Up ~19min (restarted by R1484 compose fix, env confirmed: MODELMAP no dsv4p_nv)
- ms_gw: Up 18h+
- logs_db: Up 18h+
- compose md5: 089a818e37299c1632ce56e44b326090 (unchanged from R1485)

### 容器 env 确认
- NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms ✅ (no dsv4p_nv → peer-fb path)
- NVU_PEER_FB_SKIP_MODELS="" ✅ (peer-fb enabled for all)
- NVU_PEER_FALLBACK_ENABLED=1 ✅
- NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006 ✅
- NVU_PEER_FALLBACK_TIMEOUT=66 ✅ (=UPSTREAM)
- All FASTBREAK: floor/optimal ✅
- NVU_TIER_BUDGET_DSV4P_NV=66 (=UPSTREAM, BUDGET floor) ✅
- NVU_TIER_BUDGET_GLM5_2_NV=96 ✅
- UPSTREAM_TIMEOUT=66 (floor) ✅
- TIER_TIMEOUT_BUDGET_S=205 (safe) ✅
- TIER_COOLDOWN_S=15 (floor) ✅
- KEY_COOLDOWN_S=25 (floor) ✅

### 6h 总体 (nv_requests)
- 46req / 23OK / 23fail = 50.0% SR

### 6h 每小时 SR
| 小时 | total | OK | fail | SR |
|------|-------|-----|------|-----|
| 12:00 | 7 | 3 | 4 | 42.9% |
| 13:00 | 9 | 5 | 4 | 55.6% |
| 14:00 | 7 | 3 | 4 | 42.9% |
| 15:00 | 6 | 2 | 4 | 33.3% |
| 16:00 | 9 | 6 | 3 | 66.7% |
| 17:00 | 8 | 4 | 4 | 50.0% |

### 6h 错误分类
| error_type | cnt | model | avg_dur_ms | 可配置修复? |
|-----------|-----|-------|-----------|-------------|
| zombie_empty_completion | 17 | glm5_2_nv(12)/dsv4p_nv(5) | 12,464/37,706 | ❌ NVCF content-filter |
| all_tiers_exhausted | 6 | dsv4p_nv(6) | 63,811 | ❌ pre-restart (R1484 restart) |

### zombie 详情
| model | cnt | avg_input_chars | avg_dur_ms |
|-------|-----|----------------|-------------|
| glm5_2_nv | 12 | 219,175 | 12,464 |
| dsv4p_nv | 5 | 219,850 | 37,706 |

input_chars ~200K-221K, output=6-12 chars, finish_reason=stop, content_chars<50 → NVCF content-filter (R1107 code-level feature, 不可配置修复)

### all_tiers_exhausted 详情
| model | cnt | avg_dur_ms | fallback_actually_attempted |
|-------|-----|-----------|-----------------------------|
| dsv4p_nv | 6 | 63,811 | f (全部) |

全部 pre-restart (container restarted at 17:27 UTC). R1484 重启后 MODELMAP 无 dsv4p_nv → ATE 走 peer-fb (HM2 独立 key 池). 重启后无 ATE

### ms_gw 6h
- 20req, 17OK = 85.0% SR
- glm5_2_ms (ZHIPUAI/GLM-5.2): MS-OK-STREAM + MS-STREAM-DONE 正常
- dsv4p_ms (DEEPSEEK-AI/DEEPSEEK-V4-PRO): MS-OK-STREAM + MS-STREAM-DONE 正常

### tier_attempts
- 2 rows: glm5_2_nv 429_integrate_rate_limit (k1/k2, 正常 key cycling)
- 0 其他错误 — 干净 key 池

### nv_gw 日志 (post-restart ~19min)
- NV-ZOMBIE-EMPTY: 4 (glm5_2_nv: 2, dsv4p_nv: 2) — NVCF content-filter
- NV-ZOMBIE-ERROR-CHUNK: sent finish_reason=timeout → openclaw fallback
- NV-TIER-FAIL: 0
- NV-MS-FB: 0
- NV-PEER-FB: 0
- NV-EMPTY-FASTBREAK: 0
- tier_chain: `['glm5_2_nv']` / `['dsv4p_nv']` (no fallback, 3model) — R832 预期状态 (FALLBACK_GRAPH={})
- 0 504_nv_gateway_timeout

### 成功请求延迟分布
| bucket | cnt |
|--------|-----|
| <5s | 1 |
| 5-10s | 5 |
| 10-15s | 4 |
| 15-20s | 3 |
| 20-30s | 1 |
| 30-40s | 4 |
| 40-60s | 5 |

### 按 upstream_type 分组
| upstream_type | cnt | OK | fail | avg_dur_ms |
|--------------|-----|-----|------|------------|
| nv_integrate | 25 | 13 | 12 | 13,412 |
| nvcf_pexec | 13 | 8 | 5 | 42,778 |
| (null, ATE) | 8 | 2 | 6 | 49,669 |

## 环境参数状态 (全部 floor/optimal)

| param | value | status |
|-------|-------|--------|
| UPSTREAM_TIMEOUT | 66 | floor |
| TIER_TIMEOUT_BUDGET_S | 205 | safe |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | =UPSTREAM (BUDGET floor) |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | sufficient |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | optimal (function-level) |
| NVU_EMPTY_200_FASTBREAK | 2 | set (R1039: no-op in pexec) |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | optimal (function-level) |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | sufficient |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | =UPSTREAM |
| NVU_PEER_FB_SKIP_MODELS | (empty) | peer-fb enabled for all |
| TIER_COOLDOWN_S | 15 | floor |
| KEY_COOLDOWN_S | 25 | floor |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | floor |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms | no dsv4p_nv ✅ |

## 决策

**NOP — 所有参数已在地板/最优状态，无任何优化空间。**

- zombie 17 (74% of failures): NVCF content-filter (input_chars ~200K-221K, output=6-12 chars). R1107 code-level feature — 3-15s fast abort vs old 96s hang. 不可配置修复
- ATE 6: 全部 pre-restart (R1484 重启前). 重启后 dsv4p_nv 无 ATE. MODELMAP 无 dsv4p_nv → peer-fb 路径已启用. PEER_FB_SKIP_MODELS 空 → 所有模型可走 peer-fb
- ms_gw 17/20 85% SR (healthy). glm5_2_ms + dsv4p_ms 均正常
- 0 tier_attempts (除 2 个 429 rate limit) — 干净 key 池
- 所有 FASTBREAK/Cooldown/Timeout/Budget 参数已到最优值
- PEER_FB budget math: BUDGET(205) - UPSTREAM(66) = 139s >> PEER_FALLBACK_TIMEOUT(66) ✅

**评判: 无参数可改。少改多轮，本轮 NOP。铁律: 只改HM1不改HM2 ✅**

## ⏳ 轮到HM1优化HM2
