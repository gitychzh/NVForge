# R870 — NOP 巡检轮 (cc2, HM2 nv_gw)

> 轮前链路分析 2026-08-07 05:27:33 CST 注入 → 直接进入决策, 仅助力验证 (health + config drift check)。

## 判定: NOP (SR=100% 零错误, 不改码)

**最近 30min cc4101-primary (cc2 自己路径) SR = 100% (125×200, 零错误).**

| 指标 | 值 | 状态 |
|---|---|---|
| **最近 30min cc4101-primary SR** | **100% (125×200)** | ✅ |
| **primary 目标 tier** | **dsv4f0731_nv** (自适应轮转持有, /health 确认) | ✅ |
| **error 归属** | all_tiers_exhausted×5 + stream_absolute_cap×1 **全为 caller=hermes** (外部 cron) | ✅ 与 cc2 无关 |
| **非 200 归属** | 6 条 502 全 caller=hermes (cc4101-primary 0 错误) | ✅ |
| **per-key tier 分布** | dsv4f0731_nv 5key 均 25 次 pexec_success (0→25,1→25,2→25,3→25,4→25, 共 125) | ✅ |
| **瞬态错误** | RemoteDisconnected×21/Timeout×5/529×3/empty_200×2 被 KeyManager 跨 key 吸收 | ✅ |
| **fallback 触发率** | 0 (131 请求 0 fallback) | ✅ |
| **buffer 效果** | 无 buffer/wait/keymanager 日志 → 全 attempt1 一次成交 | ✅ |
| **三容器 health** | nv_gw / cc4101 / dsv4p 均 ok | ✅ |

## 关键判断: cc2 路径全净, hermes 周期错误非本链路问题

30min 窗口 131 请求链路总览: cc4101-primary 125×200 零错误, 6 条非 200 (502) 全为
caller=hermes (外部客户端, 非 cc4101). 沿用 R853-R869 判定:
- all_tiers_exhausted×5 (avg 180034ms ≈ 5×90s=450s buffer deadline 全额耗尽) — hermes 严格 ~6min 周期 cron 特征
- stream_absolute_cap×1 — hermes 外部 cron 大请求特征
- 全与 cc2 使命无关

per-key nv_tier_attempts (tier=dsv4f0731_nv): 5key 均 25 次 pexec_success (共 125).
瞬态错误 (NVCFPexecRemoteDisconnected×21 / NVCFPexecTimeout×5 / 529_nv_overloaded×3 /
empty_200×2) 被 KeyManager 跨 key round-robin 修复链平滑吸收, 未上抛.
cc2 自身路径 125×200 零错误, fallback 0%, 无 buffer/wait 日志,
证明链路/KeyManager 无退化. **不改码.**

## 改动
无 (巡检轮).

## 验证
- `curl 40006/health` ok, passthrough 5keys, models 含 kimi/dsv4p/dsv4f/dsv4f0731/glm5_2
- `curl 4101/health` ok, primary=dsv4f0731_nv
- `curl 40066/health` ok, passthrough 5keys
- 参数无漂移: nv_gw KEY_MODE_BINDING 空, pexec_us_rr, KEY_FID_BIND 全 bind b1b22d03,
  BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90×5=450s, DISABLE_MS_FALLBACK=0;
  cc4101 primary=dsv4f0731_nv, STREAM_TOTAL=470, FALLBACK=ms_gw:40007 glm5_2_ms
- 容器稳定: nv_gw/cc4101 Up 2h, dsv4p Up 2d, 均无重启

## 下一步
- 长期观测。dsv4f0731_nv primary 维持 100% 则持续 NOP; 若 cc2 路径 SR 掉 <99% 或 buffer 退化 (>1 attempt) 再动手。
- hermes 周期 all_tiers_exhausted (严格 ~6min, 180s buffer 全额耗尽, 外部 cron) 非 cc2 使命, 持续观察不影响 NV 成功指标。
- glm5_2_nv 冷却退去后观察 cc4101 primary 是否自动回归 glm5_2_nv (主链路目标)。