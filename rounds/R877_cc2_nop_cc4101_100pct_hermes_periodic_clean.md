# R877 — cc2 NOP 巡检轮 (HM2 nv_gw)

- 日期: 2026-08-07 ~06:05 CST (DB UTC)
- 上轮: R876 (NOP, 近窗 114×200 零错误, all_tiers_exhausted 全 hermes)
- 上轮健康: nv_gw Up 2h, cc4101 Up 2h, dsv4p Up 2d, nv_gw_stable Up 5d 对照
- 判定: **NOP 巡检轮 — 只记数据不改码**

## 结论 (一句话)

cc2 自身路径 30min **100% (112×200) 零错误**, 残留 all_tiers_exhausted×5 经 DB 独立核验全部 caller=hermes 外部 cron, 不改码.

## 本轮数据 (轮前链路分析注入 + 独立 DB 复核)

**最近 30min cc4101-primary (cc2 路径) SR = 100% (112×200, 零错误)**

| 指标 | 值 | 状态 |
|---|---|---|
| **最近 30min cc4101-primary SR** | **100% (112×200)** | ✅ |
| **primary 目标 tier** | **dsv4f0731_nv** (自适应轮转持有, cc4101 /health 确认) | ✅ |
| **30min 按模型 SR** | dsv4f0731_nv = 94.9% (111/117, 注入快照); DB 复核 cc4101-primary 112×200 | 与 cc2 路径 100% 一致 (差值=hermes) |
| **error 归属** | all_tiers_exhausted×5 全为 caller=hermes (外部 cron), DB 独立 caller 核验 | ✅ 与 cc2 无关 |
| **非 200 归属** | 仅 `hermes/502/all_tiers_exhausted×5` (DB 独立复核 nv_requests caller), cc4101-primary 0 错误 | ✅ |
| **fallback** | 0 触发 (117 请求) | ✅ |
| **buffer/wait** | 30min nv_gw 日志无 BUFFER-/WAIT- 输出 (无 multi-attempt 退化) | ✅ |
| **per-key nv_tier_attempts** | dsv4f0731_nv 5key 均 22-23 次主 fid 281478d0 + 次 fid 52e1ddb6 5-7 次 (双 fid 现象), 瞬态错误被跨 key 吸收 | ✅ |
| **三容器 health** | nv_gw / cc4101 / dsv4p 均 ok, primary=dsv4f0731_nv, 5 keys | ✅ |

## 关键判断: cc2 路径全净, hermes 周期 all_tiers_exhausted 非本链路问题

30min 链路总览: cc4101-primary **112×200 零错误**; 非 200 (502) 经 **DB 独立 caller 核验全部
caller=hermes** (外部客户端, 非 cc4101): all_tiers_exhausted×5. avg ~180s ≈ buffer deadline
特征 → hermes 严格 ~6min 周期 cron 请求, 沿用 R853-R876 一致判定: 外部客户端周期性全键耗尽/超时,
非本链路退化. 不改码, 不加探针.

peery-key 观察: dsv4f0731_nv 每 key 主 fid 281478d0 (22-23 次) + 次 fid 52e1ddb6 (4-7 次) 双 fid
吸收瞬态, 无单 fid 单点故障; cc2 自身 112×200 零错误, fallback 0%, 无 buffer/wait 退化.
不改码.

## 修复链 (沿用, R827+R828+R829+R833+R813)
1. glm5_2_nv 全 key 疲劳 → R829/R833 fail-fast + cc4101 动态 primary → dsv4f0731_nv
2. dsv4f0731_nv 一次成功, 用户无感知
3. 多 tier round-robin (dsv4p/dsv4f/glm5_2_nv) 自适应吸收底层跨 key 瞬态失败 (双 fid 现象)

## 下一步
- 长期观测。glm5_2_nv 冷却退去后观察 cc4101 primary 是否自动回归 glm5_2_nv (主链路目标)。
- hermes 周期 all_tiers_exhausted 属外部客户端 cron (严格 ~6min/450s buffer 全额耗尽, 非 cc2 使命); 持续观察是否影响 NV 成功指标 (当前无影响)。
- 不改码。cc2 近窗全净 (dsv4f0731_nv primary 维持 100% 则持续 NOP; 待 cc2 路径 SR 掉 <99% 或 buffer 退化 (>1 attempt) 再动手)。