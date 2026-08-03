# R662 — NOP 巡检轮 — R661 collect-buffer-retry 改后窗口无流量待验

> 时间: 2026-08-03 16:12 CST
> 上轮: R661 (collect 传输中断→buffer 5key 重试, R651 阈值首次触发后实施)
> 容器: nv_gw Up 6min (R661 restart @16:03), cc4101 Up 54min

## 判稳结论: NOP (不改码)

### 判稳依据
1. **R661 改后窗口 (08:03-08:12 UTC, ~9min) cc4101-primary 0 请求** — 无法验证 collect-buffer-retry 效果, 但无流量 = 无错误 = 无劣化信号. 改动 ast parse ok + restart + health ok 已在上轮完成, 本轮不动码.
2. **改前 60min cc4101-primary SR=93.75%** (15×200 + 1×502/IncompleteRead) — 那 1×502 正是 R661 修复目标 (07:20:50 UTC NVAnthCollect_IncompleteRead 34384ms), 改后窗口尚未出现同类错误, 需等流量验证.
3. **tier 层 key 持续可用**: pexec_success×12 + integrate_success×4; RemoteDisconnected×6+SSLEOFError×4 被 mark_transport_error 短惩罚 (5-10s); 429_nv_rate_limit×1.
4. **deadline 链 6h=0 健康** — buffer 450s < cc4101 470s < SDK idle 500s 对齐铁证持续.
5. **/health ok**: nv_num_keys=5, nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], default=glm5_2_nv.
6. **配置无漂移**: NVU_DISABLE_MS_FALLBACK=1, buffer 5×90s=450s, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2.
7. **无启动错误**: docker logs --since 10m 无 error/traceback/import 失败.

### 注入数据 (30min 链路总览, 窗口偏移到 hermes caller)
- 30min cc4101-primary 专属 **空** (请求量低 + R661 restart 后窗口短)
- 30min 链路全是 hermes|dsv4p_nv: 33req SR=90.9% (30×200+1×429+2×502), 配额型 all_tiers_exhausted×2 (5key 全 429→TIER_COOLDOWN 180s)
- 这不是 cc2 链路 (cc2 = cc4101-primary/glm5_2_nv), 是 hermes caller 的 dsv4p_nv 流量, 与本轮优化目标无关

## 基线 (R662 实测)
- cc2 (cc4101-primary/glm5_2_nv) 60min: 16req SR=93.75% (15×200+1×502)
  - 唯一 502: 07:20:50 UTC NVAnthCollect_IncompleteRead 34384ms (R661 修复目标, 改前事件)
- dsv4p_nv (hermes caller) 30min: 33req SR=90.9% (配额型, 非本链路)
- tier 60min: pexec_success×12, integrate_success×4, integrate_conn_RemoteDisconnected×6, pexec_SSLEOFError×4, pexec_conn_RemoteDisconnected×2, 429_nv_rate_limit×1
- deadline 6h: stream_total_deadline=0 (健康)

## 下一步
- **R661 改动待验**: 等下一波 cc4101-primary 流量 + IncompleteRead 再现 → 看 `NV-ANTH-COLLECT-BUFRETRY` 日志:
  - 救回 200 → R661 生效, cc2 SR 升至 100%
  - 救回失败 (BUFRETRY-FAIL) → NVCF 持续劣化, 需更深排查
- **持续监控点**:
  1. cc2 IncompleteRead 再现时 buffer retry 是否触发
  2. 150min 回查 IncompleteRead 是否回归单次事件 (改后应减少)
  3. dsv4p_nv 配额型 429 全挂 (持续, NVCF 无 retry-after)
  4. deadline 链健康持续
- **建议维持**: 联系 NVCF 侧评估 dsv4p_nv 配额扩容 / retry-after 头

## 参数快照 (R662 无变化, 沿用 R661)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180,
  KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, MIN_OUTBOUND_INTERVAL_S=10,
  NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150,
  NVU_BUFFER_MAX_RETRIES=5, NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90,
  NVU_BUFFER_TOTAL_DEADLINE_S=450, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4,
  NVU_KEYMGR_429_BASE_COOLDOWN=120, NVU_KEYMGR_429_MAX_COOLDOWN=600,
  NVU_KEYMGR_CONN_BASE_COOLDOWN=30, NVU_KEYMGR_CONN_FAIL_THRESHOLD=3,
  NVU_KEYMGR_CONN_LONG_COOLDOWN=120, NVU_KEYMGR_CONN_MAX_COOLDOWN=60,
  TIER_TIMEOUT_BUDGET_S=180, NVU_MS_FALLBACK_ENABLED=0
- cc4101: PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, PRIMARY_UPSTREAM_MODEL=glm5_2_nv,
  FALLBACK_UPSTREAM_URL=http://dsv4p_nv40066:40066/v1/messages, FALLBACK_UPSTREAM_MODEL=dsv4p_nv,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400,
  CC4101_PRIMARY_SKIP_S=30, CC4101_PRIMARY_FAIL_THRESHOLD=3,
  UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150
