# R890 cc2 NOP 巡检轮 — R889 同源第二波尾部滑窗, 实时 100% 干净 (自 23:36 UTC)

轮号: R890 | 日期: 2026-08-07 | 类型: NOP 巡检轮 (不改码)

## 判断
近 30min 窗口 SR 未见 100% (窗口仍含 R889 所定第二波簇2 的尾部), 但**实时态 100% 干净**。
window: 200×72 + 502×5 + 499×1 = SR 92.3%; 但 live 末次错误 = 23:35:46 UTC, 自 23:36 UTC 起
逐分钟 0 错误, 连续 15+ min 全 200 = **100% SR**, 与 R889 定界完全一致。

## 结论
**NOP, 不改码。** 实时无新错误, 无进行中降级。数据为 R889 第二波 (23:14-23:35 NVCF 降级 + 兄弟坏 fid
52e1ddb6) 的窗口尾界, 非新故障。30min 窗口右移后下一轮预期 window SR 回 100%。

## 数据 (live DB now()=2026-08-06 23:50 UTC)

| 指标 | 值 | 状态 |
|---|---|---|
| 末次 cc4101-primary 错误 | 23:35:46 UTC (cluster2 残尾), ~15min 前 | 已过去 |
| 自 23:36 UTC SR (逐分钟 15min chrono) | 100% (78 全 200, 0 err) | ✅ 自愈 |
| 30min window cc4101-primary | 200×72 + 502×5 (all_tiers_exhausted;buffer_exhausted, avg 226s) + 499×1 (client_gone_during_flush) → SR 92.3% | 全为簇2 尾 (≤23:35:46) |
| 30min 错误分类 | all_tiers_exhausted ×4 (180s/244s), buffer_exhausted ×1, client_gone_during_flush ×1, stream_absolute_cap ×1 | 已知类, 各自愈 |
| per-key × status | 全 pexec_success 为主, 少量 RemoteDisconnected/Timeout/529/empty_200 均匀分布 | 轮转正常吸收 |
| nv_gw 30min 日志 | 全 buffer attempt-1 SUCCESS (6~12s direct flush), 零 cooldown/429/exhaustion/52e1ddb6 | ✅ 健康 |
| fallback | 0 次 (f|89 为总请求计数行) | ✅ |
| 三容器 health | nv_gw / cc4101 / dsv4p_nv40066 全 ok, cc4101 primary=dsv4f0731_nv, 5 keys | ✅ |

## 关键判断
- 本轮 30min 窗口的 502/all_tiers_exhausted 全部落在 ≤23:35:46 的簇2 尾部 (R889 已定界), 非新错误。
- 自 23:36:00 UTC 起逐分钟 0 bad (23:36→23:50 连续 15min 全 200), nv_gw buffer attempt-1 一次成交。
- 无 52e1ddb6 再被轮转, func_health 持续锁定健康 281478d0。
- 无新持久错误类; 对已自愈态过度 pin 削弱跨候选容灾, 不改码。

## 改动
无。

## 验证
- curl 40006/40066/4101 → 三容器 ok, primary=dsv4f0731_nv
- nv_gw 日志零 exhaustion/cooldown/52e1ddb6 marker
- 逐分钟 15min 0 bad

## 下一步
- 30min 窗口右移, 簇2 尾部 (23:35:46) 滑出 → 下一轮 window SR 预期回 100%。
- 保持 cc4101-primary fallback=dsv4f0731_nv 不动; 继续盯 52e1ddb6 是否再被集中轮转。

## 参数快照
无 env/源码改动。同 R889。