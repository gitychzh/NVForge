# R2395 (HM2→HM1): NVU_TIER_BUDGET_GLM5_2_NV 210→230

## 改前数据 (2026-07-27 06:50 UTC)

### nv_gw logs (2000 lines, post-R2394 deploy)

```
[06:33:22.6] [NV-REQ] mapped_model=glm5_2_nv stream=True (2 concurrent)
[06:33:29.2] [NV-SUCCESS] tier=glm5_2_nv k4 succeeded on first attempt (6.7s)
[06:33:47.7] [NV-TIMEOUT] tier=glm5_2_nv k3: attempt=25029ms
[06:34:12.0] [NV-TIMEOUT] tier=glm5_2_nv k4: attempt=24360ms
[06:34:36.9] [NV-TIMEOUT] tier=glm5_2_nv k5: attempt=24889ms
[06:35:02.0] [NV-TIMEOUT] tier=glm5_2_nv k1: attempt=25037ms
[06:35:03.4] [NV-COOLDOWN] tier=glm5_2_nv k2 marked cooling after 429
[06:35:28.1] [NV-TIMEOUT] tier=glm5_2_nv k3: attempt=24743ms
[06:35:53.1] [NV-TIMEOUT] tier=glm5_2_nv k4: attempt=24959ms
[06:35:53.1] [NV-TIER-FAIL] tier=glm5_2_nv all 5 keys failed: 429=1, empty200=0, timeout=6, other=0, elapsed=150462ms
[06:57:27.5] [NV-SUCCESS] tier=kimi_nv k1 succeeded after 1 cycle
[07:00:18.0] [NV-SUCCESS] tier=kimi_nv k1 succeeded on first attempt
```

### Request Summary (2000 lines)

| Model | SUCCESS | TIER-FAIL | ALL-TIERS-FAIL |
|-------|---------|-----------|-----------------|
| glm5_2_nv | 1 | 1 | 1 |
| kimi_nv | 2 | 0 | 0 |
| dsv4p_nv | 0 | 0 | 0 |

### glm5_2_nv ATE Detail

```
elapsed=150462ms (150s)
keys_tried=5
timeout=6 (6 pexec timeouts across 5 keys)
429=1 (k2, attempt 5/7)
empty200=0
other=0

Key sequence: k3→k4→k5→k1→k2(429)→k3→k4
All timeouts: ~24-25s per attempt (consistent NVCF pexec timeout)
```

### kimi_nv

- 2/2 SUCCESS, both k1
- One on first attempt, one after 1 cycle
- No issues

### Current HM1 env (nv_gw)

```
NVU_TIER_BUDGET_GLM5_2_NV=210
NVU_TIER_BUDGET_KIMI_NV=380
NVU_TIER_BUDGET_DSV4P_NV=265
NVU_PEXEC_TIMEOUT_FASTBREAK=6
KEY_COOLDOWN_S=10
TIER_COOLDOWN_S=0
UPSTREAM_TIMEOUT=24
NVU_STREAM_FIRST_BYTE_DEADLINE_S=16
NVU_STREAM_TOTAL_DEADLINE_S=90
TIER_TIMEOUT_BUDGET_S=475
CC4101 PROXY_TIMEOUT=420
```

## 问题分析

### glm5_2_nv ATE: Genuine NVCF Cluster Issue, Not Budget

The ATE consumed 150s out of 210s budget — budget was NOT the bottleneck. All 5 keys were tried (7 attempts: 6 timeout + 1 429). The consistent ~24-25s per-attempt timeout pattern indicates a genuine NVCF pexec timeout cluster (all NVCF function instances unresponsive for ~2.5 minutes).

### Why 210→230?

Even though this specific ATE was not budget-limited, the margin is thin:

- PER_KEY = 210/5 = 42s. With 24s pexec + 10s KEY_COOLDOWN = 34s/cycle. 210s = 5 full cycles + 40s headroom.
- If a future cluster outage lasts 8-9 attempts (instead of 7), 210s headroom is only 40s → may not fit
- 230s = 5 full cycles + 60s headroom → allows 1-2 extra retry attempts
- 230/5 = 46s per key, 22s margin (vs 18s at 210)

### Risk Assessment

- **No impact on kimi_nv** (380s budget, independent)
- **No impact on dsv4p_nv** (265s budget, independent)
- **No impact on cc4101** (PROXY_TIMEOUT=420s, well above 230s)
- **No impact on HM2** (single param, only HM1)
- **Conservative**: +20s on a 210s baseline = 9.5% increase

## 修改

### docker-compose.yml (HM1, /opt/cc-infra)

```yaml
# Before:
- NVU_TIER_BUDGET_GLM5_2_NV=210  # R2291 (HM2→HM1): 200→210

# After:
- NVU_TIER_BUDGET_GLM5_2_NV=230  # R2395 (HM2→HM1): 210→230
```

## 验证

1. `docker compose up -d nv_gw` → Container nv_gw Started ✅
2. `curl http://localhost:40006/health` → `{"status": "ok"}` ✅
3. `docker exec nv_gw env | grep TIER_BUDGET_GLM5` → `NVU_TIER_BUDGET_GLM5_2_NV=230` ✅

## 预期改善

- glm5_2_nv ATE 在真实 NVCF 集群故障时多 1-2 次重试机会
- 不影响 kimi_nv/dsv4p_nv 模型
- 保守 +20s，仅 9.5% 预算增加

## ⏳ 轮到HM1优化HM2