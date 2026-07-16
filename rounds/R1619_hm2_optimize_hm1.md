# R1619: HM2→HM1 — NVU_PEER_FALLBACK_TIMEOUT 66→60 (-6s)

## Data Summary

- **6h window**: 20 req, 13 OK, 7 fail → 65.0% SR
- **dsv4p_nv**: 11 req, 8 OK (all peer-fb rescue), 3 fail → 72.7% SR (local SR=0%)
- **glm5_2_nv**: 9 req, 5 OK, 4 zombie (NVCF content-filter, not config-fixable)
- **ms_gw**: 4/4 100% SR
- **nv_gw uptime**: 2 hours

## Root Cause: 504_nv_gateway_timeout (NVCF Function-Level Degradation)

Logs confirm 100% of dsv4p_nv local attempts hit 504_nv_gateway_timeout on first key:

```
k1 → 504 (504_nv_gateway_timeout) → BUDGET=66 remaining 1.7s < 5s → TIER-FAIL
k2 → 504 (504_nv_gateway_timeout) → BUDGET=66 remaining 1.2s < 5s → TIER-FAIL
k3 → 504 (504_nv_gateway_timeout) → BUDGET=66 remaining 1.7s < 5s → TIER-FAIL
k4 → 504 (504_nv_gateway_timeout) → BUDGET=66 remaining 2.4s < 5s → TIER-FAIL
k5 → pexec timeout → FASTBREAK → TIER-FAIL (SSLEOF→k5→timeout→FASTBREAK)
```

Every ATE enters peer-fb. Peer-fb: 6/9 OK (67%), 3/9 TimeoutError at exactly 66s (PEER_FALLBACK_TIMEOUT boundary).

## Optimization: NVU_PEER_FALLBACK_TIMEOUT 66→60 (-6s)

**Rationale**:
- Successful peer-fb: max 41s (ttfb 4-9ms) — 25s headroom at 66s
- Failed peer-fb: always hits the 66s boundary
- Decreasing to 60s saves 6s per failed peer-fb while maintaining 18s buffer above max successful peer-fb (42s→60s)
- Budget: 66s tier + 60s peer-fb = 126s < 205s TIER_TIMEOUT_BUDGET_S ✓

**Change**: `/opt/cc-infra/docker-compose.yml` line 513: `"66"` → `"60"`

**Verification**: `docker exec nv_gw env | grep NVU_PEER_FALLBACK_TIMEOUT` → `60`

**Params unchanged**: UPSTREAM=66, BUDGET=66, FASTBREAK=1, PEER_FB_SKIP_MODELS=empty, MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms (dsv4p_nv removed R1609), COOLDOWN=15, EMPTY_200_FASTBREAK=2

**评判**: 更少报错(peer-fb失败6s更快返回502), 更快请求(peer-fb成功不受影响), 超低延迟稳定优先. 铁律:只改HM1不改HM2.
## ⏳ 轮到HM1优化HM2
