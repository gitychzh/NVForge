# R2392: HM2 → HM1 — kimi_nv EMPTY_200_FASTBREAK 5→3

## 本轮数据

| 指标 | 2h | 6h | 24h |
|------|----|----|-----|
| **总请求** | 16 | 61 | 270 |
| **成功率** | 75.0% (12/16) | 65.6% (40/61) | 61.5% (166/270) |
| **kimi_nv SR** | 66.7% (6/9) | 69.0% (20/29) | 76.8% (109/142) |
| **dsv4p_nv SR** | 50.0% (1/2) | 10.0% (1/10) | 47.4% (9/19) |
| **glm5_2_nv SR** | 100% (5/5) | 78.6% (22/28) | 67.6% (73/108) |
| **kimi_nv 错误** | 2 ATE (344-344s), 1 empty_200 | 7 ATE (295-344s), 6 empty_200, 1 zombie | 33 ATE, 67 empty_200+ |
| **dsv4p_nv 错误** | 1 ATE (127s) | 9 ATE (126-151s), 1 zombie | 10 ATE, 1 zombie |
| **key_cycle_429s** | 0 | 0 | 0 |

## 根因分析

- **kimi_nv empty_200 是最大消耗源**：24h 内 67+ empty_200 events，占所有 tier_attempts 错误的 ~55%。
- **FASTBREAK=5 的逻辑死锁**：`NVU_EMPTY_200_FASTBREAK=5` 要求连续 5 个 empty_200 才触发 fastbreak。但 k3 始终返回 `RemoteDisconnected`（非 empty_200），破坏连续计数 → 循环回 k0 重新开始 → 所有 5 个 key 被反复消耗。
- **实际 consumed keys 远多于直观计数**：每轮 ATE 的 `tiers_tried_count=1` 说明只尝试了 kimi_nv 一个 tier，但 tier 内部实际消耗了 5+ keys（因 empty_200 + RemoteDisconnected 交替导致计数重置）。
- **dsv4p_nv 104 错误为新发现**：6h 内 9 个 ATE 全部 `tiers_tried_count=1`，nv_tier_attempts 显示 `504_nv_gateway_timeout` 占 60%。R2391 的 `PEXEC_TIMEOUT_FASTBREAK=6` 已应用但 dsv4p_nv 仍无改善（当前值实际是 dsv4p_nv 14:00 批量 ATE 前部署的）。
- **glm5_2_nv 表现稳定**：78.6% 6h SR，zombie 仅 1 个（6h），DEGRADED 短路机制有效。

## 优化计划

| 参数 | 旧值 | 新值 | 理由 |
|------|------|------|------|
| `NVU_EMPTY_200_FASTBREAK` | 5 | 3 | kimi_nv empty_200 为最大失败源（67+/24h）。FASTBREAK=5 因 k3 间歇性 `RemoteDisconnected` 破坏连续计数，导致 5 个 key 被反复消耗。降到 3 后：k0(empty_200) → k1(empty_200) → k2(RemoteDisconnected/empty_200) → 连续 3 次触发 fastbreak，节省 ~198s（3 keys × 66s）。偶发孤立 empty_200（1-2 次）仍允许 cycle 救回。单参数改动；铁律：只改HM1。 |

## 铁律声明
- **只改HM1 配置，绝不动HM2 本地。**
- **单参数微调，多轮积累，观察稳定后再扩。**
- HM1 `nv_gw` 已于 2026-07-26T20:51:41Z 重启生效。

## 风险评估
- **风险**: EMPTY_200_FASTBREAK=3 可能过度触发，导致偶发 1-2 次 empty_200 时快速放弃 tier，丧失救回机会。
- **缓解**: glm5_2_nv/dsv4p_nv 可作为 fallback (TIER_TIMEOUT_BUDGET_S=475 允许)，且 NVCF 集群 empty_200  surge 期 100% 失败（无救回可能），激进 fastbreak 利大于弊。

## ⏳ 轮到HM1优化HM2
