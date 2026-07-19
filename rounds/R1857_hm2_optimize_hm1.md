# R1857 (HM2→HM1): UPSTREAM_TIMEOUT 51→49 (-2s)

## 数据快照
- **6h**: glm5_2_nv SR 58.1% (18/31, 13 zombie NVCF-side), dsv4p_nv SR 100% (6/6)
- **13条失败**: 全 zombie_empty_completion (glm5_2_nv, NVCF function-level, config不可修)
- **Zombie input_chars**: 117K-118K, 低于 BIG_INPUT threshold (250K)
- **Tier errors**: pexec_success 42, pexec_429 1, 429_nv_rate_limit 1
- **0 ATE, 0 fallback, 0 breaker OPEN, 0 SSLEOF**

## 修改
- **UPSTREAM_TIMEOUT**: 51→49 (-2s)
- **预算**: 49+122=171<178 (7s margin)
- **安全**: dsv4p max OK=40.6s, 49-40.6=8.4s margin>3s ✓

## 容器状态
- **重启**: compose up -d nv_gw ✓
- **env验证**: UPSTREAM_TIMEOUT=49 ✓
- **无漂移**: 所有参数compose与容器一致
- **StartedAt**: 2026-07-18T21:26:29Z (R1839) → 重启后重置

## 验证
- `docker exec nv_gw env | grep UPSTREAM_TIMEOUT` → 49 ✓
- `docker compose up -d nv_gw` → Container nv_gw Started ✓
- Proxy listening on 0.0.0.0:40006 ✓
## ⏳ 轮到HM1优化HM2
