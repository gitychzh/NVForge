# R1135 cc2 NOP 巡检轮 — 2026-08-08

## 结论: NOP (不改码)

30min 主链**零表面错误** (错误分类空), cc2-primary 200|114 = **100% SR**,
全 caller dsv4f0731_nv **138/138 = 100.0%**。tier 非-success 仅 empty_200 1× (k1)
+ NVCFPexecRemoteDisconnected 1× (k2) 共 **2 次**分布式单点 self-heal 未上浮 (与上轮持平)。
fallback 0%, buffer 全 attempt-1 direct flush 无 WAIT/无新 exhaust。cc2 范围无配置回归。

## 依据 (本 session 轮前注入 + 实查 2026-08-08)

- **30min cc2-primary (nv_requests)**: `200|114` = **0 行非-200, 100% SR** — 主链全绿。
- **30min 错误分类 (cc2-primary)**: **空 (0 行)** — 无 surface 错误。
- **30min 全 caller SR**: dsv4f0731_nv `138/138 = 100.0%` (cc4101-primary 113 + hermes 25)。
- **30min nv_tier_attempts 非-success**: empty_200 1× (k1) + NVCFPexecRemoteDisconnected 1× (k2),
  共 2 次, 各 key/time 分散单点 self-heal, 无 multi-key 连续复发, 未上浮 surface。
  与上轮持平 (R1134: 2 次), 维持下沉稳态 (延续 [[ssleof-error-transient-egress-blip]])。
- **buffer 日志 (实查)**: 无 WAIT、无新 exhaust — 全 attempt-1 direct flush
  (verdict=success_tool_call, elapsed 4s~10s, buffered 2.8K~4.8K), 598 条 BUFFER 行全 success 路径。
- **fallback (注入)**: 30min f 138 = **0%** — 未触发 ms_gw。
- **容器 /health (实查)**: nv_gw 200 (passthrough, 5 key, pexec 5 模型),
  cc4101 200 (primary dsv4f0731_nv) — 全链路健康。

## 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| cc2 主链 (40006) 30min | **200|114 = 0 行非-200, 100% SR** | ✅ 零表面错误 |
| cc2 专属错误分类 | 空 (0 行) | ✅ |
| 全 caller SR (30min) | dsv4f0731_nv 138/138 = 100.0% | ✅ |
| fallback 触发率 | 0% (30min f 138, 未走 ms_gw) | ✅ |
| per-key tier 错误 | empty_200 1× (k1) + RD 1× (k2), 共 2 次, 单点分布式 self-heal 未上浮 | ✅ (与上轮持平) |
| buffer | 无 WAIT/无新 exhaust (全 attempt-1 direct flush) | ✅ |
| container /health | nv_gw 200, cc4101 200 | ✅ |

## 下一步
- 延续 NOP。主链滚动 30min 零表面错误、fallback 0%, 无参数可调。
- **观测 RD/empty_200 下沉**: 本轮 tier 非-success 2 次, 与上轮持平, 维持稳态。
  若回升尖峰 (>30 次/30min) 或同 key 多请求连续复发 RD, 再查该 key mihomo 端口线路。
- **ms_gw**: 不可调, fallback 0% 未触发, 无需动作。