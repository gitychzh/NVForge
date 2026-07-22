# R2244 (HM2→HM1): NVU_TIER_BUDGET_GLM5_2_NV 34→38 (+4s)

## 6h 窗口数据
- **总请求**: 43req, 28 OK, 15 fail → **65.1% SR**
- **Per-model**:
  - dsv4p_nv: 16req, 8 OK, 8 fail → **50.0% SR**
  - glm5_2_nv: 27req, 20 OK, 7 fail → **74.1% SR**

## 失败细节
| model | error_type | 数量 | root cause |
|---|---|---|---|
| dsv4p_nv | all_tiers_exhausted | 8 | big-input pre-empted (0 tier_attempts), breaker OPEN in R2243 window |
| glm5_2_nv | all_tiers_exhausted | 4 | big-input pre-empted (0 tier_attempts), budget tight at 34s |
| glm5_2_nv | zombie_empty_completion | 3 | NVCF function degradation (key_cycle=1-8) |

## 诊断
- R2243 (FAIL_N 3→5) deployed and breaker now CLOSED after big-input success — logs confirm
- glm5_2 ATE all big-input (316K-342K chars), 0 tier_attempts, duration 7-202s
- **NVU_TIER_BUDGET_GLM5_2_NV=34 = KEY_COOLDOWN_S(10) + UPSTREAM_TIMEOUT(24) — exact match, zero margin**
- KEY_COOLDOWN_S was 12 when R2237 set 34, now reduced to 10 (R2242) → actual constraint: 10+24=34
- Zero margin means any big-input glm5 request exceeding budget gets pre-empted
- glm5 zombies (3) are NVCF function degradation, not config-addressable

## 优化
**单参数**: `NVU_TIER_BUDGET_GLM5_2_NV`: **34 → 38** (+4s)

**理由**:
- 34 = KEY(10)+UPSTREAM(24) exact, zero margin for big-input requests
- 38 = KEY(10)+UPSTREAM(24)+4s buffer — allows one key attempt with 4s margin
- Non-big-input glm5 requests (no big-input breaker) are unaffected by the budget increase
- Big-input glm5 requests get 4s more budget to complete before pre-emption
- Budget safety: KEY(10)+TIER(0)+GLM5_2(38)=48 << TIER_TIMEOUT_BUDGET_S(157) — 109s margin
- Single parameter, low risk: only affects glm5_2_nv tier budget, not dsv4p or other tiers

**预算安全**:
- KEY_COOLDOWN_S=10, TIER_COOLDOWN_S=0, UPSTREAM_TIMEOUT=24
- NVU_TIER_BUDGET_GLM5_2_NV=38: KEY(10)+UPSTREAM(24)=34 → 4s margin ✅
- TIER_TIMEOUT_BUDGET_S=157: KEY(10)+TIER(0)+GLM5_2(38)=48 << 157 (109s margin) ✅
- NVU_TIER_BUDGET_DSV4P_NV=96: KEY(10)+UPSTREAM(24)*3=82+14=96 ✅

## 执行
```bash
ssh -p 222 opc_uname@100.109.153.83 \
  'sed -i "651s|\"34\"|\"38\"|" /opt/cc-infra/docker-compose.yml'

docker compose -f /opt/cc-infra/docker-compose.yml stop nv_gw && \
docker compose -f /opt/cc-infra/docker-compose.yml up -d nv_gw
```

✅ 验证: `docker exec nv_gw env | grep NVU_TIER_BUDGET_GLM5_2_NV` → `NVU_TIER_BUDGET_GLM5_2_NV=38`
✅ Health: `curl http://localhost:40006/health` → 200

## ⏳ 轮到HM1优化HM2