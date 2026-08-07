# R1213 — cc2 nv_gw NOP 巡检轮 (2026-08-08 08:00 CST)

## 状态: NOP (SR 100%, 无错误, fallback 0%)

## 改动: 无 (NOP 巡检轮, 不改码)

## 依据 (轮前注入链路分析 + 活查确认, 2026-08-08 CST)

- **30min cc2-primary (nv_requests)**: `200|109`, **无 502/4xx** → SR=**100% (109/109)**
  (活查确认, 注入快照 107 已随窗口滚动至 109)。
- **30min 错误分类 (活查)**: 空 → 无 buffer_exhausted / stream_total_deadline / 其他。
- **dsv4f0731_nv 全量 (含 hermes 65)**: 172/172 SR=**100%**。
- **fallback**: 0% (cc_requests 全 109 status=200, 无 fallback_triggered)。
- **per-key tier** (nv_tier_attempts): k2 NVCFPexecRemoteDisconnected×1 + k3
  NVCFPexecRemoteDisconnected×1, 其余全 pexec_success → 均为 attempt 级瞬时抖动,
  被重试自愈到 status 200, 非净新增 (与 R1212 k0/k3 同签名的链路单点瞬抖)。
- **buffer 日志**: 全部 attempt-1 success (elapsed 1-15s), 防御链单 attempt 即通过,
  未见多 attempt 重试或 WAIT- 阻塞输出。key 从 k2/k3 起转 (BUFFER_OVERRIDE _KEY_ROTATION),
  负载均匀。

## 验证
- 容器 health (活查): nv_gw /health ok (5 keys + kimi/dsv4p/dsv4f/dsv4f0731/glm5_2,
  pexec_models), cc4101 ok (primary=dsv4f0731_nv), ms_gw ok, logs_db ok。参数与 R1212
  快照一致, 无重配置迹象 → 非配置回归。
- mihomo 升级监控触发条件 (R1206/R1207 收紧) **本轮不满足**: 无真实新失败 + SR=100% ≥ 99%,
  mihomo 隧道检查继续延后。触发条件: **后续轮次出现真实新失败 (非上轮 request_id) + SR<99%**。

## 下一步
维持静稳观察。mihomo 升级监控触发条件不变: **若后续轮次出现真实新失败 (非上轮 request_id) + SR<99%**
→ 拉 mihomo 隧道线路质量 (各 egress_ip 失败率、隧道状态、`mihomo get proxies`), 评估调整 key→proxy 绑定。
单次瞬时自愈 / 上轮残留重计一律 NOP 自愈。主键: 最大化单位时间 NV 成功数; 已连续多轮 3h 100% SR 基线,
防御链工作正常。