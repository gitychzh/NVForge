# R276 — NOP 巡检轮 (dsv4p_nv 5min 配额边界持续, cc2 无流量不受影响)

**日期**: 2026-08-02 15:26 CST
**上轮**: R275 (NOP 巡检轮)
**改动**: 0 改动, 0 restart, 0 py_compile

## 轮前链路数据 (30min 实�� DB)

### 1. cc2 (cc4101-primary) 30min 0 req
- 同 R275, session 间歇空闲, 链路空闲健康. 0 fallback, 0 stream_total_deadline.
- cc2 primary 在 `NVU_BUFFER_CALLERS` 保护下, 无流量即无风险.

### 2. dsv4p_nv 30min SR=78.9% (15/19), 4 失败全 hermes caller 全 5min 边界点
| ts (UTC) | caller | status | error_type | req |
|---|---|---|---|---|
| 07:10 | hermes | 429 | all_tiers_exhausted | eab966c9 |
| 07:15 | hermes | 429 | all_tiers_exhausted | ffb0c128 |
| 07:20 | hermes | 429 | all_tiers_exhausted | 39c58630 |
| 07:25 | hermes | 429 | all_tiers_exhausted | de233fd3 |
- 4 失败全整 5min 边界点 (07:10/07:15/07:20/07:25 UTC = 15:10/15:15/15:20/15:25 CST), 等间隔 5min.
- 全 hermes caller, 非 cc2. hermes 不在 `NVU_BUFFER_CALLERS`, 走 pexec peek path 一击即败.
- nv_tier_attempts **0 条** (hermes 非 buffer caller, 无 buffer 5key 轮转发生).
- error_type `all_tiers_exhausted` + duration ~1.5-2.7s 极快失败 (pexec peek 一击即败非 buffer path).

### 3. NVCF 5min 配额边界铁证 (持续, 非一次性风暴)
- 失败全整 5min 桶边界, 桶内 ok=0 → NVCF dsv4p_nv function `12acbc62-3a9e-461f-8139-142e914b6f16`
  配额在 5min 窗口边界点耗尽, 等下一窗口刷新恢复.
- R275 记 3 失败 (07:10/07:15/07:20), 本轮新增 07:25 → 印证"持续 5min 周期"非"风暴尾巴".

### 4. 3h 周期性趋势 (确认持续性)
| UTC 小时 | ok | 429 | 502 | 总 fail | SR |
|---|---|---|---|---|---|
| 04:00 | 9 | 3 | 0 | 3 | 75.0% |
| 05:00 | 50 | 5 | 1 | 6 | 89.3% |
| 06:00 | 52 | 3 | 6 | 9 | 85.2% |
| 07:00 | 14 | 4 | 0 | 4 | 77.8% |
- 429 失败稳定 3-5/h (15/3h), 全 hermes 全整 5min 边界点.
- 06:00 出现 6 个 502 (上轮 R274 注入窗口的残留, 非 R275/R276 新增).
- 非 nv_gw 代码缺陷, NVCF 侧硬配额机制.

### 5. 为何 cc2 不受影响
- `NVU_BUFFER_CALLERS=cc4101-primary,openclaw2` — cc2 primary 在 buffer 保护下.
- cc2 遇 429 → buffer 5key 轮转 (k0→k4 各 90s) → 切下一 key 绕过单 key 配额边界.
- hermes 不在 buffer 列表, 走 pexec peek path 一击即败, 是设计 (hermes 是另一 caller 流量).

### 6. health (本轮无 restart)
- nv_gw /health: status=ok, nv_num_keys=5, nv_default_model=glm5_2_nv,
  nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], port=40006.
- 容器: nv_gw Up 54min, cc4101 Up 1h, ms_gw Up 3d, logs_db Up 3d.

## 判稳
- **NOP 巡检轮**. cc2 primary 0 req, 链路空闲健康, 0 fallback 0 deadline.
- dsv4p_nv 失败全在 hermes caller 打 NVCF 5min 配额边界, 非 nv_gw 代码缺陷.
- 3h 429 失败 15/3h 稳定 3-5/h 全边界点, 未恶化 (>10/h 或蔓延至非边界点才需介入).
- R275 判断"持续性 NVCF 5min 配额边界周期性耗尽"本轮再获验证 (07:25 新增).

## 下一步
1. cc2 session 恢复流量后, 复测 buffer 5key 轮转对 dsv4p_nv 5min 配额边界的抵抗力
   (期望: cc2 primary 遇边界点 429 → buffer 切下一 key → success).
2. 持续监控 dsv4p_nv 5min 边界 429 是否恶化 (>10/h 或蔓延至非边界点). 现状 3-5/h 可接受.
3. 若未来 hermes caller 也需保护, 考察把 hermes 纳入 NVU_BUFFER_CALLERS (非本轮任务).

## 参数快照 (2026-08-02 15:26 CST, 本轮未改参数)
- cc4101: PRIMARY_UPSTREAM_MODEL=dsv4p_nv, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages,
  FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400,
  UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150, CC4101_PRIMARY_SKIP_S=30,
  CC4101_PRIMARY_FAIL_THRESHOLD=3
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, BUFFER_MAX_RETRIES=5,
  BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, BUFFER_TOTAL_DEADLINE=450s,
  TIER_TIMEOUT_BUDGET=180s, TIER_COOLDOWN_S=180s, UPSTREAM_TIMEOUT=90s,
  KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, MIN_OUTBOUND_INTERVAL_S=10,
  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, NVU_FORCE_STREAM_UPGRADE=0,
  NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4,
  NV_GLM52_MODE_CHAIN= (空, post266 设计)
