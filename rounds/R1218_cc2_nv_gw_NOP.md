# R1218 cc2 nv_gw — NOP 巡检轮 (SR 100%, 0 错误, fallback 0%)

> 轮: R1218  |  日期: 2026-08-08  |  容器: nv_gw /health ok (5 keys, dsv4f0731_nv 单模式)
> 主链 fid: 281478d0-f307 稳定, dsv4f0731_nv 单模式 (active 流量)
> 上一轮: R1217 (NOP — SR 100%, 0 错误, fallback 0%)

## 判定: NOP — 无改码条件

## 依据 (轮前注入链路分析 + 活查确认)

- **30min cc2-primary (nv_requests)**: 活查 `200|88`, **无 502/4xx** → SR=**100% (88/88)**。
- **30min 错误分类 (活查)**: 空 (0 rows) → 无 buffer_exhausted / stream_total_deadline / 其他。
- **30min nv_requests 全量**: 00|200 (dsv4f0731_nv), hermes 69 → SR=**100% (157/157)**。
- **fallback**: 0/88 = **0%** (live 活查 cc_requests)。
- **per-key tier** (nv_tier_attempts 活查后段, 注入快照含 k2 NVCFPexecRemoteDisconnected×1):
  整窗全 pexec_success (k0 17/k1 19/k2 17/k3 17/k4 18), 全部 bind fid 281478d0-f307 →
  attempt 级瞬时抖动, 被重试自愈到 status 200, 非净新增 (与 R1212-R1217 同签名链路单点瞬抖)。
- **buffer 日志 (活查)**: 连续多请求 attempt=1 即 success_text/success_tool_call
  (如 b166b2e0 10s success_tool_call), 无 WAIT- 阻塞, 无 buffer_exhausted。
  含 1 例 multi-attempt 自愈: req `9a083b67` attempt=1 k4 execute_failed → 5s backoff →
  attempt=2 success_tool_call, flushed 25KB after 2 attempts (35s) → 请求级仍 200, 属
  attempt 级瞬时抖动被 buffer 预算内自愈, 非净新增 (与 k2 RemoteDisconnected 同签名)。
- **mihomo 升级监控条件 (R1206/R1207 收紧) 判定**: 无真实新失败 (请求级 0 错) + SR=100% ≥ 99%
  → 条件不满足, mihomo 隧道检查继续延后。触发条件: **后续轮次出现真实新失败 (非上轮 request_id) + SR<99%**。
- **容器健康 (活查)**: nv_gw /health ok (5 keys + pexec_models 含 dsv4f0731_nv), cc4101 ok,
  ms_gw ok。参数与 R1217 一致 (见参数快照), 无重配置迹象 → 非配置回归。

## 验证
活查 30min cc2-primary 88/88 (0 错误), 全量 157/157 SR 100%、fallback 0%; 容器 health ok、
参数无漂移。k2 RemoteDisconnected / k4 execute_failed 均为 attempt 级瞬时抖动, 被重试自愈到
status 200, 无任何净新增。
→ 无改码条件, NOP。

## 参数快照 (nv_gw + cc4101, 与 R1217 一致)

- **nv_gw**: UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, NVU_BUFFER_MAX_RETRIES=5
  (stairs 90×5=450s), NVU_DISABLE_MS_FALLBACK=0, NVU_FORCE_STREAM_UPGRADE=0,
  KEY_COOLDOWN_S=30, INTEGRATE_KEY_COOLDOWN_S=90, TIER_COOLDOWN_S=180, MIN_OUTBOUND_INTERVAL_S=10,
  NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NV_INTEGRATE_KEY_COOLDOWN_S=90,
  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv (全 key bind fid index 0=281478d0-f307, dsv4f0731_nv 单模式)。
- **cc4101**: PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages,
  FALLBACK_UPSTREAM_MODEL=glm5_2_ms, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, PRIMARY_FAIL_THRESHOLD=3,
  PRIMARY_SKIP_S=30, UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150。

## 上轮
R1217 (NOP — SR 100%, 0 错误, fallback 0%) → R1218: 维持 SR 100%, fallback 0%。
R1206 SSLEOFError/Remote-end-closed 瞬时 egress 抖动统计影响持续闭合。

## 下一步
维持静稳观察。**mihomo 升级监控触发条件 (R1206/R1207 收紧)**: 若 **后续轮次出现真实新失败
(非上轮 request_id) + SR<99%** → 拉 mihomo 隧道线路质量 (各 egress_ip 失败率、隧道状态、
`mihomo get proxies`), 评估是否调整 key→proxy 绑定。单次瞬时自愈 / 上轮残留重计一律 NOP 自愈。
- 主键: 最大化单位时间 NV 成功数; 已回归历史 3h 100% SR 基线, 防御链工作正常。