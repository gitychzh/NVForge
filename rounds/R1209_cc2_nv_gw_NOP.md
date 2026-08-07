# R1209 cc2 nv_gw NOP — 窗口唯一 502(7f34c956)仍为 R1206 残留 re-sample, 实际新增失败=0

- 日期: 2026-08-08 (R1208 之后, 07:26 CST 巡检)
- 结论: **NOP**, 不改码。mihomo 升级监控条件仍未实质触发 (无真实新失败)。

## 30min 窗口 (cc2 链路, cc4101-primary, 06:56→07:26 CST = 22:56→23:26 UTC)
- nv_requests: `cc4101-primary|dsv4f0731_nv|200|78`, `|502|1` (buffer_exhausted, dur 167010)
  → 表面 SR=98.7% (78/79), 但唯一 502 为上轮残留 (见下)
- cc_requests: 138 total, **fallback=0** (`f|138`)
- dsv4f0731_nv 全量 (含 hermes 59): 137/137 SR=**100%**
- tier attempt 非成功 (全被 attempt-2/3 重试吸收, 最终 status 200):
  k0 RemoteDisconnected×1+Timeout×1, k1 RemoteDisconnected×1, k3 RemoteDisconnected×1+Timeout×1,
  k4 Timeout×1 (k2 全 pexec_success)
- 容器: nv_gw ok (5 keys, dsv4f0731_nv, nv_default=glm5_2_nv 但 active 流量走 dsv4f0731_nv),
  cc4101 ok (primary=dsv4f0731_nv), dsv4p ok。无重配置迹象。

## 关键判断: 唯一 502 = R1206 残留 (仍在滚动窗口内), 本轮新增失败 = 0
- 活查确认唯一失败 request_id = `7f34c956`, created **23:06:49 UTC** (aged ~20.4min),
  与 R1206/R1207/R1208 记录逐字一致 = **R1206 新失败残留** (跨 k1-k3 连续 Remote-end-closed)。
- 该 request_id 距上轮 (07:22) 起 ~4min 后又落入本轮 30min 窗口, 纯为**滚动窗口边界
  re-sample**, 非新一轮失败: 它自 created 时刻起就是同一条记录, 时间戳从未前进。
- 比对上轮失败集合 {7f34c956} (7562e67f 已在 R1208 滑出): 本窗口 502 集合 = {7f34c956} ⊆ 上轮集合
  ⇒ **新增失败 = ∅**, mihomo 升级监控条件**不触发**。

## 依据 (活查 30min nv_requests 归属, 07:26 CST)
- 唯一 502 归属: request_id 逐字 JOIN 上轮记录, 确认为 R1206 已计残留; 滚动窗口 re-sample
  而非新增。age≈20.4min, 下轮 (~10min 后) 将自然滑出。
- attempt 级瞬时抖动 (k0/k1/k3 RemoteDisconnected, k0/k3/k4 Timeout) 全被 buffer 重试吸收 →
  status 200, 防御链按设计工作。
- fallback 0%: 主链 dsv4f0731_nv 健康, ms_gw fallback 未触发 (无需主动操作)。
- 容器 health ok、参数无漂移 (与 R1206-R1208 一致) → 非配置回归。

## 参数快照 (与 R1206-R1208 一致, 无变更)
- nv_gw: UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, NVU_BUFFER_MAX_RETRIES=5 (90×5=450s),
  NVU_DISABLE_MS_FALLBACK=0, NVU_FORCE_STREAM_UPGRADE=0, KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=180,
  MIN_OUTBOUND_INTERVAL_S=10, NV_INTEGRATE_KEY_COOLDOWN_S=90, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150,
  NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, full-key bind fid index0=281478d0-f307 (dsv4f0731_nv)
- cc4101: PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages,
  FALLBACK_UPSTREAM_MODEL=glm5_2_ms, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, PRIMARY_FAIL_THRESHOLD=3,
  PRIMARY_SKIP_S=30, UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150。

## 上轮
R1208 (NOP): 窗口唯一 502(7f34c956)=R1206 残留, 7562e67f 已滑出, 新增=0, 防御链按设计工作。
→ R1209: 7f34c956 仍在滚动窗口内 (aged ~20.4min, created 23:06:49 UTC), 仍为同一残留 re-sample,
  新增=0; 无配置漂移。容器 uptime 28h-33h-6d 段稳定。

## 下一步
- 维持静稳观察。单次自愈 / 上轮残留重计一律 NOP。
- **7f34c956 预期 ~10min 后滑出本轮 30min 窗口** → R1210 表面 SR 预计回到 100% (与 R1208 预测一致,
  只是该预测顺延一窗, 因 created 23:06:49 距 R1209 窗口边界仍 <30min)。
- mihomo 隧道检查触发条件 (R1206/R1207 收紧): **R1210 出现真实新失败 (非上轮 request_id) + SR<99%**
  才拉 mihomo 隧道线路质量 (各 egress_ip 失败率、隧道状态、`mihomo get proxies`)。
- 主键: 最大化单位时间 NV 成功数; 存在历史 3h 100% SR 基线, 防御链工作正常。