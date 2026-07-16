# R1652 (HM2→HM1): NVU_TIER_BUDGET_DSV4P_NV 76→90 (+14s)

## 数据采集 (HM1, 6h window, 2026-07-17 04:40 UTC)

### 请求统计
| Model | Total | OK | Fail | SR | Avg Lat | P50 | P95 |
|-------|-------|-----|------|-----|---------|-----|-----|
| dsv4p_nv | 12 | 7 | 5 | 58.3% | 40.3s | 37.0s | 63.1s |
| glm5_2_nv | 18 | 9 | 9 | 50.0% | 6.8s | 6.3s | 13.3s |

### 错误分布
- zombie_empty_completion: 9 (all glm5_2, avg 7.1s)
- all_tiers_exhausted: 5 (all dsv4p, avg 62.3s, NULL key_idx)

### 24h 统计
- dsv4p_nv: 35req/18OK(51.4%)
- glm5_2_nv: 292req/158OK(54.1%)

### HM1 当前配置
- NVU_TIER_BUDGET_DSV4P_NV=76
- PEER_FALLBACK_TIMEOUT=72
- TIER_TIMEOUT_BUDGET_S=195
- UPSTREAM_TIMEOUT=66

### HM2 参考配置
- NVU_TIER_BUDGET_DSV4P_NV=70
- PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv

## 根因分析

dsv4p ATE avg 62.3s: 5 key全部empty200, tier budget 76s用尽时peer-fallback仅余~14s (76-62=14s).
但HM2的dsv4p budget=70s, peer-fallback需要至少70+2=72s才能完成key cycle.
14s << 72s → peer-fallback永不触发 (tier budget先砍断).

## 优化方案

NVU_TIER_BUDGET_DSV4P_NV: 76→90 (+14s)

- 90s gives peer-fallback ~28s window (90-62=28s) after key exhaustion
- Peer-fallback timeout=72s now has a chance to fire (28s vs HM2 BUDGET 70s still tight but better than 14s)
- Budget check: 90+72=162 < 195 ✓
- Conservative +14s step — preserve 33s headroom for other models

## 执行

1. SSH到HM1, 修改 /opt/cc-infra/docker-compose.yml line 646
2. docker compose up -d nv_gw → 容器重启
3. 验证: docker exec nv_gw env → NVU_TIER_BUDGET_DSV4P_NV=90 ✓
4. 健康检查: {"status":"ok"} ✓

## 单参数; 铁律:只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
