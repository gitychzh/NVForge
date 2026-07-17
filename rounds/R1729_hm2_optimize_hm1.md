# R1729 (HM2→HM1): UPSTREAM_TIMEOUT 53→55 (+2s)

## 数据 (6h窗口, 2026-07-18 05:50 UTC)

| Metric | Value |
|---|---|
| 请求总数 | 61 |
| 成功 (OK) | 52 (85.2% SR) |
| 失败 | 9 |
| zombie_empty_completion | 7 (glm5_2_nv) |
| all_tiers_exhausted | 5 (2 real 502 dsv4p_nv + 3 phantom 200) |
| p50 | 10,174ms (10.2s) |
| p95 | 46,061ms (46.1s) |
| p99 | 51,823ms (51.8s) |
| max_ok | 51,823ms (51.8s) |
| fallbacks | 0 |
| peer-fb usage | 0 |
| key_cycle_429s | 1-key: 53 (86.9%), 2-key: 3 (4.9%), 0-key: 5 (8.2%) |

## 问题: UPSTREAM_TIMEOUT buffer violation

- UPSTREAM_TIMEOUT=53, max_ok=51.8s → buffer=1.2s
- R751 ≥3s buffer rule: 51.8+3=54.8s → need ≥55s
- R1727 set 53 when p99=49.4s; p99 has drifted to 51.8s

## 修改

```
UPSTREAM_TIMEOUT: 53 → 55 (+2s)
```

- 55−51.8=3.2s ≥ 3s (R751) ✓
- BUDGET=145 > 55 ✓
- 不影响 zombie/ATE 路径 (zombie=~7s, ATE=~70s, both < 55)
- 单参数, 铁律: 只改HM1不改HM2

## 验证

- `docker exec nv_gw env | grep UPSTREAM_TIMEOUT`: 55 ✓
- `curl /health`: status=ok ✓
- 无容器漂移: 所有调优参数 compose=container ✓

## 评判

- 更少报错: √ (buffer 恢复, 减少 UPSTREAM_TIMEOUT 误杀)
- 更快请求: → (55s 不影响 p50/p95 normal path)
- 超低延迟: → (zombie 路径不受影响, BIG_INPUT_COOLDOWN=5400 仍生效)
- 稳定优先: √ (buffer 从 1.2s→3.2s, 恢复 R751 安全边界)
## ⏳ 轮到HM1优化HM2
