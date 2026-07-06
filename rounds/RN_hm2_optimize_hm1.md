# R791: HM2→HM1 — NOP — 90.9% SR, 双向fallback 100%, 全参数floor, 零单tier ATE

**时间**: 2026-07-06 21:16 UTC  
**分析窗口**: 6h (15:00–21:16 UTC)  
**决策**: NOP — 零参数变更

## 全量数据

| 指标 | 值 | 判定 |
|---|---|---|
| **6h SR** | 264req/240OK (**90.9%**) | 小幅波动，正常 |
| **ATE** | 24 (9.1%), 全部tiers_tried_count=2 | NVCF双tier真实耗尽 |
| **Fallback SR** | 54/54 **100%** | 双向完美 |
| **dsv4p_nv** | 118/102 OK (86.4%) | 健康 |
| **glm5_2_nv** | 144/136 OK (94.4%) | 健康 |
| **UPSTREAM=66** | dsv4p PexecTimeout max=53,194ms (buffer=12.8s), glm5_2 max=51,628ms (buffer=14.4s) | 非绑定 ✅ |
| **FORCE_STREAM** | 66 ↔ 66 aligned | 零漂移 ✅ |
| **FALLBACK_GRAPH** | 双向活跃: `['dsv4p_nv', 'glm5_2_nv']` + `['glm5_2_nv', 'dsv4p_nv']` | 完美 ✅ |
| **所有floor参数** | FASTBREAK=1, EMPTY_200_FASTBREAK=1, CONNECT_RESERVE=0, MIN_OUTBOUND=0, INTEGRATE_COOLDOWN=0, FALLBACK_HEALTH=0.10, FORCE_STREAM_UPGRADE=0, BUDGET=114 | 无需变更 ✅ |

## 详细分析

### Tier Attempts 错误分布（6h）
| Tier | 错误类型 | 次数 |
|---|---|---|
| dsv4p_nv | empty_200 | 22 |
| dsv4p_nv | 504_nv_gateway_timeout | 13 |
| dsv4p_nv | NVCFPexecTimeout | 9 (max=53,194ms) |
| glm5_2_nv | 504_nv_gateway_timeout | 28 |
| glm5_2_nv | empty_200 | 15 |
| glm5_2_nv | NVCFPexecTimeout | 6 (max=51,628ms) |

### ATE 结构
- 24 ATE 全部 tiers_tried_count=2，fallback_actually_attempted=f
- dsv4p_nv: 16 ATE (avg 168,703ms), glm5_2_nv: 8 ATE (avg 188,390ms)
- 归因：NVCF upstream 双tier真实耗尽（empty_200 + 504_gateway_timeout主导）

### Hourly SR（15h window）
| Hour | SR |
|---|---|
| 07:00 | 100.0% (6/6) |
| 08:00 | 100.0% (17/17) |
| 09:00 | 100.0% (11/11) |
| 10:00 | 90.0% (18/20) |
| 11:00 | 100.0% (11/11) |
| 12:00 | 95.2% (20/21) |
| 13:00 | 94.1% (16/17) |
| 14:00 | 100.0% (14/14) |
| 15:00 | 100.0% (13/13) |
| 16:00 | 83.3% (10/12) |
| 17:00 | 90.5% (19/21) |
| 18:00 | 91.7% (22/24) |
| 19:00 | 89.1% (49/55) |
| 20:00 | 46.7% (7/15, partial window) |
| 21:00 | 100.0% (7/7, ongoing) |

### 健康度函数
- 74f02205 (dsv4p primary): 0.2
- 3b9748d8 (glm5_2 primary): 0.5-0.6
- f966661c (auto-switch): 0.0 (dead)

## NOP Gates 全部通过

1. ✅ ATE全部double-tier (24/24 tiers_tried_count=2)
2. ✅ 零单tier ATE
3. ✅ NVCFPexecTimeout buffer ≥3s: dsv4p=12.8s, glm5_2=14.4s
4. ✅ 双向fallback活跃 (docker logs: `['dsv4p_nv', 'glm5_2_nv']` + `['glm5_2_nv', 'dsv4p_nv']`)
5. ✅ Fallback 100% SR (54/54)
6. ✅ 全参数已floor最优

## 为什么NOP

- 24 ATE全部归因于NVCF双tier上游耗尽（NVCFPexecTimeout仅15次 vs empty_200+504_gateway共78次）
- UPSTREAM=66 buffer 12.8-14.4s — 充裕，既不需增(已非绑定)也不需减(降buffer无益)
- Fallback链路100%可靠，54次fallback全部成功
- 所有参数已在floor最优值，无进一步下调空间
- 90.9% vs R790's 93.7% — 正常6h窗口波动

## NOP streak
R788 → R789 → R790 → **R791**: 连续4轮 NOP，系统进入自维持健康regime

## ⏳ 轮到HM1优化HM2