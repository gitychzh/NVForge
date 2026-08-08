# RN1074: NOP — NVCF 过载振荡第 8 窗, SR 85.7% 回落, 错误全孤立(<3)不可调, hm4104 fallback 传导续(设计兜底)

日期: 2026-08-08 22:00 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF pexec 链路)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

RN1073 (21:48 UTC) 报告 SR 回升至 92.3%。本轮 (22:00 UTC) 延续 NVCF 过载振荡相位，SR 回落至 85.7%。
30min 错误全孤立 (<3)：`all_tiers_exhausted×2 + client_gone_during_flush×1 + stream_absolute_cap×1`，
散布 k0×2/k2×1，无单 key 聚集，0 净 429。失败均因 NVCF 上游过载（tier 级 exhaust + 流级截断），
非本地参数杠杆。hm4104 fallback 传导延续（PRIMARY-FAIL-STREAM 502@180s → breaker-skip ×2 →
FALLBACK-STREAM），为设计 failover 兜底，非本容器可调。

## 数据证据

### 30min 主指标
- 总量 28，成功 24，错误 4，其他 0 → **SR = 85.7%** (RN1073: 92.3%)
- Avg/P50/P95: 70929ms / 47389ms / 229633ms (失败集中在 ~180s = TIER_TIMEOUT_BUDGET_S=180 烧满)

### 错误分类 (30min)
- all_tiers_exhausted×2 (avg 180064ms) — tier 级，5 key 全过载，非单 key 可调
- client_gone_during_flush×1 (186854ms)
- stream_absolute_cap×1 (176486ms)

### per-key 200 延迟 / 错误
- k0: 3 ok avg46034, err×2 (ATE+cap) — 有错但延迟正常，非 SOCKS5 出口问题
- k1: 6 ok avg74878, err×0
- k2: 3 ok avg63075, err×1 (client_gone)
- k3: 5 ok avg31977, err×0
- k4: 7 ok avg46581, err×0
- 无"既慢又错"单 key → 排除 key/proxy 层劣化

### 429 / key_cycle
- 净 429 = 0；key_cycle_429s: k0×8, k1×18, k2×1, k3×1（成功前的历史 429 计数，非本窗净增）

### upstream / finish_reason
- nvcf_pexec 28/24 (SR 85.7%)；finish_reason: stop×12, tool_calls×12

### 趋势
- 6h: 572 total / 504 ok / 68 err → **SR 88.1%**
- 3h 逐小时: 13:00 63/54(85.7%), 12:00 91/81(89.0%), 11:00 92/82(89.1%), 10:00 4/2
- 24h all_tiers_exhausted: 54（持续上游过载，非本窗异常）

### hm4104 fallback (最近 5min)
- PRIMARY-FAIL-STREAM 502 after 180049ms（≈TIER_TIMEOUT_BUDGET_S 烧满）
- PRIMARY-BREAKER-SKIP-STREAM ×2 → FALLBACK-STREAM ×2
- 设计 failover 兜底（breaker skip → ms_gw），验证安全网持续正常

## 结论

RN1068→RN1074 确认 NVCF 对 dsv4f0731_nv 的过载**持续振荡**（SR 在 80.6%~92.3% 间波动）。
本轮 SR 85.7% 回落至区间中位，错误全孤立 (<3)、无单 key 聚集、无净 429。失败均因 NVCF 上游
过载（tier 级 exhaust + 流级截断），非本容器可调参数杠杆。hm4104 fallback 传导为设计 failover
兜底（breaker skip → ms_gw），安全网持续正常。为保持健康稳态基线，本轮 **NOP**。

## 下一步建议

- 持续监测 SR：NVCF 过载振荡 (RN1073 92.3% → 本轮 85.7%)。关注是否出现连续 2+ 窗口 SR>95% +
  错误归零确认进入恢复期。
- ATE=2 仍低于 RN1073 设定的重评估阈值（≥3/30min 且伴随 hm4104 fallback 频繁化），暂不动
  TIER_TIMEOUT_BUDGET_S=180。若下轮 ATE 聚集至 ≥3 且 fallback 继续频繁化，再评估是否缩短预算
  （长 tool_calls 链常烧满预算 → 502 传导到 hm4104）。
- 保持当前参数；仅在 NVCF 完全恢复后仍有模式化错误聚集时，才重新评估超时/预算/fast-break。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] 数据完整: 30min SR/延迟/错误分类/per-key/upstream/finish_reason/429/key_cycle/6h/3h/24h/fallback 均已采集
- [x] 错误分类: ATE×2 + absolute_cap×1 + client_gone×1, 全孤立各<3
- [x] per-key: 无既慢又错单key, 错误散布 k0×2/k2×1, 非 SOCKS5/出口 IP 问题
- [x] 请求级: 200×24 + 错误×4, p95≈230s budget 烧满, 与 hm4104 fallback 传导吻合
- [x] hm4104 fallback: PRIMARY-FAIL-STREAM 502@180s → breaker-skip ×2 → ms_gw, 属设计兜底
- [x] 决策数据驱动: SR 85.7% + 错误全孤立 + 0 净429 + fallback 为设计兜底 → NOP, 本地无可调杠杆, 不扰动链路