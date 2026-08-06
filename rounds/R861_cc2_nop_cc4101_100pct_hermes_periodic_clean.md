# R861 — cc2 NOP 巡检轮 (2026-08-07 ~05:00 CST)

## 状态
**cc2 自身路径 (cc4101-primary) SR = 100% (124×200) 零错误.** 全 caller dsv4f0731_nv SR=96.2% (125/130), 5 条失败全为 hermes 外部 cron 客户端, 与 cc2 路径无关.

## 本轮数据 (injected @04:54 CST, DB UTC, 复核)

**最近 30min cc4101-primary SR = 100% (124×200, avg 8.8s).**

| 指标 | 值 | 状态 |
|---|---|---|
| **最近 30min cc4101-primary SR** | **100% (124×200)** | ✅ |
| **primary 目标 tier** | **dsv4f0731_nv** (自适应轮转持有) | ✅ |
| **buffer 日志** | 无 (cc2 路径一次成交) | ✅ |
| **30min 错误分类** | all_tiers_exhausted × 5 (502, avg 180s) — 全 hermes | ⚠️ 外部 |
| **三容器 health** | nv_gw / cc4101 / dsv4p 均 ok | ✅ |

## 关键判断: all_tiers_exhausted×5 归属 hermes 周期客户端, 非链路退化

30min 窗口 5 条 `all_tiers_exhausted` (502, avg 180052ms) 经 caller 字段核验 **全部 caller=hermes
(外部客户端, 非 cc4101)**, 呈严格 ~6-7min 周期分布, 每次 ~180s ≈ 5×90s=450s buffer deadline 全额耗尽
— 属 cron 请求特征而非链路退化 (沿用 R853-R860 判定).

per-key nv_tier_attempts: 5 key 均足量 pexec_success (24-25), 瞬态错误
(RemoteDisconnected×10 / 529_nv_overloaded×9 / NVCFPexecTimeout×5 / empty_200×3 / 504_nv_gateway_timeout×1)
被 KeyManager 跨 key round-robin 修复链平滑吸收, 未上抛到 cc2 用户请求. cc2 自身路径 124×200 零错误,
buffer 一次成交, 证明链路/KeyManager 无退化. 不改码.

## 改动
**无 (NOP 巡检轮).** 一致后验: 修复链充分, 不改码.

## 验证
- `curl localhost:4101/health` → ok, primary=dsv4f0731_nv ✅
- `curl localhost:40006/health` → ok, 5 keys, models 含 dsv4f0731_nv 等 ✅
- `curl localhost:40066/health` → ok ✅
- caller 字段核验: 5 条 all_tiers_exhausted 全 caller=hermes, cc4101-primary 0 错误 ✅

## 下一步
- 长期观测. glm5_2_nv 冷却退去后观察 cc4101 primary 是否自动回归 glm5_2_nv (主链路目标).
- hermes 周期 all_tiers_exhausted 属外部客户端 cron, 非 cc2 使命; 持续观察是否影响 NV 成功指标 (当前无影响).
- 不改码. 修复链充分, cc2 近窗全净.