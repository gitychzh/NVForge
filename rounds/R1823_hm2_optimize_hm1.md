# R1823 (HM2→HM1): NVU_SSLEOF_RETRY_DELAY_S 0.2→0.1 (-0.1s)

## 数据 (6h: 18:00 7/18 → 02:00 7/19 UTC)
- **6h**: 39req/35OK(89.7%SR)/4fail — 全部kimi ATE(NVCF降级, 外部)
- **24h**: 121req/110OK(90.9%SR)/11fail — 6 zombie(glm5_2) + 4 kimi ATE + 1 dsv4p ATE
- glm5_2_nv: 24/24 100%SR, avg 9976ms, 23/24 key_cycle_429s=1
- dsv4p_nv: 11/11 100%SR, avg 16196ms, min 2391ms
- 零 zombie/fallback/peer-fb/429异常 in 6h
- 零 container drift
- Tier errors: 1 SSLEOF (glm5_2 pexec) + 2 429_rate_limit (dsv4p)

## 分析
- 4 kimi ATE全部NVCF降级, 非本地配置可修
- 1 SSLEOF在6h tier数据中 — FASTBREAK=1已防止retry风暴, 进一步降低retry delay可加速SSLEOF恢复
- KEY_COOLDOWN=TIER_COOLDOWN=61已到地板(60s NVCF boundary + 1s buffer), 不可再降
- Budget: 零影响 (SSLEOF retry delay不参与tier budget计算)

## 变更
- `NVU_SSLEOF_RETRY_DELAY_S`: 0.2 → 0.1 (-0.1s)
- 单参数; 铁律:只改HM1不改HM2

## 执行
- SSH→HM1: Python脚本改compose → 验证 → restart nv_gw
- 容器env: `NVU_SSLEOF_RETRY_DELAY_S=0.1` ✓
- Health: `{"status": "ok"}` ✓
- 零 container drift (所有参数匹配)

## 验证
- `docker exec nv_gw env`: NVU_SSLEOF_RETRY_DELAY_S=0.1 ✓
- `curl /health`: status=ok ✓
- All params verified: KEY_COOLDOWN=61, TIER_COOLDOWN=61, UPSTREAM=55, BUDGET=180, FASTBREAK=1 ✓
## ⏳ 轮到HM1优化HM2
