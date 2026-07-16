# R1647 — HM2→HM1: TIER_TIMEOUT_BUDGET_S 205→195 (-10s, trim kimi_nv failure path headroom)

## 数据 (HM1 post-R1646, 16h)

| Metric | Value |
|--------|-------|
| Total requests (post-R1646) | 3 |
| glm5_2_nv OK | 1 |
| glm5_2_nv zombie | 2 |
| dsv4p_nv | 0 (zero traffic) |
| kimi_nv 24h | 0 (zero traffic) |

### 24h pre-existing data (all pre-R1646)
| model | total | OK | SR% |
|-------|-------|-----|-----|
| dsv4p_nv | ~12 | ~7 | 58.3% |
| glm5_2_nv | ~121 | ~7 | 5.8% |

### 24h tier_attempts
| error_type | count |
|---|---|
| pexec_success | 258 |
| pexec_429 | 90 (24.3%) |
| pexec_SSLEOFError | 13 |
| pexec_empty_200 | 10 |

### 24h ATE (status=502)
| model | error_type | count | fallback_attempted |
|-------|------------|-------|---------------------|
| glm5_2_nv | zombie_empty_completion | 114 | 21 true / 93 false |
| dsv4p_nv | all_tiers_exhausted | 17 | 0 true |
| glm5_2_nv | all_tiers_exhausted | 16 | 0 true |

All 17 dsv4p ATE: `tiers_tried_count=1`, `fallback_actually_attempted=false` — tier breaks before peer-fallback is reached.

## 分析

Post-R1646 (16h): only 3 glm5_2_nv requests, zero dsv4p_nv/kimi_nv traffic. Peer-fallback clearing untested.

`TIER_TIMEOUT_BUDGET_S=205` is the global safety net used only by kimi_nv (no per-tier budget). All other tiers have their own budgets:
- dsv4p_nv: 78 (NVU_TIER_BUDGET_DSV4P_NV)
- glm5_2_nv: 120 (NVU_TIER_BUDGET_GLM5_2_NV)
- minimax_m3_nv: 100 (NVU_TIER_BUDGET_MINIMAX_M3_NV)

kimi_nv has **zero traffic in 24h** — effectively unused. 205→195 is a pure headroom trim.

## Budget safety

| scenario | cost | vs 195 |
|---|---|---|
| dsv4p_nv local + peer-fb | 78+72=150 | 150<195 ✓ (45s headroom) |
| glm5_2_nv local + peer-fb | 120+72=192 | 192<195 ✓ (3s headroom, tight but > 0) |
| kimi_nv 3 keys × 65s | ~195s | exact, FASTBREAK=1 breaks early |
| minimax_m3_nv | 100 | 100<195 ✓ |

## 修改

**HM1** `/opt/cc-infra/docker-compose.yml` line 489:
```
- TIER_TIMEOUT_BUDGET_S: "205"
+ TIER_TIMEOUT_BUDGET_S: "195"  # R1647
```

## 验证

- `docker compose up -d nv_gw` → container restarted ✓
- `docker exec nv_gw env | grep TIER_TIMEOUT_BUDGET_S` → `195` ✓
- Compose line 489 → `TIER_TIMEOUT_BUDGET_S: "195"` (matches container env) ✓
- `/health` → `{"status": "ok"}` ✓
- Core params: BUDGET=78, KEY=60, TIER=60, UPSTREAM=66, PEER_FALLBACK_TIMEOUT=72 all intact ✓

## 评判

预期: kimi_nv 失败路径略短10s (203→193ms benefit negligible since 0 traffic). 其他 tiers 不受影响 (own budgets). -10s 保守步长.

铁律: 只改HM1不改HM2 ✓ 单参数 ✓
## ⏳ 轮到HM1优化HM2
