# R1232: dsv4f0731_nv40666 self-opt NOP — 30min SR=66.7%(18/27), NVCF过载burst ATE×7烧满180s, hm4104多次fallback+1 fallback-fail, 24h ATE=122微升

> 时间: 2026-08-09 15:44 UTC (R1231 后 ~1h)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
> 状态: **NOP (无参数修改)** — 30min SR 66.7% (18/27), 为 NVCF 过载 burst 小样本瞬态, 与 R1224-R1231 同签名

## 结论: NOP (不改任何参数)

## 依据 (30min 窗口, 2026-08-09 ~15:44)

| 指标 | 值 |
|---|---|
| 总量/成功/失败 | 27 / 18 / 9 (SR=66.7%) |
| Avg/P50/P95 | 100961 / 99945 / 218435 ms |
| 净429 | 0 |
| upstream_type | nvcf_pexec 25 req, 18 SR=72%; null 2 (ATE null-key上报, 0 SR) — 100% pexec, 无integrate |
| finish_reason | tool_calls 13, stop 5 |

### 错误分类 (9错, 集中于 k0/null)
| error_type | n | avg_ms |
|---|---|---|
| all_tiers_exhausted | 7 | 185063 |
| client_gone_during_flush | 1 | 209369 |
| stream_absolute_cap | 1 | 167916 |

### per-key 200 延迟 (count/avg/p95)
- k0: 4 / 76743 / 111638 | k1: 3 / 63934 / 111088 | k2: 4 / 51810 / 93906 | k3: 6 / 53405 / 123843 | k4: 1 / 26783 / 26783
- 各区 26-76s (偏慢, 过载期), 无单 key 异常突出。

### per-key 错误细分
- ATE: k0×5 (157s) + null×2 (252s, tier 级烧满上报) | client_gone: k1×1 (209s) | stream_absolute_cap: k3×1 (167s)
- k0 错误集中(5/7 ATE) 为轮转起始位伪象 — ATE 是 tier 级 (5 key 全失败), 归属 key 为轮转伪象。

### key_cycle_429s (内部循环计数, 非净错误)
- k0=8, k1=17, k2=1, k3=1 (k4=0)
- k1 持续偏高(17)但 key manager 已吸收 (净429=0), 与 R1224-R1231 模式一致 → cooldown 工作正常。

### hm4104 fallback (最近30min)
- 多次 PRIMARY-FAIL-STREAM: `nv_gw 流式 server_5xx status=502 after 180051/180056 ms` → **all_tiers_exhausted 烧满整段180s budget** → 切 ms_gw fallback + circuit OPEN + BREAKER-SKIP
- 1× CONTENT_FILTER_ZOMBIE (R840 zombie) → PRIMARY-ZOMBIE-FALLBACK
- 1× **FALLBACK-FAIL-STREAM**: `ms_gw 流式 timeout status=0 after 70059ms` — 连 fallback 也超时 (ms_gw 侧 transient)
- 1× PRIMARY-RETRY-OK: primary retry 成功 (fallback timeout 后) — 主链路恢复
- 根因: NVCF 共享过载时 5 key 全失败、tier 级 ATE 烧满 180s, 非本容器超时/冷却/路由可控。

### 趋势
- 6h: 580/530 = **91.4% SR**, 50 err, 0 429 (较 R1231 6h 93.7% 微降, 过载复发)
- 3h逐小时: 07h=37/49(75.5%) / 06h=100/111(90.1%) / 05h=85/92(92.4%) / 04h=36/37(97.3%)
  → 最近一小时 (07h) SR 下滑至 75.5%, 为过载 burst 窗, 前几小时 90-97% 健康。
- 24h all_tiers_exhausted=122 (较 R1231 118 微升, 跨 24h 累积, 频率未恶化)

## 为何不改
1. **9 个错误全部为 NVCF 侧信号**: ATE×7 (180s budget 烧满 = 5 key 全失败, tier 级) + client_gone + stream_absolute_cap,
   **均非容器 key/超时/冷却参数可治愈**。6h SR=91.4% 仍健康, 最近一小时 75.5% 为 ATE burst 小样本瞬态 (27 req)。
