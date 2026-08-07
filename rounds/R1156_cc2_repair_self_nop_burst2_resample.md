# R1156 cc2 NOP — 当前整窗干净 100% SR, 注入 2× buffer_exhausted = 已闭合 Burst2 窗口 re-sample 非新事件

日期: 2026-08-08 03:05 CST (18:05 UTC)
上轮: R1155
容器: nv_gw 21h+ / cc4101 23h+, 全健康未重启 (无漂移)

## 结论: NOP 巡检轮, 不改码

**注入 30min 的 2× buffer_exhausted = R1154/55 已确认自愈的 Burst2 (18:34/18:36 UTC) 的同一批请求
在窗口边界 re-sample, 非新一轮独立复发。18:37 UTC 起整窗干净, 无第 3 次复发。**

## 依据 (实查 2026-08-08 03:00 CST)

- **决定性 — 注入 2× 的 request_id 定位** (nv_requests, 30min, cc4101-primary non-200):
  ```
  3a582e6c | 71105 chars | 18:34:27 | 502 | buffer_exhausted
  25c3a92b | 80973 chars | 18:35:45 | 502 | buffer_exhausted
  ```
  这两个 request_id 与 R1154/R1155 STATE.md 记录的 **Burst2 (3a582e6c, 25c3a92b)** 完全相同。
  → 本轮 2× = 同一次已闭合 burst 的窗口 re-sample, **非新事件**。
- **整窗干净**: 18:37 UTC 后无第 3 次 buffer_exhausted; 注入 90min 内 8× EXHAUSTED 全部 accounted for
  (Burst A 17:47-18:02 6× + Burst2 2×)。
- **Live (实查)**: 最新 10min cc4101-primary **29/29 = 100% SR**; 最新 5min **13/13 = 100% SR, 0 非-200**。
- **Tier (实查 20min)**: 全 pexec_success (k0=10, k1=12, k2=12, k3=13, k4=9), 仅 1× NVCFPexecTimeout
  = 瞬时 egress 抖动 (记忆 `ssleof-error-transient-egress-blip`), **429=0, empty=0, 无新类型**。
- **fallback (注入)**: 未触发 (f|171), 全 200 直通。
- **容器 (实查)**: cc4101 + nv_gw /health 全 ok。

## 验证
Live 10min 29/29=100%, 5min 13/13=100%; tier 无 429/empty; 容器全健康。
Burst2 (18:34/18:36) 已滚出活跃窗口, 当前干净。

## 参数快照 (无变更)

- **nv_gw**: UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, NVU_BUFFER_MAX_RETRIES=5
  (stairs 90×5=450s), NVU_DISABLE_MS_FALLBACK=0, NVU_FORCE_STREAM_UPGRADE=0,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, KEY_COOLDOWN_S=30, INTEGRATE_KEY_COOLDOWN_S=90,
  TIER_COOLDOWN_S=180, MIN_OUTBOUND_INTERVAL_S=10, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  (全 key bind fid index 0=281478d0-f307, dsv4f0731_nv 单模式)。
- **cc4101**: PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages,
  FALLBACK_UPSTREAM_MODEL=glm5_2_ms, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, PRIMARY_FAIL_THRESHOLD=3,
  PRIMARY_SKIP_S=30, UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150。

## 下一步
维持静稳观察。**核心监控不变: 是否重现独立瞬时 burst 及复发间隔**。
复发链参考: R1148/49 storm (17:47-18:02) → Burst2 (18:34/18:36, 间隔 ~32min)。
若下个窗口再现 ≥2× buffer_exhausted 且为**独立新事件** (request_id 全新, 非 3a582e6c/25c3a92b),
则按记忆 `ssleof-error-transient-egress-blip` 深挖 mihomo dsv4f0731_nv egress 线路。