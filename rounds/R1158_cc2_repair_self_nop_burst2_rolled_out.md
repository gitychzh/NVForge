# R1158 cc2_repair_self NOP — Burst2 彻底滚出, 整窗全 200

状态: NOP (不改码)
时间: 2026-08-08 03:06 CST (≈ 19:06 UTC)
主链: dsv4f0731_nv 经 nv_gw pexec (全 5 key bind fid 281478d0-f307)

## 结论
注入 30min (≈02:34-03:04 CST) cc4101-primary `200|86, 502|2 (buffer_exhausted)`。
**2× = R1157 已闭合 Burst2 (18:34:59 / 18:36:24 UTC) 的窗口 re-sample, 非新事件。**
决定性根证: `non200_since_18_37 = 0` — 自 Burst2 之后 (18:37 UTC 起) 到本轮窗口尾
(19:06 UTC) **零新增非-200**。最新 10min 全 200 SR=100%。→ NOP 不改码。

## 实查证据 (2026-08-08 03:06 CST)

- **注入 30min**: `200|86`, `502|2` (buffer_exhausted, avg_dur 34814ms)。
- **最终非-200 (limit 5)**: `18:34:59 buffer_exhausted`, `18:36:24 buffer_exhausted`,
  `18:02:46/18:01:12/17:58:38 all_tiers_exhausted`(R1148 风暴带, 已滚出)。
  → 2× buffer_exhausted 与 R1157 记录的 Burst2 request_id (3a582e6c/25c3a92b) 同时间戳逐一匹配。
- **决定性**: `SELECT count(*) ... created_at > '2026-08-07 18:37:00+00'` = **0**。
  → Burst2 之后零新非-200, 事件彻底闭合。
- **最新 10min (18:56-19:06 UTC)**: 15/15 全 200, 0 非-200。
- **tier (30min)**: 仅 `pexec_success × 89` + `NVCFPexecTimeout × 1` (单个瞬时, 非新类型), 无 429/empty/新类型。
- **buffer 日志**: 最新 3 req 全 attempt-1 direct flush 成功 (elapsed 6-14s), 无 exhaust、无 WAIT。
- **容器**: nv_gw + cc4101 /health 全 ok, 未重启。

## 改动
无 (NOP 巡检轮)。

## 验证
Live 10min SR=100% (0 非-200); non200_since_18_37=0 决定性根证; buffer attempt-1 全成功;
容器全健康; fallback 未触发 (注入 30min f|145 全 200 直通)。

## 下一步
维持静稳观察。核心监控不变: **是否重现独立瞬时 burst 及复发间隔** (Burst2 后已跨 30+ min 无新发)。
下个窗口若再现 ≥2× buffer_exhausted 且 request_id 全新 (非 3a582e6c/25c3a92b) 则为独立新事件,
按记忆 `ssleof-error-transient-egress-blip` 深挖 mihomo dsv4f0731_nv egress 线路, 评估超 5 key
超大请求 buffer 首跳韧性。当前仍判定瞬时 egress 抖动非配置漂移, NOP。

## 参数快照 (本轮无变更)
- nv_gw: UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, NVU_BUFFER_MAX_RETRIES=5 (90×5=450s),
  NVU_DISABLE_MS_FALLBACK=0, NVU_FORCE_STREAM_UPGRADE=0, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv,
  KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=180, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2。
- cc4101: PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv, FALLBACK=glm5_2_ms@ms_gw:40007,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, PRIMARY_FAIL_THRESHOLD=3, PRIMARY_SKIP_S=30。