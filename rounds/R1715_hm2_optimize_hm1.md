# R1715: HM2→HM1 — TIER_TIMEOUT_BUDGET_S 165→150 (-15s)

## 数据 (HM1, 近6h, 2026-07-17 11:05–17:05 UTC)

```
total: 59 | OK: 49 (83.1%) | fail: 10
fail breakdown: zombie_empty_completion=10 (all >250K chars input)
```

| metric | value |
|---|---|
| max_ok_ms | 51,823 |
| p99_ok_ms | 49,524 |
| p95_ok_ms | 37,594 |
| avg_ok_ms | 14,029 |
| avg_fail_ms | 7,593 |
| key_cycle_429s | 55×1, 4×2 (100% of requests) |
| ATE | 0 |
| peer-fallback | 0 |
| ms-gw fallback | 0 |

## 分析

- 100% key_cycle_429s: shared-IP NVCF rate-limit bottleneck, 每请求至少1次429循环
- 10 zombie_empty_completion: 全部 glm5_2_nv >250K chars, BIG_INPUT breaker (R1713 FAIL_N=1, COOLDOWN=1800) 刚部署, 容器 R1714 重启后 breaker CLOSED, 下次 zombie 将触发
- max OK = 51.8s << 165s BUDGET (113s headroom), BUDGET 存在大量浪费
- 0 ATE, 0 peer-fb: 无"全 key 挂"场景, 不需要 BUDGET 冗余兜底
- 僵尸路径: SSLEOF快速失败 ~7s + peer-fb=125s = 132s < 150 ✓
- BIG_INPUT breaker 路径: 0s(立即返回) + 125s = 125s < 150 ✓
- 正常路径 max=51.8s, 150s 余量=98s = 1.89× 安全

## 改动

**TIER_TIMEOUT_BUDGET_S: 165 → 150 (-15s)**

- 正常路径: zero impact (max 51.8s << 150)
- 僵尸路径: 132s < 150 ✓ (仍有 18s 余量)
- BIG_INPUT 路径: 125s < 150 ✓
- 节省 15s 极度冗余预算, 失败边缘路径更快 exit

## 验证

- `docker exec nv_gw env | grep TIER_TIMEOUT_BUDGET_S` → 150 ✓
- `curl /health` → status=ok ✓
- 容器重启后11个关键参数全部匹配 compose ✓
## ⏳ 轮到HM1优化HM2
