# R875 (cc2) — NOP 巡检轮: cc4101-primary SR=100% (114×200) 零错误, hermes 周期 all_tiers_exhausted×6 属外部 cron

> 轮次: cc2 第 R875 轮 (2026-08-07 ~05:50 CST, DB UTC)
> 结论: **NOP 巡检轮, 只记数据不改码。**

## 本轮改动
无 (巡检轮 — cc2 路径全净 114×200, hermes 周期 all_tiers_exhausted 与 cc2 无关, 修复链充分)

## 数据 (轮前链路分析注入 + DB 独立复核)

**最近 30min cc4101-primary (cc2 自己路径) SR = 100% (114×200, DB 独立核验零错误).**

| 指标 | 值 | 状态 |
|---|---|---|
| **最近 30min cc4101-primary SR** | **100% (114×200)** | ✅ |
| **primary 目标 tier** | **dsv4f0731_nv** (自适应轮转持有, /health 确认) | ✅ |
| **30min 按模型 SR** | dsv4f0731_nv = 95.0% (115/121, 注入快照); DB 复核 cc4101-primary 114×200 | 与 cc2 路径 100% 一致 |
| **error 归属** | all_tiers_exhausted×6 全为 caller=hermes (外部 cron, 非 cc4101), DB 独立复核 | ✅ 与 cc2 无关 |
| **非 200 归属** | 仅 `hermes/502/6` (DB 独立复核), cc4101-primary 0 错误 | ✅ |
| **fallback 触发率** | 0 (121 请求 0 fallback) | ✅ |
| **buffer** | 114/114 全部 attempt=1 一次成交 (NV-BUFFER-SUCCESS "after 1 attempt") | ✅ 无退化 |
| **per-key nv_tier_attempts** | dsv4f0731_nv 5key 均 23 次 pexec_success (共 ~115 成功), 瞬态错误被跨 key 吸收 | ✅ |
| **三容器 health** | nv_gw Up 2h / cc4101 Up 2h / dsv4p Up 2d, primary=dsv4f0731_nv | ✅ |

### 关键判断: cc2 路径全净, hermes 周期 all_tiers_exhausted 非本链路问题

30min 窗口链路总览: cc4101-primary **114×200 零错误**; 非 200 (502) 经 **DB 独立 caller 核验**
**全部 caller=hermes** (外部客户端, 非 cc4101): all_tiers_exhausted×6.
每次 all_tiers_exhausted avg ~180s ≈ buffer deadline 特征 — 属 hermes 严格 ~6min 周期 cron 请求,
沿用 R853-R875 判定: 外部客户端周期性全键耗尽/超时, 而非本链路退化.

buffer 全 114/114 attempt=1 一次成交, 无 multi-attempt 退化, 证明 KeyManager/跨 key
round-robin 修复链健康. cc2 自身路径 114×200 零错误, fallback 0%, 不改码.

## 修复链 (沿用, R827+R828+R829+R833+R813)
1. glm5_2_nv 全 key 疲劳 → R829/R833 fail-fast + cc4101 动态 primary → dsv4f0731_nv
2. dsv4f0731_nv 1-14s 一次成功, 用户无感知
3. 多 tier round-robin (dsv4p/dsv4f/glm5_2_nv) 自适应吸收底层跨 key 瞬态失败

## 健康检查
- `curl localhost:4101/health` → ok ✅ (cc4101, primary=dsv4f0731_nv)
- `curl localhost:40006/health` → ok ✅ (nv_gw, passthrough, 5 keys, models 含 dsv4f0731_nv)
- `curl localhost:40066/health` → ok ✅ (dsv4p_nv40066)
- docker ps: nv_gw = Up 2h, cc4101 = Up 2h, dsv4p = Up 2d (nv_gw_stable = Up 5d 对照)

## 参数快照 (无变化)
见 STATE.md R875 参数快照 (与此前轮次一致, primary 动态轮转=dsv4f0731_nv)

## 下一步
- 长期观测。glm5_2_nv 冷却退去后观察 cc4101 primary 是否自动回归 glm5_2_nv (主链路目标)。
- hermes 周期 all_tiers_exhausted 属外部客户端 cron (非 cc2 使命); 持续观察是否影响 NV 成功指标 (当前无影响)。
- 不改码。修复链充分, cc2 近窗全净 (dsv4f0731_nv primary 维持 100% 则持续 NOP; 待 cc2 路径 SR 掉 <99% 或 buffer 退化 (>1 attempt) 再动手)。