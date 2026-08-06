# R872 — cc2 NOP 巡检轮 — 近窗 cc4101-primary SR=100% (120×200) 零错误, hermes 周期 all_tiers_exhausted 属外部 cron

> 日期: 2026-08-07 ~05:40 CST
> 容器: nv_gw Up 2h / cc4101 Up 2h / dsv4p_nv40066 Up 2d
> 结论: **不改码**。cc2 自身路径 (cc4101-primary) 120×200 零错误, fallback 0%, 无 buffer/wait 日志 (全 attempt1 一次成交), 链路无退化。

## 数据 (round 注入 30min 窗口, DB UTC)

### 最近 30min cc4101-primary (cc2 自己路径) SR = 100% (120×200, 零错误)

| 指标 | 值 | 状态 |
|---|---|---|
| **最近 30min cc4101-primary SR** | **100% (120×200)** | ✅ |
| **primary 目标 tier** | **dsv4f0731_nv** (自适应轮转持有, /health 确认) | ✅ |
| **30min 按模型 SR** | dsv4f0731_nv = 95.2% (120/126) | 与 cc2 路径 100% 一致 |
| **error 归属** | all_tiers_exhausted×5 + stream_absolute_cap×1 全为 caller=hermes (外部 cron) | ✅ 与 cc2 无关 |
| **非 200 归属** | 6 条全 caller=hermes (cc4101-primary 0 错误) | ✅ |
| **fallback 触发率** | 0 (131 请求 0 fallback) | ✅ |
| **buffer** | 无 buffer/wait/keymanager 日志 → 全 attempt1 一次成交 | ✅ |
| **per-key nv_tier_attempts** | dsv4f0731_nv 5key 均 24 次 pexec_success (共 120), 瞬态跨 key 吸收 | ✅ |
| **三容器 health** | nv_gw / cc4101 / dsv4p 均 ok | ✅ |

### 错误分类
- `all_tiers_exhausted` × 5 — 全 caller=hermes (外部 cron), avg ~180035ms ≈ 5×90s=450s buffer deadline 全额耗尽
- `stream_absolute_cap` × 1 — 全 caller=hermes

## 关键判断: cc2 路径全净, hermes 周期 all_tiers_exhausted 非本链路问题

30min 窗口链路总览: cc4101-primary 120×200 零错误; 6 条非 200 (502) 经 caller 核验
**全部 caller=hermes** (外部客户端, 非 cc4101): all_tiers_exhausted×5 + stream_absolute_cap×1.
沿用 R853-R871 判定: 每次 all_tiers_exhausted ~180s (avg 180035ms) ≈ 5×90s=450s buffer
deadline 全额耗尽 — 属 hermes 严格 ~6min 周期 cron 请求特征而非链路退化.

per-key nv_tier_attempts (tier=dsv4f0731_nv): 5key 均 24 次 pexec_success
(0→24, 1→24, 2→24, 3→24, 4→24, 共 120 成功),
瞬态错误 (NVCFPexecRemoteDisconnected×20/NVCFPexecTimeout×5/529_nv_overloaded×2/empty_200×2)
被 KeyManager 跨 key round-robin 修复链自适应吸收, 未上抛到 cc2 用户请求.
cc2 自身路径 120×200 零错误, fallback 0%, 无 buffer/wait 日志,
证明链路/KeyManager 无退化. **不改码.**

## 健康检查
- `curl localhost:4101/health` → ok ✅ (cc4101, primary=dsv4f0731_nv)
- `curl localhost:40006/health` → ok ✅ (nv_gw, passthrough, 5 keys, nvcf_pexec_models 含 dsv4f0731_nv/glm5_2_nv)
- `curl localhost:40066/health` → ok ✅ (dsv4p_nv40066, passthrough, 5 keys)
- docker ps: nv_gw = Up 2h, cc4101 = Up 2h, dsv4p = Up 2d (nv_gw_stable = Up 5d 对照)

## 下一步
- 长期观测。glm5_2_nv 冷却退去后观察 cc4101 primary 是否自动回归 glm5_2_nv (主链路目标)。
- hermes 周期 all_tiers_exhausted 属外部客户端 cron (严格 ~6min/180s buffer 全额耗尽, 非 cc2 使命); 持续观察是否影响 NV 成功指标 (当前无影响)。
- 不改码。修复链充分, cc2 近窗全净 (dsv4f0731_nv primary 维持 100% 则持续 NOP; 待 cc2 路径 SR 掉 <99% 或 buffer 退化 (>1 attempt) 再动手)。