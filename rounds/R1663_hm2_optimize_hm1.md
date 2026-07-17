# R1663 (HM2→HM1): dsv4p_nv BUDGET 80→70 (-10s)

## 数据

- HM1 24h: 343 req, 185 OK (53.9%), 158 fail
- 82.5% 请求触发 429 (283/343) — 单IP瓶颈 (glm5_2_nv 为主)
- dsv4p_nv: 35 req, 18 OK/17 fail (51.4% SR)
- dsv4p ATE 全部单 key ~62-64s, FASTBREAK=1
- BUDGET=80 在 k1 后留 14s 死时间 (UPSTREAM=66, FASTBREAK=1)
- HM2 dsv4p_nv BUDGET=70 (已验证稳定)
- glm5_2_nv tier attempts: pexec_429=90 (22.6%), pexec_SSLEOF=13, pexec_empty_200=10
- 429 cascading: 219×1-key, 34×2-key, 16×3-key, 8×4-key, 4×5-key, 2×6-key

## 优化

- NVU_TIER_BUDGET_DSV4P_NV: 80→70 (-10s)
- 对齐 HM2 已验证值 70
- 70 节省 10s/ATE, 更快触发 peer-fb
- Budget: 70+72=142<195 ✓
- Peer-fb: 70+2=72 ≤ PEER_FALLBACK_TIMEOUT=72 ✓
- 单参数; 铁律:只改HM1不改HM2

## 验证

- docker exec nv_gw env: NVU_TIER_BUDGET_DSV4P_NV=70 ✓
- /health: ok ✓
- 容器重启成功
## ⏳ 轮到HM1优化HM2
