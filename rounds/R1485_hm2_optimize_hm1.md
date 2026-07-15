# R1485: HM2→HM1 — NOP (all params floor/optimal, post-restart no dsv4p_nv traffic, peer-fb active)

## 数据收集 (HM1 via SSH)

### 容器状态
- nv_gw: Up ~35min (restarted by R1484 compose fix)
- logs_db: Up 17h+
- ms_gw: Up 17h+
- compose line 674: `NVU_MS_GW_FALLBACK_MODELMAP: "glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms"` (no dsv4p_nv)

### 容器 env 确认
- NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms ✅
- NVU_PEER_FB_SKIP_MODELS="" ✅ (peer-fb enabled for all)
- NVU_PEER_FALLBACK_ENABLED=1 ✅
- NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006 ✅
- All FASTBREAK params: floor/optimal ✅
- NVU_TIER_BUDGET_DSV4P_NV=66 (=UPSTREAM_TIMEOUT, BUDGET floor) ✅
- NVU_MS_GW_FALLBACK_TIMEOUT=120 ✅

### 6h 总体 (nv_requests)
- 45req / 22OK / 23fail = 48.9% SR

### 6h 错误分类
| error_type | cnt | model | avg_dur_ms | 可配置修复? |
|-----------|-----|-------|-----------|-------------|
| zombie_empty_completion | 16 | glm5_2_nv(12) + dsv4p_nv(4) | 11,426/43,191 | ❌ NVCF content-filter |
| all_tiers_exhausted | 7 | dsv4p_nv(7) | 63,828 | ⚠️ pre-restart; peer-fb now active |

### 6h 每小时 SR
| 小时 | total | OK | fail | SR |
|------|-------|-----|------|-----|
| 11:00 | 3 | 1 | 2 | 33.3% |
| 12:00 | 7 | 3 | 4 | 42.9% |
| 13:00 | 9 | 5 | 4 | 55.6% |
| 14:00 | 7 | 3 | 4 | 42.9% |
| 15:00 | 6 | 2 | 4 | 33.3% |
| 16:00 | 9 | 6 | 3 | 66.7% |
| 17:00 | 4 | 2 | 2 | 50.0% |

### dsv4p_nv 6h 详情
| status | error_type | cnt | avg_dur_ms |
|--------|-----------|-----|-----------|
| 200 | — | 7 | 47,166 |
| 502 | all_tiers_exhausted | 7 | 63,828 |
| 502 | zombie_empty_completion | 4 | 43,191 |
| 200 | all_tiers_exhausted | 2 | 7,241 |

### ms_gw 6h
- 21req, 18OK = 85.7% SR
- dsv4p_ms (DEEPSEEK-AI/DEEPSEEK-V4-PRO): 7/7 100% SR (healthy)
- glm5_2_ms (ZHIPUAI/GLM-5.2): 11/11 100% SR
- 3 errors (null model, likely variant exhaustion)

### tier_attempts
- 0 rows (clean key pool, no 429 cycling)

### nv_gw 日志 (post-restart ~35min)
- NV-ZOMBIE-EMPTY: 2 (glm5_2_nv, content_chars=12 < 50, input_chars=221K, R1107 code-level feature)
- NV-INTEGRATE: glm5_2_nv k2/k3 → 429 rate limit → k4 success (正常 key cycling)
- NV-PEER-FB: 0 (no dsv4p_nv ATE post-restart)
- NV-MS-FB: 0 (no dsv4p_nv in MODELMAP, glm5_2_nv no ATE)

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

## 决策

**NOP — 所有参数已在地板/最优状态，无任何优化空间。**

- zombie 16: NVCF content-filter (input_chars ~200K-221K), R1107 code-level feature, 不可配置修复
- ATE 7: 全部 pre-restart (R1484 compose fix 重启前). 重启后 dsv4p_nv 无流量. MODELMAP 无 dsv4p_nv → ATE 会走 peer-fb (HM2 独立 key 池). PEER_FB_SKIP_MODELS 空 → peer-fb 已启用
- ms_gw dsv4p_ms 7/7 100% SR (healthy). R1103 streaming sync defect 仍存在，但这是 code-level 缺陷，不可配置修复
- 所有 FASTBREAK/Cooldown/Timeout/Budget 参数已到最优值
- 0 tier_attempts — 干净 key 池

**评判: 无参数可改。少改多轮，本轮 NOP。铁律: 只改HM1不改HM2 ✅**

## ⏳ 轮到HM1优化HM2
