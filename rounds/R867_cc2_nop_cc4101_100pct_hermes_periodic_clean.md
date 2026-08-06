# R867 — NOP 巡检轮 (cc2, HM2 nv_gw)

> 轮前链路分析 2026-08-07 05:17:33 CST 注入 → 直接进入决策, 仅助力验证 (caller 核验 + 时序 + buffer log)。

## 判定: NOP (SR=100% 零错误, 不改码)

**最近 30min cc4101-primary (cc2 自己路径) SR = 100% (122×200, 零错误).**

| 指标 | 值 | 状态 |
|---|---|---|
| **最近 30min cc4101-primary SR** | **100% (122×200)** | ✅ |
| **error 归属** | all_tiers_exhausted×4 + stream_absolute_cap×1 **全为 caller=hermes** (外部 cron) | ✅ 与 cc2 无关 |
| **primary 目标 tier** | **dsv4f0731_nv** (自适应轮转持有, /health 确认) | ✅ |
| **buffer** | 全 attempt1 一次成交 (8-13s ≪90s, verdict=success_tool_call/text, flushed) | ✅ |
| **三容器 health** | nv_gw / cc4101 / dsv4p 均 ok | ✅ |

## 关键判断: cc2 路径全净, hermes 周期错误非本链路问题

30min 窗口 5 条非 200 (502) 经 caller 字段核验 **全部 caller=hermes** (外部客户端, 非 cc4101),
严格 ~6min 周期 (20:54/21:00/21:06/21:09/21:16 UTC, stream_cap 为 21:09 周期尾), 全 fid=52e1ddb6.
沿用 R853-R866 判定: 每次 all_tiers_exhausted ~180s (avg 180036ms) = 5×90s buffer deadline 全额耗尽,
属 cron 请求特征而非链路退化.
per-key nv_tier_attempts 显示 5 key 均有足量 pexec_success (23-24/24/24/24/23, 共 119):
0→24, 1→24, 2→24, 3→24, 4→23. 瞬态错误 (NVCFPexecRemoteDisconnected×17 / timeouts / 529 / empty_200 / 504)
被 KeyManager 跨 key round-robin 修复链平滑吸收, 未上抛到 cc2 用户请求.
cc2 自身路径 122×200 零错误, buffer 全 attempt1 一次成交 (8-13s),
证明链路/KeyManager 无退化. **不改码.**

## 改动
无 (巡检轮).

## 验证
- `curl 40006/health` ok, passthrough 5keys, models 含 dsv4p/dsv4f/dsv4f0731/glm5_2
- `curl 4101/health` ok, primary=dsv4f0731_nv
- `curl 40066/health` ok, passthrough 5keys
- caller 核验: 5 错误全 caller=hermes, ~6min 周期分布, 全 fid 52e1ddb6
- buffer log: NV-BUFFER-SUCCESS 全 "after 1 attempt(s)" 8-13s, 无 WAIT-/退避

## 下一步
继续监控 hermes cron 周期错误是否为单点 fid 后端 (52e1ddb6) 触发; 若 cc2 路径 SR 掉 <99% 或 buffer 退化 (>1 attempt) 再动手.