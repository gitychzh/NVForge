# STATE.md — cc2 自优化 nv_gw 链路 (HM2)

> 当前轮: **R1157 (NOP — live 10min 31/31=100% SR, 5min 13/13=100%=0 非-200; 注入 30min 含
> 2× 502 buffer_exhausted = 实查 request_id 3a582e6c/25c3a92b 与 R1155/56 已闭合 Burst2
> (18:34/18:36 UTC) 逐一相同 → 窗口边界 re-sample, 非新事件; 18:37 UTC 后整窗干净无第 3 次;
> tier 全 pexec_success fallback 0% → NOP 不改码)**
> 主链 fid: **281478d0-f307** 稳定 (全 5 key pexec), dsv4f0731_nv 单模式
> 错误分类 (surface, 30min): `buffer_exhausted × 2` (= 已闭合 Burst2 的 request_id re-sample, 非新事件)
> 根因: R1148/49 风暴过境后新发 Burst2 (18:34/18:36 UTC, 超 5 key 全败), 已自愈; 18:37 后无第 3 次
> 最新 10min: **cc2-primary 31/31 = 100% SR, 0 非-200**
> fallback: **0%** (30min 1762 全 200 直通, 0 触发)

## 本轮 (R1157) 改动 + 依据 + 验证

### 改动: 无 (NOP 巡检轮。注入 2× buffer_exhausted 实查 request_id 归属 = R1155/56 已闭合 Burst2
### 同批, 非新事件; 当前整窗干净 SR 100% → 不符改码条件)

### 依据 (实查 2026-08-08 03:02 CST)

- **注入 30min cc4101-primary**: `200|91`, `502|2` (buffer_exhausted)。
- **实查 2× request_id 定位 (决定性)**: `3a582e6c` (18:34:58) + `25c3a92b` (18:36:23)
  = 与 R1155/R1156 STATE.md 记录的 **Burst2 逐一相同**。
  → 本轮 2× = 同一次已闭合 burst 的窗口 re-sample, **非新事件**。
- **整窗干净**: 18:37 UTC 后无第 3 次 buffer_exhausted; 注入 30min (≈18:28-18:58 UTC) 恰好框住
  Burst2 尾, 之后全部 200。
- **Live (实查)**: 最新 10min cc4101-primary 31/31=100%; 最新 5min 13/13=100%, 0 非-200。
- **fallback (实查 30min)**: 0% (1762 总请求 0 触发, 全 200 直通)。
- **容器 (实查)**: cc4101 + nv_gw /health 全 ok, 全未重启 (Up 24h/23h, 无漂移)。

### 验证
Live 10min 31/31=100%, 5min 13/13=100%; fallback 0%; 容器全健康。
Burst2 (18:34/18:36) 已滚出活跃窗口, 当前整窗干净。

## 参数快照 (nv_gw + cc4101, 本轮注入无变更)

- **nv_gw**: UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, NVU_BUFFER_MAX_RETRIES=5
  (stairs 90×5=450s), NVU_DISABLE_MS_FALLBACK=0, NVU_FORCE_STREAM_UPGRADE=0,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, KEY_COOLDOWN_S=30, INTEGRATE_KEY_COOLDOWN_S=90,
  TIER_COOLDOWN_S=180, MIN_OUTBOUND_INTERVAL_S=10, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  (全 key bind fid index 0=281478d0-f307, dsv4f0731_nv 单模式)。
- **cc4101**: PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages,
  FALLBACK_UPSTREAM_MODEL=glm5_2_ms, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, PRIMARY_FAIL_THRESHOLD=3,
  PRIMARY_SKIP_S=30, UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150。

## 上轮
R1156 (NOP — 2× = 已闭合 Burst2 re-sample; 18:37 后整窗干净无第 3 次复发)。
R1157 确认: 注入 2× 实查 request_id 与 R1155/56 记录逐一相同 (3a582e6c/25c3a92b), **仍非新事件**,
至本轮窗口仍无第 3 次独立复发。复发间隔窗口已跨 30+ min 无新发。

## 下一步
维持静稳观察。**核心监控: 是否重现独立瞬时 burst 及复发间隔**。
复发链参考: R1148/49 storm (17:47-18:02) → Burst2 (18:34/18:36, 间隔 ~32min)。
若下个窗口再现 ≥2× buffer_exhausted 且 request_id 全新 (非 3a582e6c/25c3a92b), 则为**独立新事件**,
按记忆 `ssleof-error-transient-egress-blip` 深挖 mihomo dsv4f0731_nv egress 线路 (7900-7904),
评估超 5 key 超大请求 (>70K chars) buffer 首跳韧性。当前仍判定瞬时 egress 抖动非配置漂移, NOP。