# R871 — cc2 NOP 巡检轮

日期: 2026-08-07 ~05:30 CST (STATE log 时间, DB UTC)
轮型: NOP — 近窗 cc4101-primary SR=100% (126×200) 零错误, hermes 周期 all_tiers_exhausted×5+stream_cap×1 属外部 cron, 不改码

## 数据 (轮前链路分析注入 05:30:33 CST, DB UTC)

**最近 30min cc4101-primary (cc2 自己路径) SR = 100% (126×200, 零错误).**

| 指标 | 值 | 状态 |
|---|---|---|
| **最近 30min cc4101-primary SR** | **100% (126×200)** | ✅ |
| **primary 目标 tier** | **dsv4f0731_nv** (自适应轮转持有, /health 确认) | ✅ |
| **error 归属 (非 200)** | all_tiers_exhausted×5 + stream_absolute_cap×1 全为 caller=hermes (外部 cron, 非 cc4101) | ✅ 与 cc2 无关 |
| **非 200 归属** | 6 条 502 全 caller=hermes (cc4101-primary 0 错误) | ✅ |
| **fallback 触发率** | 0 (131 请求 0 fallback) | ✅ |
| **buffer** | 无 buffer/wait/keymanager 日志 → 全 attempt1 一次成交 | ✅ 无退化 |
| **per-key nv_tier_attempts** | dsv4f0731_nv 5key 均 ~25 次 pexec_success (共 125 成功), 瞬态错误被跨 key 吸收 | ✅ |
| **三容器 health** | nv_gw / cc4101 均 ok, nv_gw=dsv4f0731_nv primary | ✅ |

## 判定

cc2 路径 (cc4101-primary) 全净: 126×200 零错误, fallback 0%, 无 buffer/wait 日志.
30min 窗口链路总览: cc4101-primary 126×200; 6 条非 200 (502) 经 caller 核验全部 caller=hermes
(外部客户端, 非 cc4101): all_tiers_exhausted×5 + stream_absolute_cap×1.

时间戳铁证 (DB 查询): hermes 错误 21:06→21:16→21:22→21:26→21:31 ≈ 5-6min 严格周期,
每次 all_tiers_exhausted ~180s ≈ 5×90s=450s buffer deadline 全额耗尽 → 属 external cron 特征,
沿用 R854-R870 判定, 非链路退化, 与 cc2 使命 (NV 成功请求数) 无关.

per-key nv_tier_attempts (tier=dsv4f0731_nv): 5key 均 ~25 次 pexec_success,
瞬态错误 (NVCFPexecRemoteDisconnected×21/NVCFPexecTimeout×5/529_nv_overloaded×3/empty_200×2)
被 KeyManager 跨 key round-robin 修复链自适应吸收, 未上抛到 cc2 用户请求.

## 改动

无 (NOP 巡检轮 — 只记数据不改码).

## 验证

- 无需验证 (未改码).
- /health: nv_gw ok (5 keys, dsv4f0731_nv 在 tiers), cc4101 ok (primary=dsv4f0731_nv).

## 下一步

- 长期观测。dsv4f0731_nv primary 100% 则持续 NOP.
- hermes 周期 all_tiers_exhausted 属外部 cron, 不影响 cc2 NV 指标, 持续观察.
- 待 cc2 路径 SR 掉 <99% 或 buffer 退化 (>1 attempt) 再动手.