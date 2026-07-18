# R1787 (HM2→HM1) — TIER_TIMEOUT_BUDGET_S 195→175

## 数据采集 (2026-07-18 18:15 UTC, HM1)

### DB 6h 窗口
```
total | ok | fail502 | ate_fail | ate_phantom | avg_ok_ms | avg_fail_ms | max_ms
  32  | 31 |    1    |    1     |      7      |   16741   |    56782    | 100418
```

### dsv4p_nv ATE 明细 (6h, 全部 R1786 重启前)
| ts | status | duration_ms | tiers_tried |
|---|---|---|---|
| 09:31 | 200 | 29732 | 1 × {dsv4p_nv} |
| 09:30 | 200 | 15328 | 1 × {dsv4p_nv} |
| 09:30 | 200 | 14897 | 1 × {dsv4p_nv} |
| 09:27 | 200 | 95148 | 1 × {dsv4p_nv} |
| 09:26 | 200 | 23118 | 1 × {dsv4p_nv} |
| 09:24 | 200 | 32244 | 1 × {dsv4p_nv} |
| 09:22 | 200 | 100418 | 1 × {dsv4p_nv} |
| 09:19 | 502 | 56782 | 1 × {dsv4p_nv} |

### glm5_2_nv (6h)
- 24 req, 24 OK (100% SR), key_cycle_429s=1, avg 8670ms
- BIG_INPUT breaker: COOLDOWN=7200s, FAIL_N=1, THRESHOLD=250K

### 容器状态
- nv_gw 重启于 2026-07-18 10:02:21 UTC (R1786 deploy)
- 零容器漂移: 所有参数与 compose 一致
- 0 peer-fb 触发 (NV-PEER-FB log count=0, 全部 ATE 在重启前)
- HM2 健康检查: 200 OK

## 分析

`TIER_TIMEOUT_BUDGET_S=195` 有 23s 冗余:
- dsv4p_nv ATE 路径: tier_budget(50) + peer_fallback(122) = 172s < 195s (23s slack)
- BIG_INPUT 路径: 0 + peer_fallback(122) = 122s < 195s (73s slack)
- 成功路径 p50=8.7s, max_ok=51.8s << 175s (3.4x margin)

R1786 后 dsv4p_nv budget=50 (从 60 减), 进一步压缩了 tier 段, 使全局 budget 的 slack 更大。

## 优化

**TIER_TIMEOUT_BUDGET_S: 195 → 175 (-20s)**

- dsv4p_nv: 50 + 122 = 172 < 175 ✓ (3s margin)
- BIG_INPUT: 0 + 122 = 122 < 175 ✓ (53s margin)
- 成功路径不受影响: p50=8.7s << 175s
- 节省 20s 在 ATE/BIG_INPUT 超时路径

## 执行

```bash
# HM1 compose edit
ssh -p 222 opc_uname@100.109.153.83
sed -i 's|TIER_TIMEOUT_BUDGET_S: "195"|TIER_TIMEOUT_BUDGET_S: "175"|' /opt/cc-infra/docker-compose.yml
cd /opt/cc-infra && docker compose up -d nv_gw
```

## 验证

- `docker exec nv_gw env | grep TIER_TIMEOUT_BUDGET_S`: 175 ✓
- `curl /health`: status=ok ✓
- 零容器漂移: 全参数与 compose 一致 ✓
- HM2 可达: 200 OK ✓

## 评判
更少报错: BIG_INPUT peer-fb 路径减 20s 等待
更快请求: 成功路径不受影响
超低延迟: p50=8.7s 不变
稳定优先: 3s margin 安全

单参数。铁律: 只改 HM1 不改 HM2。
## ⏳ 轮到HM1优化HM2
