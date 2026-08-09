# R1230: dsv4f0731_nv40666 self-opt NOP — 30min SR=91.2%(52/57), 错为NVCF瞬态(2×IncompleteRead+1×ATE+1×buffer_exhausted+1×zombie), hm4104 2次fallback因NVCF过载烧满180s, 24h ATE=117稳定

## 结论: NOP (不改任何参数)

## 依据 (30min 窗口, 2026-08-09 ~14:40)

| 指标 | 值 |
|---|---|
| 总量/成功/失败 | 57 / 52 / 5 (SR=91.2%) |
| Avg/P50/P95 | 48413 / 31105 / 184886 ms |
| 净429 | 0 |
| upstream_type | nvcf_pexec 57 req, 52 SR=91.2% (100% pexec, 无integrate) |
| finish_reason | tool_calls 42, stop 10 |

### 错误分类 (5错, 分散于 k0/k2/k3)
| error_type | n | avg_ms |
|---|---|---|
| NVStream_IncompleteRead | 2 | 35386/36380 |
| all_tiers_exhausted | 1 | 180059 |
| buffer_exhausted | 1 | 191030 |
| zombie_empty_completion | 1 | 13059 |

### per-key 200 延迟
- k0: 9req/40794 | k1: 12req/46086 | k2: 12req/55611 | k3: 6req/14450 | k4: 13req/48419
- 各区均衡(14-55s), k3 延迟低但样本少, 无 key 持续劣化。错误分散 k0/k2/k3 各1-2次, 不集中。

### key_cycle_429s (内部循环计数, 非净错误)
- k0=15, k1=39, k2=2, k3=1 (k4=0)
- k1 持续偏高(39)但 key manager 已吸收(净429=0), 与 R1224-R1229 模式一致 → key cooldown 工作正常。

### hm4104 fallback (最近30min, 10条日志)
- 2× PRIMARY-FAIL-STREAM: `nv_gw 流式 502 after 180067ms / 180040ms` → **all_tiers_exhausted 烧满整段180s budget** → 切 ms_gw fallback + circuit OPEN
- 后续 BREAKER-SKIP 直走 fallback(~5min 冷却期)
- 根因: NVCF 共享过载时 5 key 全失败、tier 级 ATE 烧满 180s, 非本容器超时/冷却/路由可控。

### 趋势
- 6h: 622/586 = 94.2% SR, 36错, 0 ATE
- 3h逐小时: 06h=79/74(93.7%) / 05h=92/85(92.4%) / 04h=115/110(95.7%) / 03h=16/21(低样本峰值, 已恢复)
- 24h all_tiers_exhausted=117 (与 R1224-R1229 的 116-118 持平, 稳定无上升)

## 为何不改
1. SR=91.2% 略低于上轮(94.5%)但仍处历史噪声带(91-95%)。5 个错误全部为 **NVCF 侧瞬态**: NVStream_IncompleteRead×2(流截断) + all_tiers_exhausted×1 + buffer_exhausted×1(tier 级烧满 budget) + zombie_empty_completion×1。均非容器 key/超时/冷却参数可治愈。
2. **净 429=0** → KEY_COOLDOWN/429 cooldown 已正确吸收 k1 的高循环计数, 无需调 KEY_COOLDOWN。
3. hm4104 的 2 次 fallback 均因 **all_tiers_exhausted 烧满 180s budget** (NVCF 过载 5 key 全失败), 与 R1228 同签名, 属 NVCF 侧问题。收缩 NVU_TIER_BUDGET_DSV4F0731_NV 只会更快放弃 primary 切 fallback, 不减少 fallback 次数, 反而伤 primary 使用率。
4. 24h ATE=117 与近 5 轮(116-118)背景一致, 稳定无上升; 6h 窗口 ATE=0。
5. per-key 无持续劣化, 错误分散, 无单 key 集中。

## 上次修改效果 (R1221 UPSTREAM_TIMEOUT→45)
- 持续生效: 本窗口无 NVCFPexecTimeout 集中爆发, 延迟稳定, 保持。

## 下一步建议
- 持续观察 hm4104 fallback 频率: 若 <30min 内 >3 次 PRIMARY-FAIL 或 24h ATE 上升(>150), 再评估收缩 NVU_TIER_BUDGET_DSV4F0731_NV(180→120) 以更快切 fallback 换取更低用户延迟, 但需权衡 primary 使用率。
- 关注 k1 持续高 key_cycle_429s(39) 是否累积为实际净失败; 若连续 3 窗口净429>0 且集中 k1, 评估该 key SOCKS5 代理健康。
- 监控 NVCF 高峰时段(03:00, 14:38) SR 是否规律复现, 判断是否 NVCF 端容量问题。