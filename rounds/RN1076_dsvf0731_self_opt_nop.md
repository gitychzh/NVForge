# RN1076: NOP — NVCF 过载振荡进入恢复期, SR 98.1% 显著回升, 错误单点孤立, 0 净429, 无 fallback

日期: 2026-08-09 00:10 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF pexec 链路)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

RN1075 (23:18) SR 88.9% → 本轮 (00:10) SR **98.1%**, 显著回升至稳定区, 属 NVCF 过载振荡进入恢复期。
30min 错误仅 `all_tiers_exhausted×1` (孤立, <3), 0 净 429, **hm4104 近 5min 无 fallback 日志**。
SR>95% 且无异常错误聚集 → 触发 NOP 规则, 本地无可调杠杆, 不扰动链路稳态。

## 数据证据

### 30min 主指标
- 总量 53, 成功 52, 错误 1, 其他 0 → **SR = 98.1%** (RN1075: 88.9%)
- Avg/P50/P95: 42836ms / 25378ms / 151506ms (较 RN1075 平均 54792ms 明显下降)

### 错误分类 (30min)
- all_tiers_exhausted×1 (180052ms) — tier 级单次, 5 key 单窗过载, 孤立<3 不可调

### per-key 200 延迟 / 错误
- k0: 8 ok avg26262, err×1 (ATE) — 有错但 avg_ok 最低, 非 SOCKS5 出口问题
- k1: 12 ok avg57789, err×0
- k2: 9 ok avg27424, err×0
- k3: 9 ok avg53794, err×0
- k4: 14 ok avg32550, err×0
- 无"既慢又错"单 key, 错误单点落在最快 key k0 → 随机过载, 非 key/proxy 层劣化

### 429 / key_cycle
- 净 429 = 0；key_cycle_429s: k0×17, k1×33, k2×3 (历史计数, 非本窗净增 429)

### upstream / finish_reason
- nvcf_pexec 53/52 (SR 98.1%)；integrate 0；finish_reason: tool_calls×37, stop×15

### 趋势
- 6h: 549 total / 490 ok / 59 err → **SR 89.3%** (持续爬升)
- 3h 逐小时: 16:00 16/15(93.8%), 15:00 100/96(96.0%), 14:00 91/81(89.0%), 13:00 61/55(90.2%)
- 15:00+16:00 连续两窗 SR≥93.8% → 近窗稳定回升确认
- 24h all_tiers_exhausted: 65 (历史累积计数, 非本窗异常)

### hm4104 fallback (最近 5min)
- **无 fallback 日志** — 主链路本轮健康, 未降级 ms_gw

## 结论

RN1068→RN1076 NVCF 过载振荡自 RN1075 起进入恢复期: SR 呈现
RN1074 85.7% → RN1075 88.9% → **本轮 98.1%** 连续两窗回升, 且 15:00/16:00 逐小时均 ≥93.8%。
本轮 SR 98.1% 稳定区, 错误单点孤立 (<3)、无单 key 聚集、0 净 429、**无 fallback**。
失败均因 NVCF 上游过载单次, 非本容器可调参数杠杆。为保持健康稳态基线, 本轮 **NOP**。

## 下一步建议

- 持续监测 SR 确认恢复稳态: 若连续 2+ 窗口 SR>95% + 错误归零, 则可判定 NVCF 过载振荡结束,
  进入健康基线, 后续 NOP 轮可简化为最小状态报告。
- ATE=1 远低重评估阈值, TIER_TIMEOUT_BUDGET_S=180 / NVU_TIER_BUDGET_DSV4F0731_NV=180 维持不动。
- 保持当前参数; 仅在 NVCF 恢复后仍有模式化错误聚集时, 才重新评估超时/预算/fast-break。

## 验证清单
- [x] /health 正常 (status ok, proxy_role passthrough, 5 keys, port 40666)
- [x] env 复核: UPSTREAM_TIMEOUT=50, TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_DSV4F0731_NV=180,
  TIER_COOLDOWN_S=90, KEY_COOLDOWN_S=30, NVU_KEYMGR_429_*=120, NVU_KEYMGR_CONN_*=30/60/3/120,
  NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3 ✓ (docker exec 复核无改动)
- [x] 容器 `dsvf0731_nv40666` Up 22 hours, 未重启 ✓
- [x] 数据完整: 30min SR/延迟/错误分类/per-key/upstream/finish_reason/429/key_cycle/6h/3h/24h/fallback 均已采集
- [x] 错误分类: ATE×1 单点孤立 <3
- [x] per-key: 无既慢又错单key, 错误单点落在最快 key k0, 非 SOCKS5/出口 IP 问题
- [x] hm4104 fallback: 无 (本轮主链路健康, 未降级 ms_gw)
- [x] 决策数据驱动: SR 98.1% + 错误单点孤立 + 0 净429 + 无fallback → NOP, 本地无可调杠杆, 不扰动链路