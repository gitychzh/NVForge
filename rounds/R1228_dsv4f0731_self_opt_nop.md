# R1228: dsv4f0731_nv40666 self-opt NOP — 30min SR=94.2%(49/52), 错均NVCF瞬态(3×all_tiers_exhausted+stream_cap+client_gone), 无429无fallback, 24h ATE=118稳定

## 结论: NOP (不改任何参数)

## 依据 (30min 窗口, 2026-08-09 ~13:38)

| 指标 | 值 |
|---|---|
| 总量/成功/失败 | 52 / 49 / 3 (SR=94.2%) |
| Avg/P50/P95 | 46292 / 25426 / 166028 ms |
| 净429 | 0 |
| Fallback | 0 (容器级) |
| upstream_type | nvcf_pexec 52 req, 49 SR=94.2% |
| finish_reason | tool_calls 40, stop 9 |

### 错误分类 (23min 完整窗口, 5错)
| error_type | n | status | duration_ms | key_cycle_429s | key |
|---|---|---|---|---|---|
| all_tiers_exhausted | 3 | 502 | 180043/180041/180020 | 0 | 0/0/0 |
| stream_absolute_cap | 1 | 502 | 150273 | 3 | 2 |
| client_gone_during_flush | 1 | 499 | 192088 | 1 | 3 |

### per-key 200 延迟
- k0: 10req/36464 | k1: 8req/37808 | k2: 12req/49129 | k3: 11req/28435 | k4: 8req/35695
- 各 key 延迟均衡(28-49s), 无 key 持续劣化。

### tier_attempts (30min)
- pexec_success=38, NVCFPexecRemoteDisconnected=15 (avg 35.5s), NVCFPexecTimeout=10 (avg 39.6s)

### 趋势
- 6h: 637/602 = 94.5% SR
- 3h逐小时: 05h=63/59(93.7%) / 04h=115/110(95.7%) / 03h=74/63(85.1%, 已恢复) / 02h=36/34
- 24h all_tiers_exhausted=118 (R1227=117, 稳定)

## 分析

**all_tiers_exhausted ×3 的根因**: 3 次 ATE 的 key_cycle_429s **全为 0** → 说明 180s tier budget 是被 **NVCF 侧超时(10) + 断连(15)** 消耗殆尽, 而非 429 配额耗尽。当 NVCF 过载时, 5 key 各尝试 ~40s(NVCFPexecTimeout avg 39.6s) 即 5×40=200s > 180s budget, 遂触发 all_tiers_exhausted。这是 **NVCF 侧瞬态过载**, 非本容器 key/超时/冷却参数杠杆可治愈。

**stream_absolute_cap (k2, 150s)**: NVCF 流绝对上限, 超长输出边界行为, 单次瞬态。

**client_gone_during_flush (k3, 192s, 499)**: 客户端断开, 非上游错误。

## 为何不改
1. SR=94.2% 接近 95% 阈值, 但 5 错全部为 NVCF 侧瞬态(超时/断连/流上限), 无 429, 无容器级 fallback, 无 per-key 持续劣化。
2. all_tiers_exhausted 的 key_cycle_429s=0 证明根因是 NVCF 过载而非 key 配额 → 调整 KEY_COOLDOWN/429 cooldown 无效。
3. UPSTREAM_TIMEOUT 已从 35→45 (R1221), 当前 45s 合理; 再降会误伤 NVCF 慢响应(pexec p80 正常 18s, 但流输出可到 150s+)。不降。
4. 24h ATE=118 与 R1221-R1227 背景(108-118)一致, 稳定无上升。
5. 逐小时 trend: timeout 稳定(12-14/hr), disconnect 下降(35→21), SR 已自恢复至 95%+。

## 上次修改效果 (R1221 UPSTREAM_TIMEOUT→45)
- 持续生效: 无 NVCFPexecTimeout 集中爆发, 延迟稳定, 保持。

## 下一步建议
- 若单窗口 all_tiers_exhausted >3 次 或 24h ATE 上升(>150), 考虑 NVU_TIER_BUDGET_DSV4F0731_NV 180→200 给予更多 key 重试时间(应对 NVCF 过载时 5key 全 burn), 但需权衡单请求延迟。
- 关注 NVCF 侧过载是否在高峰时段(03:00 SR=85%)复现; 该时段为 NVCF 共享负载, 非本容器可控。