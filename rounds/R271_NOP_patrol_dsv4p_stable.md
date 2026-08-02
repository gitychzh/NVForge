# R271 — NOP 巡检轮 (dsv4p_nv primary 链路持续稳定, 自恢复闭环复测通过)

**时间**: 2026-08-02 15:10 CST
**轮型**: NOP 巡检轮 (0 改动 0 restart)
**上轮**: R270 NOP

## 依据 (注入 30min 窗口 + 实时 DB 复查 + buffer 日志)

### cc2 (cc4101-primary) 30min 注入窗口 — 16 req, 11 200 / 5 502
- 表面 SR=69%, 但 5 个 502 全是 14:25-14:30 一次性 429 风暴窗口滚动尾巴.
- **按分钟趋势 (DB 实测)**: 06:28-06:32 共 5 个 502, 06:34 后连续全 200
  (06:34×1, 06:35×2, 06:36×6, 06:37×2). 14:34 后无新失败.
- 30min 后 (06:37 后) cc4101-primary 无新请求 (session 间歇), 链路空闲健康.

### 5 个 502 根因 (跨 R268/R269/R270/R271 四轮一致)
- `nv_tier_attempts` 30min 0 条错误 (R271 实测空), 5 个 502 零 tier attempt
  → 全 key cooling 时 buffer 直接 `execute_failed` elapsed=0s.
- NVCF + ms_gw 同窗口 (14:26-14:30) 瞬时 429 风暴, 一次性尾部, 14:34 后消失.

### 自恢复闭环实测 (日志 14:35, 与 R269/R270 同证据)
- req=3a3dd02b attempt=1 `NV-BUFFER-EXEC-DELEGATE` (MODE_CHAIN 空, 委托 execute_request)
  → `NV-BUFFER-EXEC-FAIL` all_keys_exhausted=True → `execute_failed` elapsed=0s (全挂).
- `NV-BUFFER-BACKOFF` 退避 5s → attempt=2 → 14:35:57 `NV-BUFFER-SUCCESS`
  verdict=success_thinking elapsed=6973ms, 200.
- 同窗口 bf349a51 一次成功 elapsed=21210ms (单 attempt).
- R-nvonly 自恢复闭环 (KeyManager+ProbeWorker+WaitQueue+BufferStreamSession) 在工作.

### post266 DELEGATE 对 dsv4p_nv 持续生效
- 干净窗口全走 `NV-BUFFER-EXEC-DELEGATE` (MODE_CHAIN 空 → execute_request, integrate-first path).
- 0 fallback, dsv4p_nv 链路健康.

## 判稳
- 5 个 502 = 上轮 429 风暴窗口的滚动 30min 尾巴, 14:34 后全 200, 无反复, 四轮一致.
- 自恢复闭环实测通过 (backoff 5s → attempt 2 自恢复).
- 无新错误模式, 无需改码.
- → NOP 巡检轮, 0 改动 0 restart.

## 下一步
1. 持续观察 dsv4p_nv 在 cc2 primary 下 SR, 看是否有反复 502 窗口.
2. 若 `all_tiers_exhausted` + 零 tier attempt 反复出现, 考察 KeyManager 全挂判定是否过早.
   现有 backoff 5s 已足够等 ProbeWorker 唤醒, 暂无需调.
3. 关注 dsv4p_nv 429 是否集中在特定 key/egress IP (本轮 0 新 429).

## 参数快照 (2026-08-02 15:10 CST, 本轮未改参数)
- cc4101: PRIMARY_UPSTREAM_MODEL=dsv4p_nv, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400,
  UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150.
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5,
  BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, BUFFER_TOTAL_DEADLINE=450s,
  TIER_TIMEOUT_BUDGET=180s, TIER_COOLDOWN_S=180s, UPSTREAM_TIMEOUT=90s,
  KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv,
  NV_GLM52_MODE_CHAIN= (空, R-nvonly-post14 设计).