2. **净 429=0** → KEY_COOLDOWN/429 cooldown 已正确吸收 k1 高循环计数, 无需调 KEY_COOLDOWN。
3. **hm4104 多次 fallback 均因 all_tiers_exhausted 烧满 180s budget** (NVCF 过载 5 key 全失败),
   与 R1228-R1231 同签名, 属 NVCF 侧问题。收缩 NVU_TIER_BUDGET_DSV4F0731_NV (180→120) 只会更快放弃
   primary 切 fallback (甚至 primary 短暂恢复时也过早放弃), 不减少 fallback 次数, 反伤 primary 使用率。
4. **per-key 无持续劣化**: k0 错误集中为轮转起始位 ATE 伪象 (非代理故障), k1 无净失败 (429 被吸收),
   k3 单次 stream_absolute_cap 为过载残余。upstream 100% pexec 运行正常, 无需调 integrate 路由。
5. **本窗口小样本 (27 req) + 规律性 NVCF 高峰瞬态**, 非长期趋势。env 全程未动, NVCF 恢复后 SR 自会回升
   (R1043→R1044 已证此模式)。

当前 env 维持: UPSTREAM_TIMEOUT=45, TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_DSV4F0731_NV=180,
KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90, NVU_KEYMGR_429_BASE/MAX_COOLDOWN=120,
NVU_KEYMGR_CONN_BASE=30/MAX=60/FAIL_THRESHOLD=3/LONG=120, NVU_PEXEC_TIMEOUT_FASTBREAK=3,
NVU_EMPTY_200_FASTBREAK=3。**无改动。**

## 当前状态 (30min)
- 30min SR: **66.7%** (18/27) / **6h SR: 91.4%** (530/580)
- Avg/P50/P95: 100961ms / 99945ms / 218435ms
- 错误 (30min): `all_tiers_exhausted` 7 (185s), `client_gone_during_flush` 1 (209s), `stream_absolute_cap` 1 (167s)
- 429: 0
- upstream: pexec 25 (200=18, avg ~88s), integrate 0
- fallback: 多次 (hm4104 PRIMARY-FAIL 502 烧满 budget + 1 FALLBACK-FAIL ms_gw timeout + 1 PRIMARY-RETRY-OK)

## 上次修改效果 (R1221 UPSTREAM_TIMEOUT=45, 持续生效)
- 无 NVCFPexecTimeout 集中爆发, 无超时相关链错误, 延迟稳定。本窗口错误全为 NVCF 过载 ATE, 非超时配置问题。

## 下一步建议
- 持续观察 hm4104 fallback 频率: 若 <30min 内 >3 次 PRIMARY-FAIL 或 24h ATE 上升(>150), 再评估收缩
  NVU_TIER_BUDGET_DSV4F0731_NV(180→120) 以更快切 fallback, 但需权衡 primary 使用率 (当前反复判定非正解)。
- 关注 07:00 后 SR 是否随 NVCF 过载消退回升至 ≥90%; 若下一小时仍 <80% 且 ATE 持续, 确认 NVCF 容量受限。
- 关注 k1 持续高 key_cycle_429s(17) 是否累积为实际净失败; 若连续 3 窗口净429>0 且集中 k1, 评估该 key SOCKS5 代理健康。
- 监控 ms_gw fallback 侧 1× FALLBACK-FAIL timeout (70s) — 若 ms_gw 侧也频繁超时, 端到端可用性会受双层过载影响。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] 数据完整: 30min/6h/3h/24h/per-key/fallback 均已采集
- [x] 错误深度: all_tiers_exhausted 7 (185s=budget 烧满) + client_gone 1 + stream_absolute_cap 1, 429=0, NVCF 过载
- [x] k0 错误集中 (5/7 ATE) 判定为轮转起始位 ATE 伪象 (tier 级错误), 非 key 劣化
- [x] 决策数据驱动: NVCF 过载 burst 小样本瞬态, 无参数可干净归因 → NOP, 不扰动配置