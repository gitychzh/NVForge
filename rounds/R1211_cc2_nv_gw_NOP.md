# R1211 — cc2 nv_gw NOP 巡检轮 (2026-08-08 07:40 CST)

## 状态: NOP (SR 100%, 无错误, 上轮残留已滑出窗口)

## 改动: 无 (NOP 巡检轮, 不改码)

## 依据 (轮前注入链路分析, 2026-08-08 07:40 CST)

- **30min cc2-primary (nv_requests)**: `200|107`, **无 502/4xx** → SR=**100% (107/107)**。
  上轮 R1210 残留的 `7f34c956` (created 23:06:49 UTC) **已滑出 30min 滚动窗口**,
  表面 SR 按 R1208-R1211 连续多轮预测成功回到 100%。
- **30min 错误分类**: 空 (无 buffer_exhausted / stream_total_deadline / 其他)。
- **dsv4f0731_nv 全量 (含 hermes 68)**: 175/175 SR=**100%**。
- **fallback**: 0% (cc_requests 全 175 status=200, 无 fallback_triggered)。
- **per-key tier** (nv_tier_attempts): k0 RemoteDisconnected×1 + k3 NVCFPexecTimeout×1,
  其余全 pexec_success → 均为 attempt 级瞬时抖动, 被重试自愈到 status 200, 非净新增。
- **buffer/wait/keymanager 日志**: 无输出 (防御���本窗口未触发)。

## 验证
- 容器 health: nv_gw /health ok (5 keys + dsv4f0731_nv), cc4101 ok (primary=dsv4f0731_nv),
  dsv4p ok。无重配置迹象。
- 参数与 R1206-R1210 一致 (见 STATE.md 参数快照), 无漂移 → 非配置回归。
- mihomo 升级监控触发条件 (R1206/R1207 收紧) **本轮不满足**: 无真实新失败 + SR=100% ≥ 99%,
  mihomo 隧道检查继续延后。

## 下一步
维持静稳观察。mihomo 升级监控触发条件不变: **若后续轮次出现真实新失败 (非上轮 request_id) + SR<99%**
→ 拉 mihomo 隧道线路质量 (各 egress_ip 失败率、隧道状态、`mihomo get proxies`), 评估调整 key→proxy 绑定。
单次瞬时自愈 / 上轮残留重计一律 NOP 自愈。主键: 最大化单位时间 NV 成功数。