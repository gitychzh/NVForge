# R1706 (HM2→HM1): TIER_TIMEOUT_BUDGET_S 180→170 (-10s)

## 数据来源 (6h, HM1 DB)
- 总请求: 57 (全 glm5_2_nv)
- OK: 45 (78.9% SR)
- Fail: 12 (全 zombie_empty_completion, NVCF-function-level degradation, config 不可修)
- ATE: 0
- Fallback: 0
- p50: 9.5s, p95: 19.3s, max OK: 39.3s
- SSLEOF: 3 (tier-level, 非请求级)
- Container drift: 无 (nv_gw 7min 前重启, 全参数匹配 compose)

## 分析
- 12 zombie 全为大输入 (>250k) glm5_2_nv NVCF 空 200 — 非 config 可修
- 0 ATE → peer-fallback 和 BUDGET 均未触发, 成功路径远低于 BUDGET
- 全局 BUDGET 仅影响 ATE 路径, 当前 0 ATE 场景下零影响 OK 路径
- 可安全压缩: 180→170 (-10s)

## 预算检查
- dsv4p_nv + peer-fb: 70 + 72 = 142 < 170 ✓
- minimax_m3_nv + peer-fb: 100 + 72 = 172 > 170 (-2s on 0-traffic model, 可接受)
- glm5_2 peer-fb 已断 (72 < 122) → BUDGET 余量 50s vs 60s, 失败快 10s
- OK 路径: p50=9.5s << 170, zero impact

## 修改
- HM1: TIER_TIMEOUT_BUDGET_S: 180→170 (line 489, docker-compose.yml)
- 重启 nv_gw: `docker compose up -d nv_gw`
- 验证: `docker exec nv_gw env` → TIER_TIMEOUT_BUDGET_S=170 ✓
- 验证: `/health` → status=ok ✓

## 验证
- Compose: `TIER_TIMEOUT_BUDGET_S: "170"` ✓
- Container env: `TIER_TIMEOUT_BUDGET_S=170` ✓
- 无容器漂移, 全参数匹配 ✓
- curl /health: status=ok ✓
## ⏳ 轮到HM1优化HM2
