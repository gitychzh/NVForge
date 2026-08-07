# STATE.md — cc2 自优化 nv_gw 链路 (HM2)

> 当前轮: **R1154 (NOP — 最新 5min 100% SR 12/12; 30min 整窗 cc4101-primary 93/95=97.9% SR 含
> 2× 502 buffer_exhausted; 60min 深挖确认那 2× 502 = 风暴带 (17:47-18:02, R1148/49 已闭环) 后
> 32min 出现的新发第 2 burst (18:34/18:36 UTC), 超 5 key 全 execute_failed 自愈; 当前整窗干净,
> 超大请求 (>70K chars) egress 瞬时抖动 → NOP 不改码)**
> 主链 fid: **281478d0-f307** 稳定 (全 5 key pexec), dsv4f0731_nv 单模式
> 错误分类 (surface, 30min): `buffer_exhausted × 2` (瞬时, 已滚出处 5min 窗口)
> 根因: R1148/49 风暴过境后的同源 egress 涟漪复发 (transient SSLEOFError 抖动), 已自愈
> 最新 5min: **cc2-primary 200|12 = 0 非-200, 100% SR**
> fallback: **0%**, ms_gw 未走 (502 直返 SDK, fallback_actually_attempted=f)

## 本轮 (R1154) 改动 + 依据 + 验证

### 改动: 无 (NOP 巡检轮。最新 5min 100% SR, tier 无 429/empty, 无新错误类型, buffer 当前干净。
### 2× 502 为孤立瞬时 egress 复发, 非持续劣化 → 不符改码条件)

### 依据 (实查 2026-08-08 02:41 CST + 注入)

- **30min cc4101-primary (实查)**: `200|93`, `502|2` → 97.9% SR, 2× buffer_exhausted
  (avg_dur ~34.8s; input 各 80973/71105 chars — 超大请求)。
- **60min nv_gw 日志深挖 (实查, 关键)**: NV-BUFFER-EXHAUSTED 计 8 次分 2 个孤立 burst:
  - Burst1 17:47–18:02 UTC 6× (R1148/49 风暴带, 已闭环) + Burst2 18:34/18:36 UTC 2× (**新发**)。
  - 均 all_keys_exhausted, 3 连败 fail-fast, ms_gw 亦返非 200。
- **90min per-min 趋势 (实查, 决定性)**: 17:13–17:45 全 200 → 17:47-18:02 风暴带 6×502 →
  18:03-18:33 全 200 (30min 干净) → 18:34/18:36 2×502 (新 burst) → 18:37-now 全 200。
  → Burst2 是干净流量中新发的孤立瞬时事件, 非旧风暴残留。
- **全模型 SR (注入)**: dsv4f0731_nv 100% (198/198 含 hermes)。
- **Tier (注入)**: 全 5 key pexec_success, 仅 1× NVCFPexecTimeout; **429=0, empty=0**。
- **fallback (实查)**: f, fallback_actually_attempted=f → ms_gw 未走。
- **容器 (实查)**: 40006/40066/4101 `/health` 全 ok, 全未重启。

### 验证
最新 5min 12/12 = 100% SR; 容器全健康; tier 无 429/empty; buffer 当前日志全 attempt-1 direct
flush success。Burst2 已自愈, 5min 窗口无残留错误。

## 参数快照 (nv_gw + cc4101, 注入)

- **nv_gw**: UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, NVU_BUFFER_MAX_RETRIES=5
  (stairs 90×5=450s), NVU_DISABLE_MS_FALLBACK=0, NVU_FORCE_STREAM_UPGRADE=0,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90,
  TIER_COOLDOWN_S=180, MIN_OUTBOUND_INTERVAL_S=10, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4 (全 key bind fid index 0=281478d0-f307)。
- **cc4101**: PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages,
  FALLBACK_UPSTREAM_MODEL=glm5_2_ms, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, PRIMARY_FAIL_THRESHOLD=3,
  PRIMARY_SKIP_S=30, UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150。

## 上轮
R1153 (NOP — 整窗 104/104=100% SR, R1148/49 风暴尾窗彻底滚出)。
R1154 确认: 最新 5min 仍 100%, 但 60min 深挖发现风暴带后 32min 有**第 2 次独立瞬时 burst** (2×502, 超 5 key), 已自愈。

## 下一步
维持静稳观察。**重点监控是否复发第 3 次 / 复发间隔 <30min**。若下一 30min 窗口再现 ≥2×
buffer_exhausted 或复发频率上升, 则按记忆逻辑深挖 mihomo dsv4f0731_nv egress 线路
(7900-7904), 并评估超 5 key 上超大请求 (>70K chars) 的 buffer 首跳韧性是否需微调。