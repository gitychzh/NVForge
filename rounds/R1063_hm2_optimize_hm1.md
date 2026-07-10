# R1063: HM2→HM1 — NOP (false trigger, double-dispatch, 100% 6h SR, 0 errors)

## TL;DR
False trigger — cron script correctly detected `"这是我提交的, 不触发"`. Double-dispatch (R1062 already committed by pre-run script). 6h: 42req/42OK(100.0%)/0fail. nv_tier_attempts 0 rows. glm5_2_nv 42/42 100% first-attempt integrate. Only 1 SSLEOF (cycled to next key OK). All params at optimal/floor. Zero param; iron rule: only change HM1 never HM2.

---

## 一、触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = opc2_uname (HM2), commit `1990225` (R1062 NOP)
- HM1 本地 git log 停留在 R821（241 轮落后）
- HM1 未提交任何新内容 → false trigger confirmed
- 本回合为 double-dispatch（预运行脚本已提交 R1062，cron 再次派遣）

---

## 二、漂移检测（Pre-change）

### 2.1 源1 — 容器 env
```
NVU_EMPTY_200_FASTBREAK=2 ✅
NVU_PEXEC_TIMEOUT_FASTBREAK=1 ✅
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1 ✅
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv ✅
NV_INTEGRATE_MODELS=glm5_2_nv,minimax_m3_nv ✅
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,dsv4p_nv:dsv4p_ms,kimi_nv:kimi_ms ✅
NVU_MS_GW_FALLBACK_TIMEOUT=90 ✅
NVU_STREAM_TOTAL_DEADLINE_S=90 ✅
NVU_TIER_BUDGET_MINIMAX_M3_NV=100 ✅
TIER_TIMEOUT_BUDGET_S=110 ✅
UPSTREAM_TIMEOUT=66 ✅
KEY_COOLDOWN_S=25 ✅
TIER_COOLDOWN_S=18 ✅
NV_INTEGRATE_KEY_COOLDOWN_S=0 ✅
MIN_OUTBOUND_INTERVAL_S=0 ✅
NVU_PEER_FALLBACK_ENABLED=1 ✅
NVU_PEER_FALLBACK_TIMEOUT=45 ✅
```

### 2.2 源2 — 容器状态
```
nv_gw Up 4 hours (healthy) — started 2026-07-10 01:08 UTC (post-R1039 deploy)
ms_gw /health=ok, 3 models (glm5_2_ms, dsv4p_ms, kimi_ms), 0 keys cooling, 0 variants cooling
```

### 2.3 源3 — 运行时日志
```
docker logs nv_gw --tail 100
→ Only 1 error: NV-INTEGRATE-ERR SSLEOFError k2 (5002ms) → NV-INTEGRATE-SSL-CYCLE to k3 → OK
→ 0 NV-TIER-FAIL, 0 NV-EMPTY-FASTBREAK, 0 NVCFPexec, 0 empty_200, 0 timeout, 0 ATE
→ All first-attempt integrate success
```

**结论：四源全部通过，无漂移。**

---

## 三、数据摘要（6h 窗口，2026-07-10 07:29–13:29 UTC）

### 3.1 DB（nv_requests）
| 指标 | 数值 |
|------|------|
| 总请求 | 42 |
| 成功 | 42 (100.0% SR) |
| 失败 | 0 |
| nv_tier_attempts | 0 rows |

### 3.2 按模型
| 模型 | 请求 | 成功 | SR | avg_ttfb | max_ttfb |
|------|------|------|-----|----------|----------|
| glm5_2_nv | 42 | 42 | 100% | 9,684ms | 39,617ms |
| dsv4p_nv | 0 | - | - | - | - |
| kimi_nv | 0 | - | - | - | - |
| minimax_m3_nv | 0 | - | - | - | - |

### 3.3 按 upstream_type
| 类型 | 请求 | 成功 | SR |
|------|------|------|-----|
| nv_integrate | 42 | 42 | 100% |
| nv_pexec | 0 | - | - |

### 3.4 错误
| 类型 | 数量 |
|------|------|
| SSLEOF (日志) | 1 (→cycled to k3→OK) |
| DB error_type | 0 |
| nv_tier_attempts | 0 |

### 3.5 ms_gw
- /health=ok, 3 models (glm5_2_ms, dsv4p_ms, kimi_ms)
- 0 keys cooling, 0 variants cooling, 0 models_all_exhausted
- ms_requests 6h: 0 rows (no fallback triggered)
- nv_gw 100% first-attempt integrate → ms_gw never needed

---

## 四、决策分析

| 参数 | 当前值 | 候选 | 数据支撑 | 决策 |
|------|--------|------|---------|------|
| All params | floor/optimal | — | 100% SR, 0 errors, integrate 100% first-attempt | ❌ NOP |

**穷举候选：**
- **UPSTREAM_TIMEOUT↓**: 66→64? 无NVCFPexecTimeout，非绑定。❌
- **BUDGET↓**: 110→108? 零ATE，无失败路径可压缩。❌
- **EMPTY_200_FASTBREAK↓**: 2→1? R1031刚升到2，数据阶段无dsv4p_nv流量验证。❌
- **TIER_COOLDOWN↓**: 18→15? R1018刚升到18，当前无tier exhaustion事件。❌
- **PEER_FALLBACK↓**: 45→40? 零peer fallback触发。❌
- **MS_GW_FALLBACK_TIMEOUT↓**: 90→60? 零ms_gw fallback触发。❌
- **STREAM_DEADLINE↓**: 90→72? R1038刚升到90。❌
- **TIER_BUDGET_MINIMAX↓**: 100→90? 零minimax流量。❌
- **INTEGRATE_KEY_COOLDOWN↑**: 0→? 零429，零key conflict。❌
- **MIN_OUTBOUND↑**: 0→? Floor=0，零节流需求。❌

**最终决策**：NOP。所有参数在最优/地板值，零错误，零优化空间。

---

## 五、结论

R1063 NOP。False trigger double-dispatch。6h 窗口 42req/42OK(100.0% SR)，全部 glm5_2_nv integrate 一次成功，avg_ttfb=9,684ms。零 tier_attempts，零 DB error。仅 1 次 SSLEOF（自动循环到 k3 成功）。所有参数在最优/地板值。无参数修改。

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2
