# R792: HM2→HM1 — NOP — 90.7% SR, 双向fallback 100%, 全参数floor, 零单tier ATE

**时间**: 2026-07-06 21:31 UTC  
**分析窗口**: 6h (15:31–21:31 UTC)  
**决策**: NOP — 零参数变更，零容器重启

## 全量数据

| 指标 | 值 | 判定 |
|---|---|---|
| **6h SR** | 259req/235OK (**90.7%**) | 小幅波动，正常 |
| **ATE** | 24 (9.3%), 全部tiers_tried_count=2 | NVCF双tier真实耗尽 |
| **Fallback SR** | 53/53 **100%** | 双向完美 |
| **dsv4p_nv** | 116req/100OK (86.2%) | 健康 |
| **glm5_2_nv** | 141req/133OK (94.3%) | 健康 |
| **kimi_nv** | 2req/2OK (100%) | 健康 |
| **UPSTREAM=66** | dsv4p PexecTimeout max=51,577ms (buffer=14.4s), glm5_2 max=51,628ms (buffer=14.4s) | 非绑定 ✅ |
| **FORCE_STREAM** | 66 ↔ UPSTREAM 66 aligned | 零漂移 ✅ |
| **FALLBACK_GRAPH** | 双向活跃: `['dsv4p_nv', 'glm5_2_nv']` + `['glm5_2_nv', 'dsv4p_nv']` | 完美 ✅ |
| **所有floor参数** | FASTBREAK=1, EMPTY_200_FASTBREAK=1, CONNECT_RESERVE=0, MIN_OUTBOUND=0, INTEGRATE_COOLDOWN=0, FALLBACK_HEALTH=0.10, FORCE_STREAM_UPGRADE=0, BUDGET=114 | 无需变更 ✅ |

## 详细分析

### Tier Attempts 错误分布（6h）
| Tier | 错误类型 | 次数 | avg_ms | max_ms |
|---|---|---|---|---|
| dsv4p_nv | empty_200 | 21 | − | − |
| dsv4p_nv | 504_nv_gateway_timeout | 13 | − | − |
| dsv4p_nv | NVCFPexecTimeout | 8 | 51,113 | 51,577 |
| dsv4p_nv | 500_nv_error | 1 | − | − |
| glm5_2_nv | 504_nv_gateway_timeout | 28 | − | − |
| glm5_2_nv | empty_200 | 15 | − | − |
| glm5_2_nv | NVCFPexecTimeout | 6 | 51,557 | 51,628 |

### ATE 结构
- 24 ATE 全部 tiers_tried_count=2
- 0 单tier ATE（fallback链完整）
- 归因：NVCF upstream 双tier真实耗尽（empty_200 + 504_gateway_timeout主导）

### 健康度函数
- 74f02205 (dsv4p primary): 0.2 (稳定)
- 3b9748d8 (glm5_2 primary): 0.5–0.65 (稳健)
- f966661c (kimi auto-switch): 0.0 (dead，不影响主链路)

### 日志关键事件（最后50行）
- 1次 双tier ATE (20:55 UTC): glm5_2 → k1 504 gateway timeout, NVCFPexecTimeout, 双tier全耗尽
- 3次 dsv4p→glm5_2 fallback全部成功 (21:01, 21:03, 21:04 UTC)
- 多个 thinking 请求自动扩展 timeout 到 66s（系统正常行为）
- BrokenPipeError: 1次 (client断开，非gateway故障)

## NOP Gates 全部通过

1. ✅ ATE全部double-tier (24/24 tiers_tried_count=2)
2. ✅ 零单tier ATE
3. ✅ NVCFPexecTimeout buffer ≥3s: dsv4p=14.4s, glm5_2=14.4s
4. ✅ 双向fallback活跃 (docker logs确认链完整)
5. ✅ Fallback 100% SR (53/53)
6. ✅ 全参数已floor最优

## 为什么NOP

- 24 ATE全部归因于NVCF双tier上游耗尽（NVCFPexecTimeout仅14次 vs empty_200+504_gateway共77次）
- UPSTREAM=66 buffer 14.4s — 充裕，既不需增(已非绑定)也不需减(降buffer无益)
- Fallback链路100%可靠，53次fallback全部成功
- 所有参数已在floor最优值，无进一步下调空间
- 90.7% vs R791's 90.9% — 正常6h窗口波动（1-2条请求差异）

## NOP streak
R788 → R789 → R790 → R791 → **R792**: 连续5轮 NOP，系统进入自维持健康regime

## HM1 当前参数（零变更）
| 参数 | 值 | 备注 |
|---|---|---|
| UPSTREAM_TIMEOUT | 66 | 充裕buffer |
| TIER_TIMEOUT_BUDGET_S | 114 | 覆盖PexecTimeout+headroom |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 1 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | floor |
| NVU_FORCE_STREAM_UPGRADE | 0 | floor |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | aligned |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| KEY_COOLDOWN_S | 25 | standard |
| TIER_COOLDOWN_S | 25 | standard |

## ⏳ 轮到HM1优化HM2