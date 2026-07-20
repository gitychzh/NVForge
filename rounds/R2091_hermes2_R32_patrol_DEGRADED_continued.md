# R2091: hermes2 R32 巡检 — NVCF dsv4p function 持续 DEGRADED, SR=0%, 连续第 2 轮

## 本轮类型: 巡检轮 (不改代码)

## 数据依据 (30min 窗口, 2026-07-20 23:00~23:30 UTC+8)

### dsv4p_nv 核心指标

| 指标 | R32 | R31 | 变化 |
|------|-----|-----|------|
| 总请求 | 162 | 148 | +9.5% |
| 成功 | **0** | **0** | — |
| 502 (hm4104层面) | 161 | 143 | +12.6% |
| all_tiers_exhausted | 161 | 148 | +8.8% |
| **SR** | **0%** | **0%** | — |
| 30min fallback | 197 | 209 | -5.7% |

### nv_gw 日志确认

```
[NV-NONCYCLE-ERR] tier=dsv4p_nv k1/k2 resp.status=400
  body={"detail": "Function id '74f02205-c7ba-438f-b81a-2537955bd7ec': DEGRADED function cannot be invoked"}
[NV-TIER-DEGRADED] tier=dsv4p_nv marked DEGRADED cooldown 60s
[NV-TIER-DEGRADED-SKIP] tier=dsv4p_nv in DEGRADED cooldown, short-circuit → tier fail
```

**仍为 400 DEGRADED**, 和 R31 完全一致。R814 DEGRADED short-circuit 正确工作。

### 健康检查

- `curl /health`: OK, proxy_role=passthrough, 5 keys, dsv4p_nv/kimi_nv/glm5_2_nv
- `docker ps`: nv_gw Up 4h, hm4104 Up 7h, ms_gw Up 2h, logs_db Up 3d — 全部正常

## 本轮决策

**不改代码。** 决策矩阵: 400 DEGRADED 持续, SR=0% < 20% → 巡检轮, 标注"NVCF function DEGRADED, 需人为联系 NVCF"。

## 七轮恶化趋势 (R26-R32)

| 轮次 | 502 | SR | Tier 429 | 判断 |
|------|-----|-----|----------|------|
| R26 | 6 | 73.1% | 57 | 持续恢复 |
| R27 | 9 | 55.0% | 28 | 恶化 |
| R28 | 10 | 50.0% | 22 | 恶化 |
| R29 | 11 | 35.3% | 13 | 触发阈值 |
| R30 | 112 | 9.0% | 6 | 误判为"502灾难" |
| R31 | 143 | 0% | 5 | 确诊: 400 DEGRADED |
| **R32** | **161** | **0%** | **0** | **持续 DEGRADED** |

502 持续上升 (6→9→10→11→112→143→161), SR 归零持续 2 轮。

## 下一步 (R33)

继续巡检。NVCF dsv4p function DEGRADED 已持续 2 轮。若 R33 仍 DEGRADED, 强烈建议人为介入联系 NVCF 支持。

## 验证

- 未改代码, 无需验证
- 容器健康: nv_gw/hm4104/ms_gw/logs_db 全部 Up
- dsv4p_nv 参数: 无变化 (R31 快照为准)