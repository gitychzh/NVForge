# R1520: HM2→HM1 — NOP (false trigger, all params floor/optimal, zero post-restart ATEs)

## 数据收集

### 容器状态
- nv_gw: Up ~1h (restart 2026-07-15T22:25:46Z)
- ms_gw: Up 24h (healthy)
- logs_db: Up 24h (healthy)
- compose md5: 9fb97661 (unchanged from R1519)

### 6h 总体
- 70req/48OK/22fail = 68.6% SR
- 19× zombie_empty_completion (NVCF content-filter: avg 222K input chars, output 6-12 chars)
- 4× all_tiers_exhausted (1 rescued to 200, 3 stayed 502)
- 2× 429_integrate_rate_limit (glm5_2_nv, transient)
- 0× NVCFPexecTimeout (clean key pool)
- fallback_occurred=false for all 70 requests

### 6h 按模型
- dsv4p_nv: 47/36/11 = 76.6% SR
- glm5_2_nv: 23/12/11 = 52.2% SR

### 6h 按小时
- 17:00: 4/2/2 50.0%
- 18:00: 18/14/4 77.8%
- 19:00: 9/5/4 55.6%
- 20:00: 10/6/4 60.0%
- 21:00: 21/17/4 81.0%
- 22:00: 4/2/2 50.0% (pre-restart)
- 23:00: 4/2/2 50.0% (post-restart: all zombie)

### 重启后 (22:25:46Z→)
- **6req/4OK/2zombie = 66.7% SR**
- **0 ATE**
- **0 tier_attempts**
- 2× zombie_empty_completion (NVCF content-filter: glm5_2_nv input=223K, dsv4p_nv input=223K)
- ms_gw: 1/1 100% SR

### 日志
- tier_chain: `['glm5_2_nv']` / `['dsv4p_nv']` (no fallback, 3model) — expected (FALLBACK_GRAPH={})
- NV-ZOMBIE-EMPTY: zombie detection active (fast abort, positive)
- NV-THINKING-TIMEOUT: extended to 66s (correct)
- NV-MS-FB: 无 (tail 200) — ms_gw fallback 未触发
- NV-TIER-FAIL: 无 (tail 200)
- NV-PEER-FB: 无 (tail 200)
- NV-EMPTY-FASTBREAK: 无 (tail 200)
- ms_gw: MS-OK-STREAM + MS-STREAM-DONE for glm5_2 and dsv4p (healthy)

### 当前参数 (floor/optimal)
- UPSTREAM_TIMEOUT=66 (floor for DSv4-Pro)
- TIER_TIMEOUT_BUDGET_S=205 (sufficient: 66 tier + 66 peer-fb = 132 < 205)
- NVU_TIER_BUDGET_DSV4P_NV=66 (floor = UPSTREAM)
- NVU_TIER_BUDGET_GLM5_2_NV=96
- NVU_TIER_BUDGET_MINIMAX_M3_NV=100
- TIER_COOLDOWN_S=15
- KEY_COOLDOWN_S=25
- NVU_PEXEC_TIMEOUT_FASTBREAK=1
- NVU_EMPTY_200_FASTBREAK=2
- NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
- NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
- NVU_MS_GW_FALLBACK_TIMEOUT=120
- NVU_PEER_FALLBACK_ENABLED=1
- NVU_PEER_FALLBACK_TIMEOUT=66
- NVU_PEER_FB_SKIP_MODELS=(empty)
- NVU_FALLBACK_HEALTH_THRESHOLD=0.05

## 决策: NOP

**原因:**
1. 重启后 0 ATE, 0 tier_attempts — 系统稳定
2. 所有参数已在 floor/optimal 状态
3. 6h 聚合中的 3 ATE 均为重启前 (22:05-22:09, 22:25 重启前)
4. 19 zombie 均为 NVCF content-filter (平均输入 222K chars, 输出 6-12 chars), 非 config 可修复
5. ms_gw 93.3% SR, dsv4p_ms 和 glm5_2_ms 均健康 (MS-OK-STREAM + MS-STREAM-DONE)
6. 0 NVCFPexecTimeout — key pool 清洁
7. 铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
