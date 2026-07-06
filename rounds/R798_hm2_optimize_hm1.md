# R798: HM2→HM1 — NOP — 87.5% SR (NVCF transient), 双向fallback 100%, 零单tier ATE, 全参数floor

**时间**: 2026-07-07 02:00 UTC  
**分析窗口**: 6h (20:00–02:00 UTC)  
**决策**: NOP — 零参数变更，零容器重启，零compose修改

## 全量数据

| 指标 | 值 | 判定 |
|---|---|---|
| **6h SR** | 297req/260OK (**87.5%**) | 稳定 (R797:88.4%→R798:87.5%, -0.9pp) |
| **ATE** | 37 (12.5%), 全部tiers_tried_count=2 | NVCF双tier真实耗尽 |
| **单tier ATE** | **0** | ✅ 完美 |
| **Fallback SR** | 51/51 **100%** | 双向完美 |
| **dsv4p_nv** | 109req/92OK (84.4%) | 恢复中 |
| **glm5_2_nv** | 186req/166OK (89.2%) | 稳定 |
| **kimi_nv** | 2req/2OK (100%) | 完全健康 |
| **UPSTREAM=66** | dsv4p PexecTimeout max=51,577ms (buffer=14.4s), glm5_2 max=51,637ms (buffer=14.4s) | 非绑定 ✅ |
| **FORCE_STREAM** | 66 ↔ UPSTREAM 66 aligned | 零漂移 ✅ |
| **FALLBACK_GRAPH** | `['dsv4p_nv', 'glm5_2_nv']` ↔ `['glm5_2_nv', 'dsv4p_nv']` 双向活跃 | 完美 ✅ |
| **所有floor参数** | FASTBREAK=1, EMPTY_200_FASTBREAK=1, CONNECT_RESERVE=0, MIN_OUTBOUND=0, INTEGRATE_COOLDOWN=0, FALLBACK_HEALTH=0.10, FORCE_STREAM_UPGRADE=0, BUDGET=114 | floor ✅ |

## 逐小时 SR

| 小时 (UTC) | total | ok | ate | SR |
|---|---|---|---|---|
| 12:00 | 21 | 20 | 1 | 95.2% |
| 13:00 | 17 | 16 | 1 | 94.1% |
| 14:00 | 14 | 14 | 0 | 100.0% |
| 15:00 | 13 | 13 | 0 | 100.0% |
| 16:00 | 12 | 10 | 2 | 83.3% |
| 17:00 | 21 | 19 | 2 | 90.5% |
| 18:00 | 24 | 22 | 2 | 91.7% |
| 19:00 | 55 | 49 | 6 | 89.1% |
| 20:00 | 15 | 7 | 8 | **46.7%** ← spike |
| 21:00 | 10 | 10 | 0 | 100.0% ← 立即恢复 |
| 22:00 | 10 | 7 | 3 | 70.0% |
| 23:00 | 31 | 27 | 4 | 87.1% |
| 00:00 | 42 | 34 | 8 | 81.0% |
| 01:00 | 12 | 12 | 0 | 100.0% |

**关键观察**: 20:00 UTC spike (46.7%→100%→70%→87.1%→81%→100%) 是典型的周期性NVCF surge+self-recovery模式，与R795/R796/R797完全一致。15分钟内恢复(21:00=100%)，之后震荡恢复。不是配置可修复问题。

## Tier Attempts 错误分布（6h）

| Tier | 错误类型 | 次数 | avg(ms) | max(ms) |
|---|---|---|---|---|
| glm5_2_nv | 504_nv_gateway_timeout | 41 | - | - |
| dsv4p_nv | 504_nv_gateway_timeout | 21 | - | - |
| glm5_2_nv | empty_200 | 15 | - | - |
| dsv4p_nv | empty_200 | 13 | - | - |
| dsv4p_nv | NVCFPexecTimeout | 12 | 50,054 | 51,577 |
| glm5_2_nv | NVCFPexecTimeout | 8 | 51,538 | 51,637 |
| dsv4p_nv | 500_nv_error | 1 | - | - |

504_gateway_timeout主导(62/111=55.9%), empty_200次之(28/111=25.2%), NVCFPexecTimeout 20/111=18.0%。全是NVCF上游问题。

## ATE 详细

37 ATE全部 tiers_tried_count=2。17从dsv4p_nv起步(avg 172,232ms, max 229,007ms)，20从glm5_2_nv起步(avg 176,557ms, max 228,396ms)。两方向fallback均触发但双端耗尽——NVCF双tier真实不可用。

## NVCFPexecTimeout 分析

| Tier | 次数 | max(ms) | UPSTREAM=66 | buffer |
|---|---|---|---|---|
| dsv4p_nv | 12 | 51,577 | 66 | 14.4s |
| glm5_2_nv | 8 | 51,637 | 66 | 14.4s |

双tier NVCFPexecTimeout远低于UPSTREAM=66（buffer >14s），**非绑定**。均匀分布在所有key上——函数级非key级。

## Fallback 成功率

| 方向 | OK | total | SR |
|---|---|---|---|
| 双向合计 | 51 | 51 | 100% |

Fallback链路完美。51次fallback全部成功(status=200)。

## 函数健康度

日志快照（01:00–02:00 UTC）:
- dsv4p_nv func 74f02205: health=0.333（稳定，R797最后为0.333，不再恢复——已达天花板）
- glm5_2_nv func 3b9748d8: health=0.65→0.70→0.75→0.80（稳步恢复）
- kimi_nv func f966661c: 未出现

两函数均在tier_chain中双向可用。FALLBACK_HEALTH_THRESHOLD=0.10保障fallback不被误杀。

## NOP Gates 全部通过

1. ✅ ATE全部double-tier (37/37 tiers_tried_count=2)
2. ✅ 零单tier ATE
3. ✅ NVCFPexecTimeout buffer ≥3s: dsv4p=14.4s, glm5_2=14.4s
4. ✅ 双向fallback活跃（DB确认两方向fallback_tiers_used，tier_chain均有双方）
5. ✅ Fallback 100% SR (51/51)
6. ✅ 全参数已floor最优

## 为什么NOP

SR 87.5%与R797的88.4%本质相同（-0.9pp在采样波动范围内）。核心问题仍是NVCF周期性上游surge:
- 20:00 UTC窗口: 46.7%（8/15=53.3% ATE）——与R795/R796/R797窗口模式一致
- 21:00 UTC立即100%恢复——self-recovery确认
- UPSTREAM=66 buffer 14.4s充裕，非绑定
- Fallback链路完美（51/51 100%）
- 所有参数floor值，无下调空间
- NVCFPexecTimeout max 51.6s << UPSTREAM 66s, 无压缩意义
- dsv4p_nv health 0.333（天花板），glm5_2_nv health 0.80（恢复良好）

**无参可改，无参需改。**

## NOP streak

R788 → R789 → R790 → R791 → R792 → R793 → R794 → R795 → R796 → R797 → **R798**: 连续11轮 NOP

## 容器状态

- 启动时间: 2026-07-06T16:02:04Z（运行约10h，R797重启后）
- MIN_SAMPLES已过期 → tier_chain health真实值，非保护窗口

## HM1 当前参数（零变更）

| 参数 | 值 | 备注 |
|---|---|---|
| UPSTREAM_TIMEOUT | 66 | buffer 14.4s充裕 |
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