# R1210 cc2 nv_gw NOP — 窗口唯一 502(7f34c956) 27min 终滑出倒计时, 新增失败=0

- 日期: 2026-08-08 (R1209 之后, 07:35 CST 巡检)
- 结论: **NOP**, 不改码。mihomo 升级监控条件仍不触发 (无真实新失败, 唯一 502 仍为上轮残留)。

## 30min 窗口 (cc2 链路, cc4101-primary, 07:05→07:35 CST = 23:05→23:35 UTC)
- nv_requests: `cc4101-primary|dsv4f0731_nv|200|92`, `|502|1` (buffer_exhausted, dur 167010)
  → 表面 SR=98.9% (92/93), 但唯一 502 为上轮残留 (见下)
- cc_requests: 95 total, **fallback=0**
- dsv4f0731_nv 全量 (含 hermes 58): 150/150 SR=**100%**
- tier attempt 非成功 (全被 attempt-2/3 重试吸收, 最终 status 200):
  k0 RemoteDisconnected×1+Timeout×1, k1 RemoteDisconnected×1, k3 RemoteDisconnected×1+Timeout×1
  (k2/k4 全 pexec_success)
- 容器: nv_gw ok (5 keys, dsv4f0731_nv), cc4101 ok (primary=dsv4f0731_nv), dsv4p ok。
  无重配置迹象, 与 R1206-R1209 一致。

## 关键判断: 唯一 502 = R1206 残留 (27min 龄, 即将滑出), 本轮新增失败 = 0
- 活查确认唯一失败 request_id = `7f34c956`, created **23:06:49 UTC** (age≈27min, now=23:33:45 UTC),
  与 R1206/R1208/R1209 记录逐字一致 (dur 167010 相同) = **同一 R1206 残留** 仍在滚动窗口内 re-sample。
- created 字段从未前进 (自 R1206 起一直是 23:06:49 UTC): 它就是那一条失败, 时间戳固定,
  → 本窗口 502 = 同一条在**窗口边界 re-sample**, 非新一轮发生。
- 比对上轮失败集合 {7f34c956}: 本窗口 502 集合 = {7f34c956} ⊆ 上轮集合
  ⇒ **新增失败 = ∅**, mihomo 升级监控条件**不触发**。
- 该残留 age≈27min, **~3min 后自然滑出 30min 窗口** → R1211 表面 SR 预计回到 100%
  (与 R1208/R1209 连续三轮的预测一致)。

## 依据 (活查 30min nv_requests 归属, 07:35 CST)
- 唯一 502 归属: request_id 逐字 JOIN 上轮记录, 确认为 R1206 已计残留; 滚动窗口 re-sample
  而非新增。
- attempt 级瞬时抖动 (k0/k1/k3 RemoteDisconnected, k0/k3 Timeout) 全被 buffer 重试吸收 →
  status 200, 防御链按设计工作。
- fallback 0%: 主链 dsv4f0731_nv 健康 (150/150 SR 100%), ms_gw fallback 未触发。
- 容器 health ok、参数无漂移 → 非配置回归。

## 参数快照 (与 R1206-R1209 一致, 无变更)
- nv_gw: UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, NVU_BUFFER_MAX_RETRIES=5 (90×5=450s),
  NVU_DISABLE_MS_FALLBACK=0, NVU_FORCE_STREAM_UPGRADE=0, KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=180,
  MIN_OUTBOUND_INTERVAL_S=10, NV_INTEGRATE_KEY_COOLDOWN_S=90, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150,
  NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, full-key (0:0;1:0;2:0;3:0;4:0) bind fid
  index0=281478d0-f307 (dsv4f0731_nv)
- cc4101: PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages,
  FALLBACK_UPSTREAM_MODEL=glm5_2_ms, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, PRIMARY_FAIL_THRESHOLD=3,
  PRIMARY_SKIP_S=30, UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150。

## 上轮
R1209 (NOP): 窗口唯一 502(7f34c956) 仍为 R1206 残留 (aged ~20.4min), 新增=0, 防御链按设计工作。
→ R1210: 7f34c956 仍为同一 R1206 残留 (aged ~27min, created 23:06:49 UTC 不变), 新增=0;
  无配置漂移, 全量 dsv4f0731_nv 150/150 SR 100%, fallback 0%。容器 uptime 稳定。

## 下一步
- 维持静稳观察。单次自愈 / 上轮残留重计一律 NOP。
- **预判 R1211**: 7f34c956 (age 27min) ~3min 后滑出窗口, R1211 表面 SR 应回到 100%。