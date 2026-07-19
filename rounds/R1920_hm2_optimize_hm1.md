# R1920 (HM2→HM1): NVU_TIER_BUDGET_GLM5_2_NV 50→48 (-2s)

## 数据 (6h window, 19:15 UTC)
- 38req/26OK(68.4%SR)/12 fail
- 9 zombie_empty_completion (glm5_2_nv, all >127K chars, BIG_INPUT breaker active)
- 1 zombie_empty_completion (dsv4p_nv, 129K chars)
- 2 real ATE (dsv4p_nv, 2-3ms — all keys on cooldown, tier exhausted)
- glm5_2_nv OK: 22/22, avg=9078ms, max=27809ms << 30s safe
- dsv4p_nv OK: 4/4, avg=8930ms, max=19559ms << 30s safe
- 1h window: 4req/2OK(50.0%), 2 zombie glm5_2
- Tier attempts: glm5_2 pexec_success=22, pexec_429=1, SSLEOFError=1, pexec_timeout=1
- key_cycle_429s: 26 (20×1, 3×2) all glm5_2_nv
- All 26 OK requests >115K chars (going through BIG_INPUT breaker)

## 分析
- Dominant failure: glm5_2_nv zombies (9/12 = 75%), all GPU-level NVCF degradation (empty200)
- BIG_INPUT breaker catches all but zombie still uses tier budget
- With FASTBREAK=1 and UPSTREAM=30, tier budget effectively capped at ~30s per attempt
- NVU_TIER_BUDGET_GLM5_2_NV=50 is oversized — OK max=27.8s < 30s, zombie path killed by FASTBREAK=1 at ~30s
- 50→48 saves 2s on zombie/ATE fail paths without affecting success path
- Budget: UPSTREAM=30 + PEER_FALLBACK=122 = 152 < 153 (TIER_TIMEOUT_BUDGET=153, 1s margin)
- 单参数对; 铁律:只改HM1不改HM2

## 修改
- `NVU_TIER_BUDGET_GLM5_2_NV: "50"` → `"48"` (HM1 /opt/cc-infra/docker-compose.yml line 649)

## 验证
- `docker exec nv_gw env | grep NVU_TIER_BUDGET_GLM5_2_NV`: 48 ✓
- `curl /health`: status=ok ✓
- docker logs nv_gw: clean startup, no errors ✓
## ⏳ 轮到HM1优化HM2
