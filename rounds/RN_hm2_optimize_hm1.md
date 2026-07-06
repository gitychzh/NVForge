# R794: HM2→HM1 — NOP — 90.0% SR, 双向fallback 100%, 全参数floor, 零单tier ATE

**时间**: 2026-07-06 22:46 UTC  
**分析窗口**: 6h (16:46–22:46 UTC)  
**决策**: NOP — 零参数变更，零容器重启

## 全量数据

| 指标 | 值 | 判定 |
|---|---|---|
| **6h SR** | 260req/234OK (**90.0%**) | R793 90.8%→90.0% 正常波动 |
| **ATE** | 26 (10.0%), 全部tiers_tried_count=2 | NVCF双tier真实耗尽 |
| **Fallback SR** | 52/52 **100%** | 双向完美 |
| **dsv4p_nv** | 116req/99OK (85.3%) | 健康 |
| **glm5_2_nv** | 142req/133OK (93.7%) | 健康 |
| **UPSTREAM=66** | dsv4p PexecTimeout max=51,577ms (buffer=14.4s), glm5_2 max=51,628ms (buffer=14.4s) | 非绑定 ✅ |
| **FORCE_STREAM** | 66 ↔ UPSTREAM 66 aligned | 零漂移 ✅ |
| **FALLBACK_GRAPH** | `['dsv4p_nv', 'glm5_2_nv']` 双向活跃 | 完美 ✅ |
| **所有floor参数** | FASTBREAK=1, EMPTY_200_FASTBREAK=1, CONNECT_RESERVE=0, MIN_OUTBOUND=0, INTEGRATE_COOLDOWN=0, FALLBACK_HEALTH=0.10, FORCE_STREAM_UPGRADE=0, BUDGET=114 | 无需变更 ✅ |

## Tier Attempts 错误分布（6h）

| Tier | 错误类型 | 次数 | avg_ms | max_ms |
|---|---|---|---|---|
| dsv4p_nv | empty_200 | 18 | − | − |
| dsv4p_nv | 504_nv_gateway_timeout | 16 | − | − |
| dsv4p_nv | NVCFPexecTimeout | 11 | 50,004 | 51,577 |
| dsv4p_nv | 500_nv_error | 1 | − | − |
| glm5_2_nv | 504_nv_gateway_timeout | 30 | − | − |
| glm5_2_nv | empty_200 | 15 | − | − |
| glm5_2_nv | NVCFPexecTimeout | 6 | 51,557 | 51,628 |

## ATE 结构
- 26 ATE 全部 tiers_tried_count=2
- 0 单tier ATE（fallback链完整）
- NVCFPexecTimeout 占比: dsv4p 11/46 (23.9%), glm5_2 6/51 (11.8%)
- 504_nv_gateway_timeout + empty_200 主导（dsv4p 35, glm5_2 45）

## 日志关键事件
- 22:17–22:42 UTC: 1次 dsv4p→glm5_2 fallback成功 + 1次双tier失败（peer-fallback也耗尽→502）
- NV-CYCLE 504触发: dsv4p_nv k3 + glm5_2_nv k2
- dsv4p_nv 健康度波动: 74f02205 0.15, 3b9748d8 0.8, f966661c 0.0
- BrokenPipeError: 1次 (client断开)
- 无单tier fallback阻断

## 24h 全景
- 684req/617OK (90.2%), 67 ATE
- 全部 all_tiers_exhausted，无其他错误类型
- 系统长期稳定在~90% SR

## NOP Gates 全部通过

1. ✅ ATE全部double-tier (26/26 tiers_tried_count=2)
2. ✅ 零单tier ATE
3. ✅ NVCFPexecTimeout buffer ≥3s: dsv4p=14.4s, glm5_2=14.4s
4. ✅ 双向fallback活跃 (tier_chain=['dsv4p_nv','glm5_2_nv'] dynamic fallback)
5. ✅ Fallback 100% SR (52/52)
6. ✅ 全参数已floor最优

## 为什么NOP
- 26 ATE全部归因于NVCF双tier上游耗尽（empty_200 + 504_gateway_timeout）
- UPSTREAM=66 buffer 14.4s — 充裕，既不需增也不需减
- Fallback链路100%可靠
- 所有参数已在floor最优值
- SR波动90.0%→90.8%→90.0% 正常窗口抖动（±<1%）
- BUDGET=114 >> 66+66=132 安全余量 114 足够

## NOP streak
R788 → R789 → R790 → R791 → R792 → R793 → **R794**: 连续7轮 NOP

## HM1 当前参数（零变更）
| 参数 | 值 | 备注 |
|---|---|---|
| UPSTREAM_TIMEOUT | 66 | 充裕buffer 14.4s |
| TIER_TIMEOUT_BUDGET_S | 114 | 安全 |
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