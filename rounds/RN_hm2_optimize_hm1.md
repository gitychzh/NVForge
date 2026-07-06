# R790: HM2→HM1 — NOP — 93.7% SR, 双向fallback 100%, 全参数floor, 零单tier ATE

**时间**: 2026-07-06 19:50 UTC  
**分析窗口**: 6h (13:50–19:50 UTC)  
**决策**: NOP — 零参数变更

## 全量数据

| 指标 | 值 | 判定 |
|---|---|---|
| **6h SR** | 252req/236OK (**93.7%**) | 优秀 |
| **ATE** | 16 (6.3%), 全部tiers_tried_count=2 | NVCF双tier真实耗尽 |
| **Fallback SR** | 49/49 **100%** | 双向完美 |
| **dsv4p_nv** | 113/102 OK (90.3%) | 健康 |
| **glm5_2_nv** | 136/131 OK (96.3%) | 健康 |
| **UPSTREAM=66** | dsv4p PexecTimeout max=53,194ms (buffer=12.8s), glm5_2 max=51,628ms (buffer=14.4s) | 非绑定 ✅ |
| **FORCE_STREAM** | 66 ↔ 66 aligned | 零漂移 ✅ |
| **FALLBACK_GRAPH** | 双向活跃: `['glm5_2_nv', 'dsv4p_nv']` + `['dsv4p_nv', 'glm5_2_nv']` | 完美 ✅ |
| **所有floor参数** | FASTBREAK=1, EMPTY_200_FASTBREAK=1, CONNECT_RESERVE=0, MIN_OUTBOUND=0, INTEGRATE_COOLDOWN=0, FALLBACK_HEALTH=0.10, FORCE_STREAM_UPGRADE=0, BUDGET=114 | 无需变更 ✅ |

## NOP Gates 全部通过

1. ✅ ATE全部double-tier (16/16 tiers_tried_count=2)
2. ✅ 零单tier ATE
3. ✅ NVCFPexecTimeout buffer ≥3s: dsv4p=12.8s, glm5_2=14.4s
4. ✅ 双向fallback活跃 (docker logs确认)
5. ✅ Fallback 100% SR (49/49)
6. ✅ 全参数已floor最优

## 为什么NOP

- 16 ATE全部归因于NVCF双tier上游耗尽（empty_200: 38次, 504_nv_gateway_timeout: 37次, NVCFPexecTimeout: 13次）
- UPSTREAM=66 buffer 12.8-14.4s — 充裕，既不需增(已非绑定)也不需减(降buffer无益)
- Fallback链路100%可靠，49次fallback全部成功
- 所有参数已在floor最优值，无进一步下调空间

## NOP streak
R788 → R789 → **R790**: 连续3轮 NOP，系统进入自维持健康regime

## 健康度
dsv4p_nv: 0.45 (日志最近), glm5_2_nv: 0.80-0.90 — 双tier健康稳定

## ⏳ 轮到HM1优化HM2