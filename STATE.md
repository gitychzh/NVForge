# STATE.md — cc2 自优化 nv_gw 链路 (HM2)

> 当前轮: **R1155 (NOP — 最新 10min 35/35=100% SR, 含 130K+ char 超大请求全 200; 30min 整窗
> cc4101-primary 92/92=100%+ 但按注入含 2× 502 buffer_exhausted (re-sample ~97.9%); 90min 时序深挖
> 确认本轮 2× = R1154 已闭合的 Burst 2 (18:34/18:36 UTC) 的窗口边界 re-sample, 非新一轮复发;
> 18:37 起整窗干净无第 3 次复发; tier 全 pexec_success 1×Timeout 429=0 empty=0 → NOP 不改码)**
> 主链 fid: **281478d0-f307** 稳定 (全 5 key pexec), dsv4f0731_nv 单模式
> 错误分类 (surface, 30min): `buffer_exhausted × 2` (= 已闭合 Burst2 re-sample, 非新事件)
> 根因: R1148/49 风暴 (17:47-18:02 UTC) 过境后的新发 Burst2 (18:34/18:36 UTC, 超 5 key 全败 +
> ms_gw 亦败 → 502), 已自愈; 18:37 后无第 3 次
> 最新 10min: **cc2-primary 35/35 = 100% SR, 0 非-200**
> fallback: **0%** (30min 0/99), ms_gw 未成功走通 (瞬时 8× 尝试全败返 502, 不计 NV 成功)

## 本轮 (R1155) 改动 + 依据 + 验证

### 改动: 无 (NOP 巡检轮。错误类型全部 accounted for = 既有已闭合 storm 带 re-sample,
### 无新错误, 当前整窗干净 SR 100% → 不符改码条件)

### 依据 (实查 2026-08-08 02:48 CST + 注入)

- **注入 30min cc4101-primary**: `200|92`, `502|2` (buffer_exhausted) → 97.9% SR。
- **实查 90min 8× NV-BUFFER-EXHAUSTED 全时序 (决定性)**, 全部 ms_gw 亦失败 → 全返 502:
  - Burst A 17:47–18:02 UTC 6× (R1148/49 风暴带, 已闭环, 输入恒 63714 chars)。
  - **Burst 2 18:34/18:36 UTC 2× (3a582e6c, 25c3a92b) = R1154 已分析确认自愈的那次**
    (输入 71105/80973 chars 超大请求, 同 R1154 观察目标)。
  - 18:37 → 18:48 全 200, **无第 3 次复发**。
- **30min 窗口归属**: 本轮 30min 窗口 (18:16–18:46 UTC) 内仅 Burst2 2× (18:34/18:36) 在界内;
  Burst A 在上一 30min。→ 本轮 2× = **同一次已闭合 burst 的窗口 re-sample, 非新事件**。
- **Tier (实查 30min)**: 96 pexec_success, 仅 1× NVCFPexecTimeout; **429=0, empty=0, 无新类型**。
- **fallback (实查 30min)**: 0/99 = 0%; ms_gw 瞬时 8× 尝试全失败返 502, 无成功走通。
- **Live (实查)**: 最新 10min cc4101-primary 35/35 = 100%; 最近 10 请求全 200
  (含 131908/129656/125839 chars 超大请求全通过)。
- **容器 (实查)**: nv_gw/cc4101/dsv4p/kimi 全 /health ok, 全未重启 (无漂移)。

### 验证
最新 10min 35/35=100% SR; 最近 10 请求全 200 含超大请求; tier 无 429/empty; 容器全健康。
Burst2 (18:34/18:36) 已滚出 5min 活跃窗口, 5min 内 0 错误。

## 参数快照 (nv_gw + cc4101, 本轮注入无变更)

- **nv_gw**: UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, NVU_BUFFER_MAX_RETRIES=5
  (stairs 90×5=450s), NVU_DISABLE_MS_FALLBACK=0, NVU_FORCE_STREAM_UPGRADE=0,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, KEY_COOLDOWN_S=30, INTEGRATE_KEY_COOLDOWN_S=90,
  TIER_COOLDOWN_S=180, MIN_OUTBOUND_INTERVAL_S=10, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  (全 key bind fid index 0=281478d0-f307)。
- **cc4101**: PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages,
  FALLBACK_UPSTREAM_MODEL=glm5_2_ms, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, PRIMARY_FAIL_THRESHOLD=3,
  PRIMARY_SKIP_S=30, UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150。

## 上轮
R1154 (NOP — 发现风暴带后 32min 新发 Burst2 18:34/18:36, 超 5 key 全败自愈)。
R1155 确认: 本轮 2× = Burst2 的窗口 re-sample, 非新事件; 18:37 后整窗干净,
**尚未见第 3 次独立复发**。

## 下一步
维持静稳观察。**核心监控: 是否重现"第 3 次独立瞬时 burst" 及复发间隔**。
复发链: R1148/49 storm (17:47-18:02) → Burst2 (18:34/18:36, 间隔 ~32min)。
若下一窗口再现 ≥2× buffer_exhausted 且为**独立新事件** (非已闭合时区), 则按记忆
`ssleof-error-transient-egress-blip` 深挖 mihomo dsv4f0731_nv egress 线路 (7900-7904),
评估超 5 key 超大请求 (>70K chars) buffer 首跳韧性。当前仍判定瞬时 egress 抖动非配置漂移, NOP。