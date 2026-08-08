# RN1075: NOP — NVCF 过载振荡第 9 窗, SR 88.9% 区间中位, 错误全孤立(<3), 无 fallback, ATE=2 低于重评估阈值

日期: 2026-08-08 23:18 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF pexec 链路)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

RN1074 (22:00) SR 85.7% → 本轮 (23:18) SR 88.9%, 回升至 NVCF 过载振荡区间中位。
30min 错误��孤立 (<3)：`all_tiers_exhausted×2 + client_gone_during_flush×1 + stream_absolute_cap×1`，
散布 k0×3/k4×1，无单 key 聚集，0 净 429。**hm4104 近 5min 无 fallback 日志**（本轮链路健康）。
失败均因 NVCF 上游过载（tier 级 exhaust + 流级截断），非本地参数杠杆。
ATE=2 低于 RN1073 设定的重评估阈值（≥3/30min 且伴随 fallback 频繁化），不动 TIER_TIMEOUT_BUDGET_S=180。

## 数据证据

### 30min 主指标
- 总量 36，成功 32，错误 4，其他 0 → **SR = 88.9%** (RN1074: 85.7%)
- Avg/P50/P95: 54792ms / 35885ms / 180034ms (p95≈180s = TIER_TIMEOUT_BUDGET_S=180 烧满)

### 错误分类 (30min)
- all_tiers_exhausted×2 (avg 180035ms) — tier 级，5 key 全过载烧满 budget，非单 key 可调
- client_gone_during_flush×1 (198293ms)
- stream_absolute_cap×1 (174127ms)

### per-key 200 延迟 / 错误
- k0: 7 ok avg38911, err×3 (ATE×2 + absolute_cap×1) — 有错但 avg_ok 居中，非 SOCKS5 出口问题
- k1: 6 ok avg47850, err×0
- k2: 4 ok avg40763, err×0
- k3: 6 ok avg37419, err×0
- k4: 9 ok avg32552, err×1 (client_gone)
- 无"既慢又错"单 key → 排除 key/proxy 层劣化

### 429 / key_cycle
- 净 429 = 0；key_cycle_429s: k0×8, k1×24, k2×3, k4×1（历史计数，非本窗净增 429）

### upstream / finish_reason
- nvcf_pexec 36/32 (SR 88.9%)；integrate 0；finish_reason: tool_calls×26, stop×6

### 趋势
- 6h: 559 total / 492 ok / 67 err → **SR 88.0%**
- 3h 逐小时: 15:00 24/25(96.0%), 14:00 81/91(89.0%), 13:00 62/72(86.1%), 12:00 56/62(90.3%)
- 15:00 逐小时 SR 96% → 近窗回升迹象，需下窗确认
- 24h all_tiers_exhausted: 62（持续上游过载，非本窗异常）

### hm4104 fallback (最近 5min)
- **无 fallback 日志** — 主链路本轮健康，未降级 ms_gw

## 结论

RN1068→RN1075 确认 NVCF 对 dsv4f0731_nv 的过载**持续振荡**（SR 在 80.6%~95.1% 间波动）。
本轮 SR 88.9% 区间中位，错误全孤立 (<3)、无单 key 聚集、无净 429、**无 fallback**。
失败均因 NVCF 上游过载（tier 级 exhaust + 流级截断），非本容器可调参数杠杆。
ATE=2 低于重评估阈值且 fallback 未复现，TIER_TIMEOUT_BUDGET_S=180 维持。为保持健康稳态基线，本轮 **NOP**。

## 下一步建议

- 持续监测 SR：NVCF 过载振荡 (RN1074 85.7% → 本轮 88.9% → 15:00 逐时 96%)。
  关注是否出现连续 2+ 窗口 SR>95% + 错误归零确认进入恢复期。
- ATE=2 仍低于重评估阈值（≥3/30min 且伴随 hm4104 fallback 频繁化），暂不动 TIER_TIMEOUT_BUDGET_S=180。
  若下轮 ATE 聚集至 ≥3 且 fallback 复现，再评估是否缩短 NVU_TIER_BUDGET_DSV4F0731_NV 180→150
  以加速 fallback（牺牲长链成功率换更快降级）。
- 保持当前参数；仅在 NVCF 完全恢复后仍有模式化错误聚集时，才重新评估超时/预算/fast-break。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] env 复核: UPSTREAM_TIMEOUT=50, TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_DSV4F0731_NV=180,
  TIER_COOLDOWN_S=90, KEY_COOLDOWN_S=30, NVU_KEYMGR_429_*=120, NVU_KEYMGR_CONN_*=30/60/3/120,
  NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3 ✓ (docker exec 复核无改动)
- [x] 容器 `dsvf0731_nv40666` Up 21 hours, 未重启 ✓
- [x] 数据完整: 30min SR/延迟/错误分类/per-key/upstream/finish_reason/429/key_cycle/6h/3h/24h/fallback 均已采集
- [x] 错误分类: ATE×2 + absolute_cap×1 + client_gone×1, 全孤立各<3
- [x] per-key: 无既慢又错单key, 错误散布 k0×3/k4×1, 非 SOCKS5/出口 IP 问题
- [x] hm4104 fallback: 无 (本轮主链路健康, 未降级 ms_gw)
- [x] 决策数据驱动: SR 88.9% + 错误全孤立 + 0 净429 + 无fallback + ATE=2低阈值 → NOP, 本地无可调杠杆, 不扰动链路