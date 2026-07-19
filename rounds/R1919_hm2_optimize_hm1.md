# R1919 (HM2→HM1): NVU_TIER_BUDGET_GLM5_2_NV 55→50 (-5s)

## 数据 (6h window, 19:00 UTC)
- 39req/27OK(69.2%SR)/12 fail
- 9 zombie_empty_completion (glm5_2_nv, all >127K chars input, BIG_INPUT breaker active on 9/10)
- 2 real ATE (dsv4p_nv, 2-3ms — all keys on cooldown, tier exhausted on arrival)
- 1 zombie dsv4p_nv (129K chars, BIG_INPUT breaker caught)
- dsv4p_nv OK: 4/4, avg=8930ms, max=19559ms << 30s safe
- glm5_2_nv OK: 23/23, avg=8508ms, max=27809ms << 30s safe
- 1h window: 4req/2OK(50.0%), 2 zombie glm5_2
- Tier attempts: glm5_2 pexec_success=22, pexec_429=2, SSLEOFError=1, pexec_timeout=1; dsv4p: 0 tier attempts

## 分析
- Dominant failure: glm5_2_nv zombies (9/12 = 75%), all GPU-level NVCF degradation (empty200)
- BIG_INPUT breaker catches most (>115K cutoff), but zombie still uses full tier budget
- With FASTBREAK=1 and UPSTREAM=30, tier budget is effectively capped at 30s per attempt
- NVU_TIER_BUDGET_GLM5_2_NV=55 is oversized — OK max=27.8s < 30s, zombie path already killed by FASTBREAK=1 at ~30s
- 55→50 saves 5s on zombie/ATE fail paths without affecting success path
- Budget: UPSTREAM=30 + PEER_FALLBACK=122 = 152 < 153 (TIER_TIMEOUT_BUDGET=153, 1s margin)
- 单参数对; 铁律:只改HM1不改HM2

## 修改
- `NVU_TIER_BUDGET_GLM5_2_NV: "55"` → `"50"` (HM1 /opt/cc-infra/docker-compose.yml line 649)

## 验证
- `docker exec nv_gw env | grep NVU_TIER_BUDGET_GLM5_2_NV`: 50 ✓
- `curl /health`: status=ok ✓
- All key env params match compose ✓
- docker logs nv_gw: clean startup, no errors ✓
## ⏳ 轮到HM1优化HM2
