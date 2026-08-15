# R1231: dsv4f0731_nv40666 self-opt NOP — 30min SR=86.2%(50/58), NVCF过载burst ATE×4烧满180s, hm4104多次fallback同签名, 24h ATE=118稳定

## 结论: NOP (不改任何参数)

## 依据 (30min 窗口, 2026-08-09 ~14:52)

| 指标 | 值 |
|---|---|
| 总量/成功/失败 | 58 / 50 / 8 (SR=86.2%) |
| Avg/P50/P95 | 55950 / 30658 / 181705 ms |
| 净429 | 0 |
| upstream_type | nvcf_pexec 56 req, 50 SR=89.3%; 2 null(ATE null-key上报) — 100% pexec, 无integrate |
| finish_reason | tool_calls 41, stop 9 |

### 错误分类 (8错, 分散于 k0/k2/k3/null)
| error_type | n | avg_ms |
|---|---|---|
| all_tiers_exhausted | 4 | 228476 |
| NVStream_IncompleteRead | 2 | 58930 |
| buffer_exhausted | 1 | 191030 |
| zombie_empty_completion | 1 | 13059 |

### per-key 200 延迟 (count/avg/p95)
- k0: 7 / 37063 / 78468 | k1: 12 / 41303 / 123277 | k2: 12 / 45981 / 99123 | k3: 8 / 18288 / 29703 | k4: 11 / 50554 / 113901
- 各区均衡(18-50s), k3 延迟最低但样本少。错误分散 k0/k2/k3/null 各1-2次 / ATE×4, 无单 key 持续劣化。

### per-key 错误细分
- ATE: k0×2 + null×2 (null 为 tier 级烧满上报) | IncompleteRead: k0×1 + k3×1 | buffer_exhausted: k2×1 | zombie: k2×1

### key_cycle_429s (内部循环计数, 非净错误)
- k0=23, k1=34, k2=1 (k3/k4=0)
- k1 持续偏高(34)但 key manager 已吸收(净429=0), 与 R1224-R1230 模式一致 → cooldown 工作正常。

### hm4104 fallback (最近30min)
- 多次 PRIMARY-FAIL-STREAM: `nv_gw 流式 server_5xx status=502 after 1800xx ms` → **all_tiers_exhausted 烧满整段180s budget** → 切 ms_gw fallback + circuit OPEN + BREAKER-SKIP
- 1× CONTENT_FILTER_ZOMBIE (R840 zombie, 14:50) → PRIMARY-ZOMBIE-FALLBACK
- 根因: NVCF 共享过载时 5 key 全失败、tier 级 ATE 烧满 180s, 非本容器超时/冷却/路由可控。

### 趋势
- 6h: 623/584 = 93.7% SR, 39错, 0 429
- 3h逐小时: 06h=91/100(91%) / 05h=85/92(92.4%) / 04h=110/115(95.7%) / 03h=8/9(低样本)
- 24h all_tiers_exhausted=118 (与 R1224-R1230 的 116-118 持平, 稳定无上升)

## 为何不改
1. SR=86.2% 低于上轮(91.2%)但为 **NVCF 过载 burst 瞬态**: ATE 从 1→4 是本次窗口核心驱动, 且 24h ATE=118 与近 6 轮(116-118)背景持平, 无上升趋势; 6h SR=93.7% 健康。8 个错误全部为 NVCF 侧信号(ATE/buffer_exhausted/IncompleteRead/zombie), 均非容器 key/超时/冷却参数可治愈。
2. **净 429=0** → KEY_COOLDOWN/429 cooldown 已正确吸收 k1 的高循环计数, 无需调 KEY_COOLDOWN。
3. hm4104 的多次 fallback 均因 **all_tiers_exhausted 烧满 180s budget** (NVCF 过载 5 key 全失败), 与 R1228-R1230 同签名, 属 NVCF 侧问题。收缩 NVU_TIER_BUDGET_DSV4F0731_NV 只会更快放弃 primary 切 fallback, 不减少 fallback 次数, 反而伤 primary 使用率。
4. per-key 无持续劣化, 错误分散, 无单 key 集中。upstream 100% pexec 运行正常, 无需调 integrate 路由。
5. 本窗口小样本(58 请求), ATE burst 属规律性出现的 NVCF 高峰瞬态(此前 14:38 亦复现), 非长期趋势。

## 上次修改效果 (R1221 UPSTREAM_TIMEOUT→45)
- 持续生效: 本窗口无 NVCFPexecTimeout 集中爆发, 无超时相关链错误, 延迟稳定, 保持。

## 下一步建议
- 持续观察 hm4104 fallback 频率: 若 <30min 内 >3 次 PRIMARY-FAIL 或 24h ATE 上升(>150), 再评估收缩 NVU_TIER_BUDGET_DSV4F0731_NV(180→120) 以更快切 fallback 换取更低用户延迟, 但需权衡 primary 使用率。
- 关注 k1 持续高 key_cycle_429s(34) 是否累积为实际净失败; 若连续 3 窗口净429>0 且集中 k1, 评估该 key SOCKS5 代理健康。
- 监控 NVCF 高峰时段(03:00, 14:38) SR 是否规律复现, 判断是否 NVCF 端容量限制(非本容器可调)。