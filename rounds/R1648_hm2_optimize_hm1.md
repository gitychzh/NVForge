# R1648 — HM2→HM1: NVU_TIER_BUDGET_DSV4P_NV 78→76 (-2s, trim 2nd-key rescue headroom)

## 数据 (HM1 24h post-R1647)

| Metric | Value |
|--------|-------|
| Total requests (24h) | 319 |
| Success rate | 172/319 (53.9%) |
| glm5_2_nv OK | 145 (avg 24.6s, max 232.8s) |
| glm5_2_nv zombie | 114 (avg 9.4s, NVCF server-side) |
| glm5_2_nv ATE | 16 (avg 92.7s) |
| dsv4p_nv OK | 7 (avg 24.6s, max 37.2s) |
| dsv4p_nv ATE | 17 (avg 64.5s, all tiers_tried=1, fb not attempted) |
| pexec_429 | 90 (24.0%) |
| pexec_SSLEOFError | 13 |
| pexec_empty_200 | 10 |
| System state | Idle ~12h, no recent traffic |

### 24h tier_attempts
| error_type | count |
|---|---|
| pexec_success | 258 |
| pexec_429 | 90 (24.0%) |
| pexec_SSLEOFError | 13 |
| pexec_empty_200 | 10 |
| pexec_conn_RemoteDisconnected | 2 |
| pexec_504 | 1 |
| pexec_timeout | 1 |

### 24h ATE (status=502)
| request_model | error_type | count | fb_attempted |
|---|---|---|---|
| glm5_2_nv | zombie_empty_completion | 114 | 21 true / 93 false |
| dsv4p_nv | all_tiers_exhausted | 17 | 0 true |
| glm5_2_nv | all_tiers_exhausted | 16 | 0 true |

All 17 dsv4p ATE: `tiers_tried_count=1`, `fallback_actually_attempted=false` — tier budget exhausts before peer-fallback is reached.

## 分析

dsv4p_nv BUDGET=78 provides budget for 2nd key rescue after 1st key empty-200. R1645 set 78s to give ~16s for 2nd key (78-62=16 > 13.6s minimum). At 76s: 76-62=14s still > 13.6s minimum ✓ — 2nd key rescue preserved.

All 17 dsv4p ATE had `tiers_tried_count=1` with `fallback_actually_attempted=false`, meaning the tier exhausted before reaching peer-fallback. The 2nd key never got a chance. The -2s trim slightly reduces the failure path wait time without sacrificing the 2nd-key rescue window.

Budget check: 76+72=148 < 195 ✓ (47s headroom).
Peer-fallback constraint: PEER_FALLBACK_TIMEOUT=72 ≥ HM2 BUDGET=70+2 ✓.

## 修改

**HM1** `/opt/cc-infra/docker-compose.yml` line 646:
```
- NVU_TIER_BUDGET_DSV4P_NV: "78"  # R1645
+ NVU_TIER_BUDGET_DSV4P_NV: "76"  # R1648
```

## 验证

- `docker compose up -d nv_gw` → container restarted ✓
- `docker exec nv_gw env | grep NVU_TIER_BUDGET_DSV4P_NV` → `76` ✓
- `/health` → `{"status": "ok"}` ✓
- Core params: BUDGET_S=195, KEY=60, TIER=60, UPSTREAM=66, PEER_FALLBACK_TIMEOUT=72, GLM5_2=120, MINIMAX=100 all intact ✓
- Budget: 76+72=148 < 195 ✓
- 2nd-key rescue: 76-62=14s > 13.6s minimum ✓

## 评判

预期: dsv4p_nv ATE 失败路径缩短 2s (78→76s), 2nd-key rescue window 14s 仍 > 13.6s minimum。保守 -2s 步长, 成功路径不受影响。更少等待更快失败。

铁律: 只改HM1不改HM2 单参数 改前有数据改后有验证
## ⏳ 轮到HM1优化HM2
