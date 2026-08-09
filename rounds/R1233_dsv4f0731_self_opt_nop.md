# R1233: dsv4f0731_nv40666 self-opt NOP — 30min SR=83.8%(31/37)回升, NVCF过载burst ATE×4残余, hm4104 fallback归零, 24h ATE=121稳定

> 时间: 2026-08-09 15:56 UTC (R1232 后 ~1h)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
> 状态: **NOP (无参数修改)** — 30min SR 83.8% (31/37), 较 R1232 (66.7%) 回升; 6h SR 91.4%;
> hm4104 fallback 近 5min **归零** (R1232 多次 PRIMARY-FAIL), NVCF 过载尾抖动, 非本容器可调

## 结论: NOP (不改任何参数)

## 依据 (30min 窗口, 2026-08-09 ~15:56)

| 指标 | 值 |
|---|---|
| 总量/成功/失败 | 37 / 31 / 6 (SR=83.8%) |
| Avg/P50/P95 | 77401 / 70668 / 180043 ms |
| 净429 | 0 |
| upstream_type | nvcf_pexec 37 req, 31 SR=83.8% — 100% pexec, 无integrate |
| finish_reason | tool_calls 25, stop 6 |

### 错误分类 (6错, 集中于 k0 ATE + 分散残余)
| error_type | n | avg_ms |
|---|---|---|
| all_tiers_exhausted | 4 | 152378 |
| client_gone_during_flush | 1 | 209369 |
| stream_absolute_cap | 1 | 167916 |

### per-key 200 延迟 (count/avg/p95)
- k0: 13 / 58339 / 125923 | k1: 6 / 67560 / 156858 | k2: 6 / 64859 / 121078 | k3: 5 / 64191 / 119914 | k4: 1 / 3176 / 3176
- 各区 58-68s 均衡 (过载期偏慢), k0 负载最重 (13 req) 但 avg 最低, 无单 key 代理劣化。

### per-key 错误细分
- ATE: k0×4 (152s≈budget 烧满, tier 级错误) | client_gone: k1×1 (209s) | stream_absolute_cap: k3×1 (167s)
- k0 ATE 集中为轮转起始位伪象 (tier 级 5-key 全失败归属), 非 k0 代理故障。

### key_cycle_429s (内部循环计数, 非净错误)
- k0=9, k1=24, k2=3, k3=1 (k4=0)
- k1 持续偏高(24)但 key manager 已吸收 (净429=0), 与 R1224-R1232 模式一致 → cooldown 工作正常。

### hm4104 fallback (最近5min)
- **无 fallback 日志** — 较 R1232 的多次 PRIMARY-FAIL-STREAM 502 + 1 FALLBACK-FAIL 明显改善。
  主链路 nv_gw 端到端恢复, 不再需要切 ms_gw 兜底。

### 趋势
- 6h: 583/533 = **91.4% SR**, 50 err, 0 429 (与 R1232 6h 91.4% 持平)
- 3h逐小时: 07h=57/70(81.4%) / 06h=100/111(90.1%) / 05h=85/92(92.4%) / 04h=2/3(低样本)
  → 最近一小时 81.4% 略低但为 ATE burst 小样本瞬态, 前几小时 90-92% 健康。
- 24h all_tiers_exhausted=121 (较 R1232 118 微升, 仍稳于 116-122 背景带, 无恶化)

## 为何不改
1. **6 个错误全部为 NVCF 侧信号**: ATE×4 (152s≈budget 烧满 = 5 key 全失败, tier 级) + client_gone + stream_absolute_cap,
   **均非容器 key/超时/冷却参数可治愈**。6h SR=91.4% 健康, 30min 83.8% 较 R1232 66.7% 回升, 为过载尾抖动小样本。
2. **净 429=0** → KEY_COOLDOWN/429 cooldown 已正确吸收 k1 高循环计数, 无需调 KEY_COOLDOWN。
3. **hm4104 fallback 已归零** → 主链路恢复, 无需收缩 NVU_TIER_BUDGET_DSV4F0731_NV (180→120)
   只会更快放弃 primary 切 fallback, 不减少 fallback (当前已 0), 反伤 primary 使用率。
4. **per-key 无持续劣化**: k0 ATE 集中为轮转起始位伪象 (avg_ok 58s 全 key 最低), k1 无净失败 (429 被吸收),
   k3 单次 stream_absolute_cap 为过载残余。upstream 100% pexec 运行正常, 无需调 integrate 路由。
5. **本窗口小样本 (37 req) + 规律性 NVCF 高峰瞬态**, 非长期趋势。env 全程未动,
   SR 已自 R1232 的 66.7% 回升至 83.8%, 证实为 NVCF 自发恢复而非参数效应。

当前 env 维持: UPSTREAM_TIMEOUT=45, TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_DSV4F0731_NV=180,
KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90, NVU_KEYMGR_429_BASE/MAX_COOLDOWN=120,
NVU_KEYMGR_CONN_BASE=30/MAX=60/FAIL_THRESHOLD=3/LONG=120, NVU_PEXEC_TIMEOUT_FASTBREAK=3,
NVU_EMPTY_200_FASTBREAK=3。**无改动。**

## 当前状态 (30min)
- 30min SR: **83.8%** (31/37) / **6h SR: 91.4%** (533/583)
- Avg/P50/P95: 77401ms / 70668ms / 180043ms
- 错误 (30min): `all_tiers_exhausted` 4 (152s), `client_gone_during_flush` 1 (209s), `stream_absolute_cap` 1 (167s)
- 429: 0
- upstream: pexec 37 (200=31, avg ~77s), integrate 0
- fallback: **0** (hm4104 近 5min 无 fallback 日志)

## 上次修改效果 (R1221 UPSTREAM_TIMEOUT=45, 持续生效)
- 无 NVCFPexecTimeout 集中爆发, 无超时相关链错误, 延迟稳定。本窗口错误全为 NVCF 过载 ATE 残余,
  非超时配置问题。hm4104 fallback 自 R1232 多次 → 本轮归零, 主链路恢复。

## 下一步建议
- 持续观察 hm4104 fallback 频率: 若 <30min 内 >3 次 PRIMARY-FAIL 或 24h ATE 上升(>150), 再评估收缩
  NVU_TIER_BUDGET_DSV4F0731_NV(180→120) 换取更快切 fallback, 但需权衡 primary 使用率 (当前 0 fallback, 非正解)。
- 关注 07:00 后 SR 是否随 NVCF 过载完全消退回升至 ≥90% (30min 与 6h 对齐); 若回升则判定过载尾抖动结束。
- 关注 k1 持续高 key_cycle_429s(24) 是否累积为实际净失败; 若连续 3 窗口净429>0 且集中 k1, 评估该 key SOCKS5 代理健康。
- 下轮重点: (a) 30min SR 是否 ≥90%, (b) all_tiers_exhausted 是否降至 ≤2, (c) hm4104 fallback 是否保持 0。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] 数据完整: 30min/6h/3h/24h/per-key/fallback 均已采集
- [x] 错误深度: all_tiers_exhausted 4 (152s=budget 烧满) + client_gone 1 + stream_absolute_cap 1, 429=0, NVCF 过载残余
- [x] k0 错误集中 (4/6 ATE) 判定为轮转起始位伪象 (avg_ok 58s 全 key 最低, 代理健康), 非 key 劣化
- [x] 决策数据驱动: NVCF 过载尾抖动小样本瞬态, 无参数可干净归因 → NOP, 不扰动配置