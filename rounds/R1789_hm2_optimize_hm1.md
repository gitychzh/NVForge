# R1789 (HM2→HM1) — NOP (dsv4p_nv zero post-deploy traffic)

## 数据采集 (2026-07-18 11:20 UTC, HM1)

### 容器状态
- **nv_gw 重启时间**: 2026-07-18 10:50:27 UTC (R1787 deploy, 约30min ago)
- **零容器漂移**: 全参数与 compose 一致 ✓
- **TIER_TIMEOUT_BUDGET_S=175** (R1787), **NVU_TIER_BUDGET_DSV4P_NV=50** (R1786)
- **NVU_PEER_FALLBACK_TIMEOUT=122** (R1744)

### DB 6h 窗口
```
total | ok | fail502 | avg_ok_ms | ate(total) | ate_phantom | ate_real
  32  | 31 |    1    |   16741   |     8      |      7      |    1
```

### 按模型 (6h)
| model | total | ok | fail | avg_ok_ms | ATE |
|---|---|---|---|---|---|
| glm5_2_nv | 24 | 24 | 0 | 8806 | 0 |
| dsv4p_nv | 8 | 7 | 1 | 44412 | 8 |

### Post-Restart (10:50 UTC 后)
```
total | ok | fail | avg_ok_ms
  2   |  2 |   0  |    6764
```
- 仅 glm5_2_nv × 2，零 dsv4p_nv 流量
- 零 peer-fallback 触发 (`docker logs` 零 NV-PEER-FB)
- 零 ERROR/WARN (仅 1× SSLEOFError on glm5_2_nv k3, mode→advance 正常处理)

### Tier Attempts (6h)
| tier | error_type | cnt |
|---|---|---|
| glm5_2_nv | pexec_success | 24 |
| glm5_2_nv | pexec_SSLEOFError | 1 |

### dsv4p_nv ATE 明细 (全部 R1786 部署前)
| ts | status | duration_ms | fallback_occurred |
|---|---|---|---|
| 09:31 | 200 | 29732 | f |
| 09:30 | 200 | 15328 | f |
| 09:30 | 200 | 14897 | f |
| 09:27 | 200 | 95148 | f |
| 09:26 | 200 | 23118 | f |
| 09:24 | 200 | 32244 | f |
| 09:22 | 200 | 100418 | f |
| 09:19 | 502 | 56782 | f |

全部 pre-restart, fallback_occurred=false, tiers_tried_count=1 (单 tier 无 peer-fb)。

## 分析

R1786 (TIER_DSV4P 60→50) + R1787 (BUDGET 195→175) 预期效果：
- 旧配置: 70+125=195≥195 → peer-fb skipped (R1739 boundary equality)
- 新配置: 50+122=172<175 → peer-fb 应可触发 (3s margin)

**但 dsv4p_nv 零 post-deploy 流量**，无法验证 peer-fb 是否实际生效。R1788 的 NOP 原因仍然成立：无 post-deploy 数据 = 无法决策。

## 决策

| 参数 | 候选 | 理由 |
|---|---|---|
| 全部 | NOP | dsv4p_nv 零 post-deploy 流量，无数据支撑任何改动 |

**最终决策：NOP。** 等待 dsv4p_nv 流量积累，验证：(1) peer-fb 是否从 skipped→enabled，(2) 50s tier budget 是否过短导致过早判定 key 失败，(3) BUDGET=175 是否足够容纳 50+122=172s。

## 执行

无执行。NOP 轮。

## 验证

| 指标 | 数值 | 状态 |
|---|---|---|
| 首试成功率 | 100% (2/2) | ⏳ 数据太少 |
| Post-restart dsv4p_nv | 0 | ⏳ 待流量 |
| Peer-fallback | 0 | ⏳ 待验证 |
| 容器漂移 | 零 | ✅ |
| ERROR/WARN | 0 | ✅ |

## 评判
更少报错: 100% SR (2/2, 但无 dsv4p_nv)
更快请求: glm5_2_nv avg=6764ms
超低延迟: 正常
稳定优先: 零漂移，零ERROR

单参数少改多轮。铁律: 只改 HM1 不改 HM2。
## ⏳ 轮到HM1优化HM2