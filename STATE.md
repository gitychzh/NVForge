# STATE.md — cc2 自优化 nv_gw 链路 (HM2)

> 当前轮: **R1207 (NOP — 滚动窗口边界归零: 表面 2× buffer_exhausted (SR 97.4%)
> 经归属核实全为上轮已计重复 (7562e67f=R1205 blip 残留, 7f34c956=R1206 新失败残留),
> R1207 实际新增失败 = 0; 其他 attempt 级瞬时抖动能自愈, 防御链工作 → NOP 不改码)**
> 主链 fid: **281478d0-f307** 稳定, dsv4f0731_nv 单模式
> 错误分类 (活查 35min): cc2-primary buffer_exhausted ×2 (7562e67f + 7f34c956, 均上轮残留)
> 根因: 无新根因; 残余来自 R1205 全-key SSL egress blip + R1206 跨 k1-k3 连续 Remote-end-closed
> 最新窗口: 30min cc2-primary 200|74, dsv4f0731_nv 全量 119/119 SR 100%
> fallback: **0%**

## 本轮 (R1207) 改动 + 依据 + 验证

### 改动: 无 (NOP 巡检轮。R1206「升级监控」条件经归属核实未实质触发, 不改码不查 mihomo)

### 依据 (活查 35min nv_requests + nv_tier_attempts, 2026-08-08 07:18 CST)

- **30min cc2-primary (nv_requests)**: `200|74`, `502|2` (buffer_exhausted),
  表面 SR=97.4%。fallback 触发率 ~0%。dsv4f0731_nv 全量 SR=100% (119/119 含 hermes)。
- **2× buffer_exhausted 归属 (滚动窗口 re-sample, 无一新增)**:
  - `7562e67f`(22:45:43 UTC, dur 79860) = **R1205 blip 重复计入** (22:43-22:47 全-key blip)
  - `7f34c956`(23:04:02 UTC, dur 167010) = **R1206 本轮新失败重复计入** (R1206 已完整分析
    k1/k2/k3 连续 Remote-end-closed)。二者 request_id 与上轮记录逐字一致, 均非本轮新发生。
- **attempt 级瞬时抖动全自愈**: 22:32:57 k3 RemoteDisconnected、22:42:22 k0 Timeout、
  22:54:48 k1 RemoteDisconnected、22:55:49 k4 Timeout、23:04:49 k3 Timeout、23:15:54 k0 Timeout
  等单 attempt 失败均被 attempt-2/3 重试吸收 → status 最终 200, 无 out-window 失败。
- **R1206 升级条件判定关键的校正**: 表面 SR<99% + buffer_exhausted 看似触发"查 mihomo",
  但归属核实证明 2× 502 全为上轮残留、本轮新增=0 → 不满足"仍见此类分散错误"实质条件,
  mihomo 隧道检查延后; 触发条件收紧为"R1208 出现真实新失败 + SR<99%"。
- **容器健康**: nv_gw /health ok (5 keys + dsv4f0731_nv, fid 281478d0-f307) ok,
  cc4101 ok (primary=dsv4f0731_nv), dsv4p_nv40066 ok。nv_gw 28h / cc4101 27h 无漂移,
  参数与 R1206 一致 → 非配置回归。

### 验证
表面 2× buffer_exhausted 经 request_id 逐字 JOIN 全为上轮已计 (R1205 blip + R1206 新失败),
本轮实际新增失败 = 0; 同信号 attempt 级失败全数自愈; dsv4f0731_nv 全量 SR 100%; 容器 health
ok、参数无漂移 → 无改码条件, 升级监控条件未实质触发。fallback 0%。

## 参数快照 (nv_gw + cc4101, 与 R1206 一致)

- **nv_gw**: UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, NVU_BUFFER_MAX_RETRIES=5
  (stairs 90×5=450s), NVU_DISABLE_MS_FALLBACK=0, NVU_FORCE_STREAM_UPGRADE=0,
  KEY_COOLDOWN_S=30, INTEGRATE_KEY_COOLDOWN_S=90, TIER_COOLDOWN_S=180, MIN_OUTBOUND_INTERVAL_S=10,
  NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NV_INTEGRATE_KEY_COOLDOWN_S=90,
  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150 (全 key bind fid index 0=281478d0-f307, dsv4f0731_nv 单模式)。
- **cc4101**: PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages,
  FALLBACK_UPSTREAM_MODEL=glm5_2_ms, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, PRIMARY_FAIL_THRESHOLD=3,
  PRIMARY_SKIP_S=30, UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150。

## 上轮
R1206 (NOP — 3× buffer_exhausted SR96.6%, 2=R1205 blip 重复 + 1 新失败 7f34c956 跨 k1-k3 连续 3 次
Remote-end-closed) → R1207: 该 7f34c956 + 7562e67f 随滑窗带进本轮, 无任何新失败。SSLEOFError
瞬时 egress 抖动自 R1205 泛化后未产生净新增, 非配置回归。

## 下一步
维持静稳观察。**核心监控升级触发条件收紧/校正**: R1206 原"R1207 表面 SR<99% + 分散错误查 mihomo"
经本轮归属核实证明表面 SR 不足信 (2× 502 全为上轮残留)。改为以**新增失败 (非上轮 request_id) 为准**:
若 **R1208 出现真实新失败 + SR<99%** → 拉 mihomo 隧道线路质量 (各 egress_ip 失败率、隧道状态、
`mihomo get proxies`), 评估是否调整 key→proxy 绑定。单次瞬时自愈 / 上轮残留重计一律 NOP 自愈。
- 主键: 最大化单位时间 NV 成功数; 存在历史 3h 100% SR 基线, 防御链工作正常。