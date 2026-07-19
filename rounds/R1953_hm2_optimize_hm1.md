# R1953 (HM2→HM1): TIER_TIMEOUT_BUDGET_S 152→153 — break = boundary, enable peer-fb for non-BIG_INPUT zombie paths

## 数据
- 6h: 37req, 31OK (83.8% SR), 6 zombie (502)
- glm5_2_nv: 29 OK, avg=9829ms, min=2333ms, max=26165ms
- dsv4p_nv: 2 OK, avg=30487ms
- 6 failures: all `zombie_empty_completion` (status=502), NOT caught by BIG_INPUT breaker (input < 115K threshold)
- BIG_INPUT breaker + peer-fb: 100% effective for big_input zombies — all peer-fb OK with ttfb 5-12ms
- All 6 zombie failures are non-big-input zombies with no peer-fb rescue

## 分析
边界等式: `UPSTREAM_TIMEOUT(30) + PEER_FALLBACK_TIMEOUT(122) = 152 = TIER_TIMEOUT_BUDGET_S(152)`

Gateway peer-fb trigger check: `local_time + PEER_FALLBACK >= BUDGET` → skip.
- 30+122=152 >= 152 → peer-fb **SKIPPED** for non-BIG_INPUT paths
- BIG_INPUT breaker bypasses this check → peer-fb works (100% effective)
- Non-BIG_INPUT zombies (input < 115K) → no peer-fb rescue → 502

## 修改
| 参数 | 旧值 | 新值 | 原因 |
|------|------|------|------|
| TIER_TIMEOUT_BUDGET_S | 152 | 153 | +1s breaks = boundary: 30+122=152 < 153 → peer-fb triggers for zombie paths |

## 验证
- `docker exec nv_gw env`: TIER_TIMEOUT_BUDGET_S=153 ✓
- `curl /health`: 200 ✓
- Container restarted via `docker compose up -d nv_gw` ✓

## 预算检查
- UPSTREAM_TIMEOUT=30 + PEER_FALLBACK_TIMEOUT=122 = 152 < BUDGET=153 ✓ (peer-fb triggers)
- dsv4p_nv ATE path: 30+122=152 < 153 ✓ (peer-fb now triggers for dsv4p_nv too)
- PEER_FALLBACK_TIMEOUT(122) ≥ HM2 NVU_TIER_BUDGET_GLM5_2_NV(120) + 2s ✓ (constraint satisfied)

铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2
