# R1229: dsv4f0731_nv40666 NOP — 30min SR=94.5%(52/55), 3错全为NVCF瞬态(2×NVStream_IncompleteRead + 1×zombie_empty_completion), 无429无fallback, 24h ATE=116稳定

## 结论: NOP (不改任何参数)

## 依据 (30min 窗口, 2026-08-09 ~14:32)

| 指标 | 值 |
|---|---|
| 总量/成功/失败 | 55 / 52 / 3 (SR=94.5%) |
| Avg/P50/P95 | 42968 / 28538 / 124675 ms |
| 净429 | 0 |
| Fallback | 0 (hm4104 最近5min无fallback日志) |
| upstream_type | nvcf_pexec 55 req, 52 SR=94.5% (100% pexec, 无integrate) |
| finish_reason | tool_calls 43, stop 9 |

### 错误分类
| error_type | n | avg_ms | key |
|---|---|---|---|
| NVStream_IncompleteRead | 2 | 35883/36380 | k0/k3 各1 |
| zombie_empty_completion | 1 | 13059 | k2 |

### per-key 200 延迟
| key | n | avg | p95 |
|---|---|---|---|
| 0 | 8 | 33319 | 77436 |
| 1 | 14 | 47633 | 95076 |
| 2 | 8 | 51759 | 103888 |
| 3 | 8 | 30067 | 74792 |
| 4 | 14 | 49314 | 133669 |

各区均衡(30-52s), 无 key 持续劣化。错误分散 k0/k2/k3, 各1次, 不集中。

### key_cycle_429s (内部循环计数, 非净错误)
- k0=15, k1=35, k2=3, k3=2 (k4=0)
- k1 偏高(35)但 key manager 已吸收(净429=0), 与 R1224/R1226/R1227 模式一致 → key cooldown 工作正常, 无需调 KEY_COOLDOWN。

### 趋势
- 6h: 622/586 = 94.2% SR, 36错, 0 ATE
- 3h逐小时: 06h=62/59(95.2%) / 05h=92/85(92.4%) / 04h=115/110(95.7%) / 03h=33/26(78.8%, 已恢复)
- 24h all_tiers_exhausted=116 (与 R1224=116/R1226=116/R1227=117/R1228=118 持平, 稳定无上升)

## 为何不改
1. SR=94.5% 接近 95% 阈值, 3 个错误全部为 **NVCF 侧瞬态**: NVStream_IncompleteRead(流被上游截断) ×2 + zombie_empty_completion(zombie报告200无内容, 仅13s, 未达 NVU_EMPTY_200_FASTBREAK=3 阈值) ×1。均非容器 key/超时/冷却参数可治愈。
2. **净 429=0** → KEY_COOLDOWN/429 cooldown 已正确吸收 k1 的高循环计数。
3. **无 fallback 触发**(容器级), 无 per-key 持续劣化。
4. 24h ATE=116 与近 5 轮(108-118)背景一致, 稳定无上升; 6h 窗口 ATE=0。
5. 03:00 峰值时段 SR=78.8% 为 NVCF 共享负载瞬态, 已自恢复(04h=95.7%, 06h=95.2%), 非本容器可控。

## 上次修改效果 (R1221 UPSTREAM_TIMEOUT→45)
- 持续生效: 本窗口无 NVCFPexecTimeout 集中爆发, 延迟稳定, 保持。

## 下一步建议
- 若单窗口 all_tiers_exhausted >3 次 或 24h ATE 上升(>150), 考虑 NVU_TIER_BUDGET_DSV4F0731_NV 180→200 给予更多 key 重试时间(应对 NVCF 过载时 5key 全 burn), 但需权衡单请求延迟。
- 关注 k1 持续高 key_cycle_429s(35)是否在后续窗口累积为实际净失败; 若连续 3 窗口净429>0 且集中在 k1, 再评估该 key 的 SOCKS5 代理健康。
- 持续观察 NVCF 侧过载是否在高峰时段(03:00 SR=78.8%)规律复现。