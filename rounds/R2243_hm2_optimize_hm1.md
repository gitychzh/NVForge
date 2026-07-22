# R2243 (HM2→HM1): NVU_BIG_INPUT_FAIL_N 3→5 (+2)

## 6h 窗口数据
- **总请求**: 45req, 29 OK, 16 fail → **64.4% SR**
- **Per-model**:
  - dsv4p_nv: 16req, 8 OK, 8 fail → **50.0% SR**
  - glm5_2_nv: 29req, 21 OK, 8 fail → **72.4% SR**

## 失败细节
| model | error_type | 数量 | root cause |
|---|---|---|---|
| dsv4p_nv | all_tiers_exhausted | 8 | big-input 预缴 (0 tier_attempts), breaker OPEN |
| glm5_2_nv | all_tiers_exhausted | 4 | big-input 预缴 |
| glm5_2_nv | zombie_empty_completion | 4 | NVCF function degradation |

## 诊断
- 所有 8 个 dsv4p ATE 和 4 个 glm5_2 ATE 均为 **big-input breaker 预缴**:
  - `total_input_chars` > 315K (THRESHOLD=250K)
  - 0 tier_attempts rows (tier 从未被尝试)
  - duration_ms 5-94s (budget 耗尽在 breaker 等待)
  - `NVU_BIG_INPUT_FAIL_N=3` → 连续3次fail → breaker OPEN, 阻断后续所有 big-input
- dsv4p itself is healthy: 当 breaker CLOSED 时 big-input 请求仍成功 (200 OK, duration ~20-47s)
- glm5_2 zombie 4个: key_cycle=1-8, pexec timeout → SSLEOFError → 最终 all_keys_exhausted
- NVU_BIG_INPUT_THRESHOLD=250000 已升足够 (所有请求 > 315K), 不再 blanket-block
- FAIL_N=3 对 sporadic zombie ~1.5h fail 仍敏感

## 优化
**单参数**: `NVU_BIG_INPUT_FAIL_N`: **3 → 5** (+2)

**理由**:
- FAIL_N=5 需要连续5次 big-input fail 才 OPEN breaker
- dsv4p big-input 请求是间歇性的 (~1-2h apart), 非连续的 surge
- 5个连续fail已足够触发 breaker 于真正 chain-fail, 但避免 2-3 sporadic fail → OPEN
- COOLDOWN=2100s (35m) 仍有效: OPENER 后在35min内所有 big-input 直接返回 ATE → peer-fallback
- 单参数, 低风险: 不影响非-big-input 请求; 不修改任何 key/tier/budget 参数

**预算安全** (不改动, 仅确认):
- KEY_COOLDOWN_S=10, TIRED_COOLDOWN_S=0, UPSTREAM_TIMEOUT=24
- NVU_TIER_BUDGET_DSV4P_NV=96: KEY(10)+UPSTREAM(24)*3=82+14=96 ✅
- TIER_TIMEOUT_BUDGET_S=157: KEY(10)+TIER(0)+DSV4P(96)=106 << 157 (51s margin) ✅
- GLOBAL_NVU_GLM5_2_NV=34: KEY(12)+UPSTREAM(24)=36 → 34 紧 but ← 下一步可考虑

## 执行
```bash
ssh -p 222 opc_uname@100.109.153.83 \
  "sed -i '635s|      NVU_BIG_INPUT_FAIL_N: \"3\".*|      NVU_BIG_INPUT_FAIL_N: \"5\"  # R2243 (HM2->HM1): 3->5|' /opt/cc-infra/docker-compose.yml"

docker compose -f /opt/cc-infra/docker-compose.yml stop nv_gw && \
docker compose -f /opt/cc-infra/docker-compose.yml up -d nv_gw
```

✅ 验证: `docker exec nv_gw env | grep BIG_INPUT_FAIL_N` → `NVU_BIG_INPUT_FAIL_N=5`
✅ Health: `curl http://localhost:40006/health` → 200

## ⏳ 轮到HM1优化HM2