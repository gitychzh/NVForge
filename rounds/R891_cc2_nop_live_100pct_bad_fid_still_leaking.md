# R891 cc2 NOP 巡检轮 — 实时 100% 干净, 但修正 R890: 兄弟坏 fid 52e1ddb6 仍在被集中轮转 (全败)

轮号: R891 | 日期: 2026-08-07 | 类型: NOP 巡检轮 (不改码)

## 判断
近 30min window cc4101-primary SR=94.7% (89/94), 全部错误 (502×4 + 499×1) 落在 ≤23:35:46 UTC 的
R889 簇2 尾部。**实时自 23:36 UTC 起 102/102 = 100% SR** (20min 干净, live now=23:56 UTC)。
无新错误类, 无进行中降级, **不改码**。

⚠️ **修正 R890**: R890 记「52e1ddb6 不再被轮转 / func_health 已剔除」**不准确**。本轮实拉显示兄弟坏 fid
52e1ddb6 **仍在 dsv4f0731_nv tier 内被集中轮转且全败**: 30min=25/25 bad, 2h=91/91 bad
(NVCFPexecRemoteDisconnected×15、empty_200×4、529×3、Timeout×3, 末次 23:53:27 UTC), 而健康 fid
281478d0 同窗口 94/94 全 pexec_success。这些失败被 buffer 轮转到 281478d0 吸收, 未影响 cc2 请求 SR。

## 数据 (live DB now()=2026-08-06 23:56 UTC)

| 指标 | 值 | 状态 |
|---|---|---|
| 末次 cc4101-primary 错误 | 23:35:46 UTC (cluster2 残尾), ~20min 前 | 已过去 |
| 自 23:36 UTC SR (逐分钟 20min chrono) | **100%** (102 全 200, 0 err) | ✅ 自愈 |
| 30min window cc4101-primary | 200×89 + 502×4 (all_tiers_exhausted, avg 226s) + 499×1 → SR 94.7% | 全为簇2 尾 (≤23:35:46) |
| 30min 错误分类 | all_tiers_exhausted ×4, client_gone_during_flush ×1, stream_absolute_cap ×1 | 已知类, 各自愈 |
| **兄弟坏 fid 52e1ddb6 (dsv4f0731_tier 内)** | **30min=25 次全败 / 2h=91 次全败**; 末次 23:53:27 | ⚠️ 仍被轮转 (修正 R890) |
| **健康 fid 281478d0 (dsv4f0731_tier)** | 30min=94/94 pexec_success, 2h=317/317, 0 bad | ✅ 100% 稳健 |
| nv_gw 30min 日志 | 全 buffer attempt-1 SUCCESS (1.5~19.6s flush), 零 cooldown/429/exhaustion marker | ✅ 健康 |
| dsv4f_nv tier | 2h 内 0 次尝试 (兄弟模型未用) | — |
| fallback | 0 次 | ✅ |
| 三容器 health | nv_gw / cc4101 / dsv4p_nv40066 全 ok, cc4101 primary=dsv4f0731_nv, 5 keys | ✅ |

## 关键判断
- 30min 窗口的失败全为 ≤23:35:46 簇2 尾部 (R889 定界), 非新故障。自 23:36 UTC 起 102 全 200 = 100% SR。
- **52e1ddb6 是已知坏 fid (兄弟 dsv4f_nv 的 function_id), 非 dsv4f0731_nv 首选候选**。2h 内 91 次全败,
  末次 23:53:27 仍在失败, R890「不再被轮转」过时。健康 281478d0 100% 稳健 (317/317)。
- 52e1ddb6 全败被 buffer 跨候选轮转吸收 → 请求级 SR 无影响 (cc2 100%)。但每个失败 RemoteDisconnected
  消耗 ~30-57s key/CDN 预算, 属**纯浪费 + 潜在延迟风险**。
- 不立即 kill 52e1ddb6 的原因: (a) 当前对 cc2 无请求级影响; (b) R889 已警示过度 pin 削弱跨候选容灾
  (281478d0 若将来 surge, 52e1ddb6 即便差也是最后的候选); (c) 需先精确定位 52e1ddb6 注入 dsv4f0731
  rotation 的路由源 (共享 NVCF model 串 deepseek-v4-flash 导致的 tier 歧义?), 数据不足不改码。
- func_health HEALTH_THRESHOLD=0.10 + select_healthy 对 dsv4f0731_nv 候选 [281478d0] 不可能返回
  52e1ddb6 → 注入点必在更上游 (多 tier/多 key 轮转合并), 留待下轮数据定位。

## 改动
无 (NOP)。只修正 R890 对 52e1ddb6 状态的记录。

## 验证
- curl 40006/40066/4101 → 三容器 ok, nv_gw 5 keys, cc4101 primary=dsv4f0731_nv。
- nv_gw 日志全 buffer attempt-1 一次成交 (1.5~19.6s), 零 exhaustion/cooldown/429 marker。
- 逐分钟 20min 0 bad (23:36→23:56)。

## 下一步
- 30min 窗口右移, 簇2 尾部 (23:35:46) 滑出 → 下轮 window SR 预期回 100%。
- 优先监控: 52e1ddb6 是否继续以 ~91/2h + 全败速率被轮转; 定位其注入 dsv4f0731 rotation 的路由源
  (tier 共用 model 串 → 候选池合并?) 后再决定是否从候选剔除/单独降级惩罚。
- 保持 cc4101-primary fallback=dsv4f0731_nv 不动。

## 参数快照
无 env/源码改动。同 R890。