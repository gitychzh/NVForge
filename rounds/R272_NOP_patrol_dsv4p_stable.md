# R272 — NOP 巡检轮 (dsv4p_nv primary 链路持续稳定, 502 窗口已滚出 30min)

**时间**: 2026-08-02 15:12 CST
**轮型**: NOP 巡检轮 (0 改动 0 restart)
**上轮**: R271 NOP

## 依据 (实时 30min DB 复查 + buffer 日志, 非旧注入窗口)

### cc2 (cc4101-primary) 30min 实测 — 11 req, 11 200 / 0 错
- SR=100%. 上轮 R271 注入窗口里的 5 个 502 (14:25-14:30 一次性 429 风暴尾巴)
  已滚出 30min 窗口, 本轮零 502 零 429 零 fallback.
- **按分钟趋势 (DB)**: 06:34×1, 06:35×2, 06:36×6, 06:37×2 全 200, 之后 cc4101-primary
  无新请求 (session 间歇). 06:35 唯一一个 429 来自 `hermes` caller 非 cc2.
- `nv_tier_attempts` 30min 0 条错误 → 无 key cooling, 5key 全可用.

### 自恢复闭环 (日志 14:35, 与 R269/R270/R271 同证据, 持续生效)
- req=3a3dd02b: attempt=1 `NV-BUFFER-EXEC-DELEGATE` (MODE_CHAIN 空) →
  `NV-BUFFER-EXEC-FAIL` all_keys_exhausted=True elapsed=0s →
  `NV-BUFFER-BACKOFF` 退避 5s → attempt=2 → 14:35:57 `NV-BUFFER-SUCCESS`
  verdict=success_thinking elapsed=6973ms, 200.
- req=bf349a51: 单 attempt 成功 elapsed=21210ms, 1 attempt flush 5224b.
- req=18e1c015: 1 attempt flush 6261b elapsed=11330ms.
- post266 DELEGATE (MODE_CHAIN 空委托 execute_request, integrate-first path) 对 dsv4p_nv 持续生效.

### 2h SR 趋势 (10min 桶)
- 05:54-06:23 全 200 (零星), 06:28-06:32 五个 502 (一次性风暴), 06:34 后全 200 至今.
- 五轮一致 (R268-R272): 14:34 后 0 反复 0 新失败.

## 判稳
- cc2 primary 30min SR=100%, 无新错误模式, 无 fallback, 无 key cooling.
- dsv4p_nv 链路健康, post266 修复持续生效, 自恢复闭环实测通过.
- → NOP 巡检轮, 0 改动 0 restart.

## 下一步
1. 持续观察 dsv4p_nv 在 cc2 primary 下 SR, 看是否有新 502/429 风暴窗口.
2. 若 `all_tiers_exhausted` + 零 tier attempt 反复出现, 考察 KeyManager 全挂
   判定是否过早. 现有 backoff 5s 已足够等 ProbeWorker 唤醒, 暂无需调.
3. 关注 dsv4p_nv 429 是否集中特定 key/egress IP (本轮 0 新 429).

## 参数快照 (2026-08-02 15:12 CST, 本轮未改参数)
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
