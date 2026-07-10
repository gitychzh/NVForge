# R1071: HM2→HM1 — TIER_TIMEOUT_BUDGET_S 110→132 (+22s)

## 数据摘要 (6h window, HM1)
- 总请求: 59 req / 54 OK (91.5% SR) / 5 ATE
- glm5_2_nv: 57 req / 54 OK (94.7%) / 3 NVStream_TimeoutError (~100s, code-level)
- dsv4p_nv: 2 req / 0 OK (0.0%) / 2 all_tiers_exhausted (110s, no fallback)
- 成功延迟: avg 14,856ms, min 3,409ms, max 56,413ms
- 零 fallback 发生 (0 fallback_occurred=true)
- 1h: 5/5 100% SR

## 问题诊断
R1070 将 `NVU_PEER_FALLBACK_TIMEOUT` 从 45→66s，对齐 HM2 UPSTREAM_TIMEOUT=66s。
但 `TIER_TIMEOUT_BUDGET_S=110` 在第一次 UPSTREAM=66s 尝试后仅剩 44s (110-66=44)。
44s < PEER_FALLBACK_TIMEOUT=66s，导致 peer-fb 永远无法触发。
dsv4p_nv 的 2 个 ATE 全部在 110s 耗尽 budget，peer-fb 从未尝试。

## 修改
`TIER_TIMEOUT_BUDGET_S: 110 → 132` (+22s)

**理由**: 132 = 66 (UPSTREAM) + 66 (PEER_FB)，给 peer-fb 完整单 key 窗口。
预算 132 < 300s (openclaw timeout) 安全。

## 验证
- YAML OK
- docker compose stop + up → Recreated/Started
- `docker exec nv_gw env | grep TIER_TIMEOUT_BUDGET_S` → 132
- `/health` → OK, 5 keys, 4 models

## 参数变更
| 参数 | 旧值 | 新值 | 变化 |
|------|------|------|------|
| TIER_TIMEOUT_BUDGET_S | 110 | 132 | +22s |

单参数; 铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2