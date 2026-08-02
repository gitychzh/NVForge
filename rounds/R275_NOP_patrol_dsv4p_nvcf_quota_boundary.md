# R275 — NOP 巡检轮: dsv4p_nv NVCF 5min 配额边界周期性 429 (hermes caller, 非 cc2)

## 日期
2026-08-02 15:20 CST (R274 后约 7min)

## 链路 (本轮无 restart, 无改动)
cc2(cc4101-primary, dsv4p_nv) → nv_gw(40006) → NVCF

## 本轮关键发现

### 1. cc2 primary 30min 仍 0 req (链路空闲健康)
- 同 R274, cc2 session 间歇空闲, 无 cc2 流量 → 无 buffer/WaitQueue 触发.
- 0 fallback, 0 stream_total_deadline.

### 2. dsv4p_nv SR 下降但根因是 NVCF 配额边界, 非代码缺陷
- 30min: 24/26 = 92.3% (R274 时 28/29=96.6%).
- 3 失败全 hermes caller (非 cc2 primary), 同一 NVCF function 12acbc62-3a9e-461f-8139-142e914b6f16.
- 失败时间精确等间隔 5min: 07:10:31 / 07:15:32 / 07:20:33 (CST 15:10/15:15/15:20).
- duration 1.5-2.7s 极快失败, nv_tier_attempts 0 条 (走 pexec peek-retry path, 非 buffer path).
- **关键铁证**: 失败发生的整 5min 桶内 ok=0 (07:10/07:15/07:20 全 0 成功), 说明 NVCF 配额
  在 5min 窗口边界点耗尽, 等下一窗口刷新恢复. 这是 NVCF 侧 dsv4p_nv function 的硬配额机制.

### 3. 3h 周期性趋势 (确认非一次性风暴)
| UTC 小时 | ok | fail |
|---|---|---|
| 04:00 | 9 | 4 |
| 05:00 | 50 | 6 |
| 06:00 | 52 | 9 |
| 07:00 | 14 | 3 |
- 失败稳定 3-9/h, 累计 22/3h, 全 hermes caller, 全整 5min 边界点.
- 非 R274 记的"一次性风暴尾巴", 是持续性 NVCF 配额边界模式.

### 4. 为何 hermes 流量不受 buffer 保护
- `NVU_BUFFER_CALLERS=cc4101-primary,openclaw2` — hermes 不在列表.
- hermes 遇 429 走 pexec peek-retry path, 一击即败 (1.5-2.7s all_tiers_exhausted).
- cc2 primary 在 buffer 保护下, 遇 429 会 5key 轮转 (k0→k4 各 90s), 故 cc2 不会受此配额边界影响.
- 这是设计: buffer 保护 cc2 自有流量, hermes 是另一 caller (peer 流量).

## 判稳
- **NOP 巡检轮**. cc2 primary 0 req, 链路空闲健康, 0 fallback 0 deadline.
- dsv4p_nv 失败全在 hermes caller 打 NVCF 5min 配额边界, 非 nv_gw 代码缺陷.
- R274 "考察 TIER_COOLDOWN 牵连" 前提 ("对孤立风暴可接受, cc2 流量未受影响") 仍成立:
  cc2 primary 无流量受影响, 牵连只发生在非 buffer caller (hermes) 的 pexec path.
- 本轮 0 改动, 0 restart.

## 与 R274 对比
- R274: 1 个 429 风暴尾巴 (eab966c9, 15:10:31).
- R275: 同 eab966c9 + 续 2 个 (ffb0c128 15:15, 39c58630 15:20), 揭示为 5min 周期性而非一次性.
- 模式升级: 从"一次性风暴尾巴"修正认知为"NVCF dsv4p_nv function 5min 配额边界周期性耗尽".

## 下一步
1. cc2 session 恢复流量后, 复测 buffer 5key 轮转对 dsv4p_nv 5min 配额边界的抵抗力
   (期望: cc2 primary 遇边界点 429 → buffer 切下一 key → success, 不受 hermes 风暴影响).
2. 若未来 hermes caller 也需保护, 考察把 hermes 纳入 NVU_BUFFER_CALLERS (非本轮任务,
   涉及 peer 流量策略, 需谨慎).
3. 持续监控 dsv4p_nv 5min 边界 429 是否恶化 (>10/h 或蔓延至非边界点).
   现状 3-9/h 全在边界点, 可接受.

## 参数快照 (2026-08-02 15:20 CST, 本轮未改参数)
- cc4101: PRIMARY_UPSTREAM_MODEL=dsv4p_nv, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400,
  UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150, CC4101_PRIMARY_SKIP_S=30,
  CC4101_PRIMARY_FAIL_THRESHOLD=3,
  PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages,
  FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, BUFFER_MAX_RETRIES=5,
  BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, BUFFER_TOTAL_DEADLINE=450s,
  TIER_TIMEOUT_BUDGET=180s, TIER_COOLDOWN_S=180s, UPSTREAM_TIMEOUT=90s,
  KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, MIN_OUTBOUND_INTERVAL_S=10,
  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, NVU_FORCE_STREAM_UPGRADE=0,
  NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- /health: status=ok, nv_num_keys=5, nv_default_model=glm5_2_nv,
  nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], port=40006
