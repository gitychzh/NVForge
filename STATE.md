# STATE — cc2 自优化 nv_gw 链路 (R-nvonly 方向)

## 当前轮基线 (2026-08-02 15:13 CST, R273 NOP 巡检轮)
- 本仓 master: 本轮 R273. (主仓 hermes_improve_self main 收 round 文件.)
- **架构变化 (主仓 b4527f9, 非本轮)**: cc4101 `PRIMARY_UPSTREAM_MODEL` 已从
  `glm5_2_nv` 切到 `dsv4p_nv`. cc2 链路现 = cc4101(dsv4p_nv) → nv_gw → NVCF.
- **本轮 R273 (hm2_cc2)**: NOP 巡检轮. dsv4p_nv 30min 实测 31/31 全 200, 0 错 0 fallback,
  nv_tier_attempts 0 条 (5key 全可用无 cooling). 上轮 R271 429 风暴窗口完全消散, 六轮一致 (R268-R273).
  cc4101-primary caller 区段空 (cc2 session 间歇), 但 hermes/openclaw caller 全 200 证明链路健康.
- 0 改动 0 restart.

## R-nvonly 核心铁律 (持续生效)
- 只改 HM2 nv_gw (40006), 不碰 HM1, 不碰 ms_gw 源码.
- ms_gw fallback 已恢复 (`NVU_DISABLE_MS_FALLBACK=0`, `FALLBACK_UPSTREAM=ms_gw:40007`), 不主动禁用.
- 改前有数据, 改后必验证, 写入仓库.

## 本轮关键数据 (30min 实时 DB 复查 ~15:13)

### 1. dsv4p_nv 30min 总览 — 31 req, 31 200 / 0 错
- SR=100.0%, 0 fallback, 0 错误分类.
- avg_dur=10355ms, max_dur=26542ms, min_dur=4408ms.
- finish_reason: tool_calls×24, stop×7.
- per-key: key2 200×30 (egress 203.10.96.139), key3 200×1 (134.195.101.194).

### 2. nv_tier_attempts 30min 0 条错误
- 无 key cooling, 5key 全可用, 上轮风暴窗口完全消散.

### 3. cc4101-primary (cc2) 30min 区段
- 注入窗口显示 cc4101-primary caller 区段为空 — cc2 session 间歇, 30min 内无新请求.
- hermes (30×200) + openclaw (1×200) caller 全 200 证明 nv_gw→NVCF 链路健康.

### 4. 容器健康
- nv_gw Up 36min, cc4101 Up 43min, ms_gw Up 3d, logs_db Up 3d.
- `/health`: status=ok, nv_num_keys=5, pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv].

### 5. 自恢复闭环 (六轮一致 R268-R273)
- 本轮 30min 内无 BUFFER-EXHAUSTED / WAIT-TIMEOUT 日志 — 链路一击直中, 无需触发自恢复.
- post266 DELEGATE + backoff 5s 闭环持续生效.

## 判稳
- dsv4p_nv 整链 30min SR=100% (31/31), 0 错 0 fallback, 0 key cooling.
- cc2 primary 区段空窗系 session 间歇非链路问题.
- → NOP 巡检轮, 0 改动 0 restart.

## 下一步
1. 持续观察 dsv4p_nv 在 cc2 primary 下 SR, 看是否有新 502/429 风暴窗口.
2. 若 `all_tiers_exhausted` + 零 tier attempt 反复出现, 考察 KeyManager 全挂判定是否过早
   (现有 backoff 5s 已足够等 ProbeWorker 唤醒, 暂无需调).
3. 关注 dsv4p_nv 429 是否集中特定 key/egress IP (本轮 0 新 429).
4. cc2 session 间歇导致 cc4101-primary 区段空窗 — 非链路问题, 数据需多 session 累积.

## 参数快照 (2026-08-02 15:13 CST, 本轮未改参数)
- cc4101: PRIMARY_UPSTREAM_MODEL=dsv4p_nv, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  PRIMARY_UPSTREAM_URL=nv_gw:40006/v1/messages (host:port 写法避 push-protection),
  FALLBACK_UPSTREAM_URL=ms_gw:40007/v1/chat/completions,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400,
  UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150, CC4101_PRIMARY_SKIP_S=30,
  CC4101_PRIMARY_FAIL_THRESHOLD=3
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, BUFFER_MAX_RETRIES=5,
  BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, BUFFER_TOTAL_DEADLINE=450s,
  TIER_TIMEOUT_BUDGET=180s, TIER_COOLDOWN_S=180s, UPSTREAM_TIMEOUT=90s,
  KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, MIN_OUTBOUND_INTERVAL_S=10,
  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, NVU_FORCE_STREAM_UPGRADE=0,
  NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
