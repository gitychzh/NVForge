# R799: HM2→HM1 — NOP (false trigger) — 87.1% SR, 零新提交, 全参数floor, 系统稳定

**时间**: 2026-07-07 02:51 UTC  
**分析窗口**: 6h (12:00–02:00+ UTC)  
**决策**: NOP — HM1未提交新commit，cron误触发。系统状态与R798一致，无参需改。

## 触发原因

检测脚本判定"HM1提交了新commit"触发cron，但实际git HEAD仍是R798（HM2自己的NOP round）。脚本fetch后确认`8f3759e`已处理，输出"等待新提交"。无HM1→HM2新round，RN_hm2_optimize_hm1.md末尾标记"⏳ 轮到HM1优化HM2"——当前是HM1的回合，非HM2。

## 逐小时 SR

| 小时 (UTC) | total | ok | ate | SR |
|---|---|---|---|---|
| 12:00 | 2 | 1 | 1 | 50.0% |
| 13:00 | 17 | 16 | 1 | 94.1% |
| 14:00 | 14 | 14 | 0 | 100.0% |
| 15:00 | 13 | 13 | 0 | 100.0% |
| 16:00 | 12 | 10 | 2 | 83.3% |
| 17:00 | 21 | 19 | 2 | 90.5% |
| 18:00 | 24 | 22 | 2 | 91.7% |
| 19:00 | 55 | 49 | 6 | 89.1% |
| 20:00 | 15 | 7 | 8 | **46.7%** ← spike |
| 21:00 | 10 | 10 | 0 | 100.0% ← 恢复 |
| 22:00 | 10 | 7 | 3 | 70.0% |
| 23:00 | 31 | 27 | 4 | 87.1% |
| 00:00 | 42 | 34 | 8 | 81.0% |
| 01:00 | 12 | 12 | 0 | 100.0% |
| 02:00 | 8 | 8 | 0 | 100.0% |

**关键观察**: 20:00 UTC spike (46.7%~53.3% ATE) — 与R795/R796/R797/R798周期一致。21:00立即恢复(100%)。不是配置可修复问题。

## 全量数据（6h, 12:00–02:00+ UTC）

| 指标 | 值 | 判定 |
|---|---|---|
| **6h SR** | 286req/249OK (**87.1%**) | 与R798(87.5%)一致(-0.4pp, 采样波动) |
| **ATE** | 37 (12.9%), 全部tiers_tried_count=2 | NVCF双tier耗尽 |
| **单tier ATE** | **0** | ✅ 完美 |
| **Fallback SR** | 50/50 **100%** | 双向完美 |
| **dsv4p_nv** | health 0.333→0.368 | 稳定 |
| **glm5_2_nv** | health 0.8→1.0 | 完全恢复 |
| **NVCFPexecTimeout max** | dsv4p=51,577ms, glm5_2=51,637ms | buffer 14.4s vs UPSTREAM=66 ✅ |

## Tier Attempts 错误分布（6h）

| Tier | 错误类型 | 次数 | avg(ms) | max(ms) |
|---|---|---|---|---|
| glm5_2_nv | 504_nv_gateway_timeout | 40 | - | - |
| dsv4p_nv | 504_nv_gateway_timeout | 23 | - | - |
| glm5_2_nv | empty_200 | 15 | - | - |
| dsv4p_nv | NVCFPexecTimeout | 13 | 50,123 | 51,577 |
| dsv4p_nv | empty_200 | 11 | - | - |
| glm5_2_nv | NVCFPexecTimeout | 8 | 51,538 | 51,637 |
| dsv4p_nv | 500_nv_error | 1 | - | - |

504_gateway_timeout主导(63/111=56.8%), empty_200次之(26/111=23.4%), NVCFPexecTimeout 21/111=18.9%。全是NVCF上游问题。

## NVCFPexecTimeout 分析

| Tier | 次数 | max(ms) | UPSTREAM=66 | buffer |
|---|---|---|---|---|
| dsv4p_nv | 13 | 51,577 | 66 | 14.4s |
| glm5_2_nv | 8 | 51,637 | 66 | 14.4s |

双tier NVCFPexecTimeout远低于UPSTREAM=66（buffer >14s），**非绑定**。均匀分布在所有key上——函数级非key级。

## Fallback 成功率

| 方向 | OK | total | SR |
|---|---|---|---|
| 双向合计 | 50 | 50 | 100% |

Fallback链路完美。50次fallback全部成功。

## 函数健康度

日志快照（01:00–02:33 UTC）:
- dsv4p_nv func 74f02205: health 0.333→0.368→0.353（微小波动，R798天花板0.333）
- glm5_2_nv func 3b9748d8: health 0.8→0.9→0.95→1.0（完全恢复！）

两函数均在tier_chain中双向可用。FALLBACK_HEALTH_THRESHOLD=0.10保障fallback不被误杀。

## 日志确认

```
[NV-REQ] tier_chain=['dsv4p_nv', 'glm5_2_nv'] (dynamic fallback, health={74f02205: 0.333-0.375, 3b9748d8: 0.8-1.0})
[NV-REQ] tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={...})
[NV-FALLBACK-SUCCESS] Success on fallback tier glm5_2_nv after primary dsv4p_nv failed
```

双向fallback活跃，零单tier现象，零HEALTH_THRESHOLD误杀。

## NOP Gates 全部通过

1. ✅ ATE全部double-tier (37/37 tiers_tried_count=2)
2. ✅ 零单tier ATE
3. ✅ NVCFPexecTimeout buffer ≥3s: dsv4p=14.4s, glm5_2=14.4s
4. ✅ 双向fallback活跃（tier_chain双方均含fallback目标）
5. ✅ Fallback 100% SR (50/50)
6. ✅ 全参数已floor最优: FASTBREAK=1, EMPTY_200_FASTBREAK=1, CONNECT_RESERVE=0, MIN_OUTBOUND=0, INTEGRATE_COOLDOWN=0, FALLBACK_HEALTH=0.10, FORCE_STREAM_UPGRADE=0, BUDGET=114, UPSTREAM=66

## 为什么NOP

1. **False trigger**: HM1未提交新commit——cron误触发。脚本输出明确"等待新提交"。
2. **SR不变**: 87.1% vs R798 87.5%（-0.4pp，采样波动内）
3. **20:00 UTC spike不变**: 周期性NVCF surge+self-recovery模式延续
4. **UPSTREAM=66 buffer 14.4s充裕**，非绑定
5. **所有参数floor值**，无下调/上调空间
6. **glm5_2_nv health→1.0**（完全恢复），dsv4p_nv health 0.333稳定
7. **HF1回合**: RN_hm2_optimize_hm1.md末尾标记"轮到HM1优化HM2"——当前是HM1回合

**无参可改，无参需改，无回合需执行。**

## NOP streak

R788 → R789 → R790 → R791 → R792 → R793 → R794 → R795 → R796 → R797 → R798 → **R799**: 连续12轮 NOP

## 容器状态

- HM1启动时间: 2026-07-06T16:02:04Z（运行约10.8h）
- MIN_SAMPLES已过期 → tier_chain health真实值

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