# R1723 — HM2优化HM1: NVU_TIER_BUDGET_DSV4P_NV 65→60 (-5s)

## 数据采集 (HM1)
- **6h窗口**: 62req/51OK(82.3%SR)/11 fail
  - 9 zombie_empty_completion (glm5_2_nv, 3-14s, 30min GFP cadence :03/:33)
  - 2 dsv4p_nv ATE 502 (69s, 70s; tiers_tried=1, 无 fallback)
- **Tier attempts**: 57 pexec_success, 4 pexec_SSLEOFError (glm5_2_nv), 1 pexec_429
- **OK duration**: max_ok=51.8s (glm5_2_nv), dsv4p OK=25.1s
- **ms_gw**: 0 activity (6h)
- **peer-fb**: 0 activity in logs, no TimeoutError
- **Last data**: 19:33 UTC (~8h quiet gap)

## 分析
- dsv4p ATE: 2 fail at 69-70s with tiers_tried=1, budget was 65s
  - Key1 exhausts at ~65s (UPSTREAM_TIMEOUT=55 + NVCF response ~10s SSLEOF)
  - Budget 65→60: key1 still gets 55s, key2 only gets 5s instead of 10s → saves 5s/ATE
  - 节省5s让peer-fb多5s: 140-60=80s ≥ 72 (HM2 BUDGET 70+2) ✓ (+8s margin vs 75s)
- glm5_2 zombie: 9x at 3-14s — NVCF empty completion, not config fixable (server-side GFP clock)
- 8h quiet gap: likely overnight low-traffic period, no new data since
- 单参数, trimming trajectory continues

## 修改
- `NVU_TIER_BUDGET_DSV4P_NV`: 65 → 60 (-5s)
- HM1 docker-compose.yml line 652
- 单参数; 铁律:只改HM1不改HM2

## 预算验证
| 路径 | 计算 | 约束 | 状态 |
|------|------|------|------|
| dsv4p ATE→peer-fb | 60+125=185→cap 140 | peer-fb 得 80s ≥ 72 (HM2 70+2) ✓ | ✅ |
| glm5_2 BIG_INPUT→peer-fb | 0+125=125 | < 140 ✓ | ✅ |
| OK path | max_ok=51.8s | < 140 safe (88s headroom) | ✅ |

## 验证
- `docker compose up -d nv_gw` → Started ✓
- `docker exec nv_gw env`: NVU_TIER_BUDGET_DSV4P_NV=60 ✓
- `curl /health`: status=ok ✓
- 无漂移: compose = container (60/60) ✓
## ⏳ 轮到HM1优化HM2
