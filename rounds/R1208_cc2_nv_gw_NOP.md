# R1208 cc2 nv_gw NOP — 窗口内唯一 502(7f34c956)全为 R1206 残留, 实际新增失败=0

- 日期: 2026-08-08 (R1207 之后, 07:22 CST 巡检)
- 结论: **NOP**, 不改码。mihomo 升级监控条件仍未实质触发 (无真实新失败)。

## 30min 窗口 (cc2 链路, cc4101-primary, 22:52→23:22 UTC)
- nv_requests: `200|82`, `502|1` (buffer_exhausted) → 表面 SR=98.8% (82/83)
- cc_requests: 84/84 SR=**100%**, **fallback=0%**
- dsv4f0731_nv 全量 (含 hermes 53): SR 稳定 (注入 134/134)
- tier attempt 非成功: k0 RemoteDisconnected×1 + Timeout×1, k1 RemoteDisconnected×2,
  k3 Timeout×1, k4 Timeout×1 — 全数被 attempt-2/3 重试吸收, 无 out-window 失败
- 容器: nv_gw ok (5 keys, dsv4f0731_nv), cc4101 ok (primary=dsv4f0731_nv), dsv4p ok;
  无重配置迹象 (轮前 nv_gw/cc4101 起 27-33h 段)

## 关键判断: 唯一 502 = R1206 残留, 本轮新增失败 = 0
- 本窗口唯一失败 request_id = `7f34c956`, created **23:06:49 UTC** (dur 167010ms),
  与 R1206/R1207 记录逐字一致 = **R1206 新失败残留** (跨 k1-k3 连续 Remote-end-closed),
  非本轮新发生。
- `7562e67f` (R1205 blip 残留, created 22:47) 已随滑窗滑出本窗口, 不再计入 — 印证滚动窗口
  边界 re-sample 的预期行为。
- 比对上轮失败集合 {7562e67f, 7f34c956}: 本窗口 502 集合 = {7f34c956} ⊆ 上轮集合
  ⇒ **新增失败 = ∅**, mihomo 升级监控条件**不触发**。

## 依据 (活查 30min nv_requests + nv_tier_attempts, 07:22 CST)
- 唯一 502 归属: request_id 逐字 JOIN 上轮记录, 确认为 R1206 已计; 滚动窗口边界 re-sample,
  非新增。
- attempt 级瞬时抖动 (k0/k1 RemoteDisconnected, k0/k3/k4 Timeout) 全被重试吸收 → status 200,
  防御链 (buffer upgrade + key fail) 按设计工作。
- fallback 0%: 主链 dsv4f0731_nv 健康, ms_gw fallback 未触发 (无需主动操作)。

## 参数快照 (与 R1206/R1207 一致, 无变更)
- nv_gw: UPSTREAM_TIMEOUT=90, NVU_BUFFER_MAX_RETRIES=5 (90×5=450s), NVU_DISABLE_MS_FALLBACK=0,
  NVU_FORCE_STREAM_UPGRADE=0, KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=180, MIN_OUTBOUND_INTERVAL_S=10,
  NV_INTEGRATE_KEY_COOLDOWN_S=90, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, TIER_TIMEOUT_BUDGET_S=180,
  NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, full-key bind fid index0=281478d0-f307 (dsv4f0731_nv)
- cc4101: PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, CC4101_STREAM_TOTAL_DEADLINE_S=470,
  PRIMARY_HEADER_TIMEOUT=400, PRIMARY_FAIL_THRESHOLD=3, PRIMARY_SKIP_S=30, UPSTREAM_TIMEOUT=130

## 上轮
R1207 (NOP): 表面 2× buffer_exhausted 全为上轮重复, 实际新增=0, 升级监控条件经归属核实未实质触发。
→ R1208: 窗口进一步推进, 7562e67f 滑出, 仅剩 7f34c956 (R1206 残留) 在窗, 新增仍为 0。

## 下一步
- 维持静稳观察。单次自愈 / 上轮残留重计一律 NOP。
- mihomo 隧道检查触发条件 (R1206/R1207 收紧): **R1209 出现真实新失败 (非上轮 request_id) + SR<99%**
  才拉 mihomo 隧道线路质量。当前 7f34c956 随下一滑窗将自然滑出, 预期 R1209 表面 SR 回到 100%。
- 主键: 最大化单位时间 NV 成功数; 存在历史 3h 100% SR 基线, 防御链工作正常。